from __future__ import annotations

import os
import queue
from dataclasses import asdict
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import ANDROID_API, APP_NAME, BUILD_TOOLS, VERSION
from .build_history import BuildHistoryStore
from .builder import GhostBuilder
from .core import ConfigStore, Paths, ToolchainManager
from .i18n import Translator, detect_system_language, normalize_language
from .project_store import RecentProjects, load_project, save_project
from .readiness import check_play_readiness
from .ui_actions import ActionsMixin
from .ui_layout import LayoutMixin
from .ui_theme import ACCENT, BG, BLUE, CARD, MUTED, SURFACE, TEXT, WARNING

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")


class GhostApp(LayoutMixin, ActionsMixin, ctk.CTk):
    TABS = ("home", "project", "android", "kotlin", "signing", "engine", "logs")
    SIMPLE_TABS = ("home", "project")

    def __init__(self, smoke_test: bool = False):
        super().__init__()
        self.paths = Paths()
        self.store = ConfigStore(self.paths.config)
        self.recent_projects = RecentProjects(self.paths.root / "recent_projects.json", limit=8)
        self.build_history = BuildHistoryStore(self.paths.root / "build_history.json", limit=50)
        self.current_project_path: Path | None = None
        self._active_build_cfg = None
        self._build_started_at = None
        saved = self.store.load()
        self.lang = normalize_language(saved.get("language") or detect_system_language())
        self.ui_mode = saved.get("ui_mode") if saved.get("ui_mode") in {"simple", "advanced"} else "simple"
        self.t = Translator(self.lang)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.toolchain = ToolchainManager(self.paths, self._emit)
        self.builder = GhostBuilder(self.toolchain, self._emit)
        self._translated: list[tuple[object, str, dict]] = []
        self._tab_names: dict[str, str] = {}
        self._busy = False

        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1280x840")
        self.minsize(1040, 700)
        self.configure(fg_color=BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()
        self._build_project_productivity_ui()
        self._load_config(saved)
        self._apply_ui_mode(self.ui_mode, persist=False)
        self._refresh_recent_projects()
        self.after(80, self._drain_events)
        self.after(180, self.refresh_engine_status)

        if smoke_test:
            self.after(900, self.destroy)
        elif not saved.get("onboarding_done"):
            self.after(350, self._show_welcome)

    def trw(self, widget, key: str, **kwargs):
        widget.configure(text=self.t(key, **kwargs))
        self._translated.append((widget, key, kwargs))
        return widget

    def _mode_labels(self):
        return ("Prosty", "Zaawansowany") if self.lang == "pl" else ("Simple", "Advanced")

    def _apply_ui_mode(self, mode: str, persist: bool = True) -> None:
        self.ui_mode = "advanced" if mode == "advanced" else "simple"
        simple_label, advanced_label = self._mode_labels()
        self.mode_switch.configure(values=[simple_label, advanced_label])
        self.ui_mode_var.set(simple_label if self.ui_mode == "simple" else advanced_label)
        visible_keys = self.TABS if self.ui_mode == "advanced" else self.SIMPLE_TABS
        visible_names = [self._tab_names[key] for key in visible_keys]
        self.tabs._segmented_button.configure(values=visible_names)
        try:
            current = self.tabs.get()
        except Exception:
            current = ""
        if current not in visible_names:
            self.tabs.set(self._tab_names["home"])
        if persist:
            data = self.store.load()
            data["ui_mode"] = self.ui_mode
            data["language"] = self.lang
            self.store.save(data)
            self._append_log("info", f"UI mode: {self.ui_mode}")

    def _switch_ui_mode(self, value: str) -> None:
        simple_label, _ = self._mode_labels()
        self._apply_ui_mode("simple" if value == simple_label else "advanced", persist=True)

    def _go_tab(self, key):
        if self.ui_mode == "simple" and key not in self.SIMPLE_TABS:
            self._apply_ui_mode("advanced", persist=True)
        self.tabs.set(self._tab_names[key])

    def _switch_language(self, value):
        ActionsMixin._switch_language(self, value)
        self._apply_ui_mode(self.ui_mode, persist=False)
        self._refresh_recent_projects()
        self._refresh_productivity_labels()

    def save_config(self, quiet=False):
        ActionsMixin.save_config(self, quiet=quiet)
        data = self.store.load()
        data["ui_mode"] = self.ui_mode
        self.store.save(data)

    def _build_project_productivity_ui(self) -> None:
        project_tab = self._tab("project")
        tools = ctk.CTkFrame(project_tab, fg_color=CARD, corner_radius=14)
        tools.pack(fill="x", padx=12, pady=10)
        self.profile_title = ctk.CTkLabel(tools, text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold"))
        self.profile_title.pack(side="left", padx=16, pady=14)
        self.profile_open_btn = ctk.CTkButton(tools, width=115, fg_color=CARD, command=self.open_project_profile)
        self.profile_open_btn.pack(side="right", padx=(6, 14), pady=10)
        self.profile_save_btn = ctk.CTkButton(tools, width=115, fg_color=BLUE, command=self.save_project_profile)
        self.profile_save_btn.pack(side="right", padx=6, pady=10)
        self.play_check_btn = ctk.CTkButton(tools, width=145, fg_color=ACCENT, text_color="#04100e", command=self.show_play_readiness)
        self.play_check_btn.pack(side="right", padx=6, pady=10)
        self.history_btn = ctk.CTkButton(tools, width=115, fg_color=CARD, command=self.show_build_history)
        self.history_btn.pack(side="right", padx=6, pady=10)
        self.cert_btn = ctk.CTkButton(tools, width=115, fg_color=CARD, command=self.show_certificate_fingerprints)
        self.cert_btn.pack(side="right", padx=6, pady=10)

        home_tab = self._tab("home")
        self.recent_box = ctk.CTkFrame(home_tab, fg_color=CARD, corner_radius=14)
        self.recent_box.pack(fill="x", padx=14, pady=10)
        self.recent_title = ctk.CTkLabel(self.recent_box, text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold"), anchor="w")
        self.recent_title.pack(fill="x", padx=16, pady=(14, 6))
        self.recent_rows = ctk.CTkFrame(self.recent_box, fg_color="transparent")
        self.recent_rows.pack(fill="x", padx=12, pady=(0, 12))
        self._refresh_productivity_labels()

    def _refresh_productivity_labels(self) -> None:
        pl = self.lang == "pl"
        self.profile_title.configure(text="Profil projektu .ghostproject" if pl else "Project profile .ghostproject")
        self.profile_open_btn.configure(text="Otwórz" if pl else "Open")
        self.profile_save_btn.configure(text="Zapisz" if pl else "Save")
        self.play_check_btn.configure(text="Gotowość Play" if pl else "Play readiness")
        self.history_btn.configure(text="Historia" if pl else "History")
        self.cert_btn.configure(text="Certyfikat" if pl else "Certificate")
        self.recent_title.configure(text="Ostatnie projekty" if pl else "Recent projects")

    def _apply_project_config(self, cfg) -> None:
        self._load_config(asdict(cfg))
        self.code.delete("1.0", "end")
        self.code.insert("1.0", cfg.custom_source or "")

    def save_project_profile(self) -> None:
        initial = self.current_project_path.name if self.current_project_path else f"{self.app_name.get().strip() or 'Ghost-App'}.ghostproject"
        path = filedialog.asksaveasfilename(defaultextension=".ghostproject", initialfile=initial, filetypes=[("Ghost Project", "*.ghostproject")])
        if not path:
            return
        try:
            target = save_project(path, self._config())
            self.current_project_path = target
            self.recent_projects.add(target)
            self._refresh_recent_projects()
            self._append_log("success", f"Project profile saved: {target}")
            messagebox.showinfo("Ghost APK Builder", ("Projekt zapisany:\n" if self.lang == "pl" else "Project saved:\n") + str(target))
        except Exception as exc:
            messagebox.showerror("Ghost APK Builder", str(exc))

    def open_project_profile(self, path: str | Path | None = None) -> None:
        selected = str(path) if path else filedialog.askopenfilename(filetypes=[("Ghost Project", "*.ghostproject")])
        if not selected:
            return
        try:
            source = Path(selected)
            cfg = load_project(source)
            self._apply_project_config(cfg)
            self.current_project_path = source
            self.recent_projects.add(source)
            self._refresh_recent_projects()
            self._append_log("success", f"Project profile opened: {source}")
            self._go_tab("project")
        except Exception as exc:
            self.recent_projects.remove(selected)
            self._refresh_recent_projects()
            messagebox.showerror("Ghost APK Builder", str(exc))

    def _refresh_recent_projects(self) -> None:
        if not hasattr(self, "recent_rows"):
            return
        for child in self.recent_rows.winfo_children():
            child.destroy()
        items = self.recent_projects.load()
        if not items:
            ctk.CTkLabel(self.recent_rows, text="Brak zapisanych projektów" if self.lang == "pl" else "No saved projects yet", text_color=MUTED).pack(anchor="w", padx=4, pady=6)
            return
        for item in items[:5]:
            path = Path(item)
            row = ctk.CTkFrame(self.recent_rows, fg_color="transparent")
            row.pack(fill="x", pady=3)
            ctk.CTkLabel(row, text=path.stem, text_color=TEXT, anchor="w").pack(side="left", fill="x", expand=True)
            ctk.CTkLabel(row, text=str(path.parent), text_color=MUTED, anchor="e").pack(side="left", padx=10)
            ctk.CTkButton(row, width=90, text="Otwórz" if self.lang == "pl" else "Open", fg_color=BLUE, command=lambda p=path: self.open_project_profile(p)).pack(side="right")

    def show_build_history(self) -> None:
        pl = self.lang == "pl"
        win = ctk.CTkToplevel(self)
        win.title("Historia buildów" if pl else "Build history")
        win.geometry("900x560")
        win.configure(fg_color=BG)
        ctk.CTkLabel(win, text="Historia buildów" if pl else "Build history", text_color=TEXT, font=ctk.CTkFont(size=23, weight="bold")).pack(anchor="w", padx=22, pady=(20, 4))
        ctk.CTkLabel(win, text="Ostatnie zweryfikowane artefakty APK/AAB" if pl else "Recent verified APK/AAB artifacts", text_color=MUTED).pack(anchor="w", padx=22, pady=(0, 12))
        frame = ctk.CTkScrollableFrame(win, fg_color=SURFACE)
        frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        items = self.build_history.load()
        if not items:
            ctk.CTkLabel(frame, text="Brak buildów w historii." if pl else "No builds in history yet.", text_color=MUTED).pack(anchor="w", padx=10, pady=12)
            return
        for item in items[:20]:
            artifact = Path(item.get("artifact", ""))
            row = ctk.CTkFrame(frame, fg_color=CARD, corner_radius=12)
            row.pack(fill="x", padx=6, pady=5)
            title = f"{item.get('app_name','Ghost App')}  v{item.get('version_name','?')}  •  {item.get('mode','?')} {item.get('format','?')}"
            ctk.CTkLabel(row, text=title, text_color=TEXT, anchor="w", font=ctk.CTkFont(weight="bold")).pack(fill="x", padx=12, pady=(9,2))
            meta = f"SHA-256: {item.get('sha256','')[:16]}…   •   {item.get('size_bytes',0)/1048576:.2f} MB   •   {item.get('duration_seconds','?')} s"
            ctk.CTkLabel(row, text=meta, text_color=MUTED, anchor="w").pack(side="left", fill="x", expand=True, padx=12, pady=(0,9))
            ctk.CTkButton(row, width=110, text="Otwórz folder" if pl else "Open folder", fg_color=BLUE, command=lambda p=artifact: self._open_artifact_folder(p)).pack(side="right", padx=10, pady=(0,9))

    @staticmethod
    def _open_artifact_folder(path: Path) -> None:
        folder = path.parent if path.suffix else path
        if folder.exists() and os.name == "nt":
            os.startfile(str(folder))

    def show_certificate_fingerprints(self) -> None:
        pl = self.lang == "pl"
        path = self.keystore.get().strip()
        alias = self.alias.get().strip()
        password = self.store_password.get()
        if not path or not alias or not password:
            messagebox.showwarning("Ghost APK Builder", "Ustaw keystore, alias i hasło sesji." if pl else "Set keystore, alias and the session password first.")
            return
        try:
            found = self.builder.certificate_fingerprints(Path(path), password, alias)
            text = f"SHA-1\n{found['SHA1']}\n\nSHA-256\n{found['SHA256']}"
            self.clipboard_clear(); self.clipboard_append(found["SHA256"])
            messagebox.showinfo("Certificate fingerprints", text + ("\n\nSHA-256 skopiowano do schowka." if pl else "\n\nSHA-256 copied to clipboard."))
        except Exception as exc:
            messagebox.showerror("Ghost APK Builder", str(exc))

    def show_play_readiness(self) -> None:
        report = check_play_readiness(self._config())
        pl = self.lang == "pl"
        labels_pl = {
            "app_name_required":"Brak nazwy aplikacji.","package":"Nieprawidłowa nazwa pakietu.","version_name":"Nieprawidłowa nazwa wersji.","version_code":"Version code musi być dodatni.","target_sdk":"Target SDK musi mieć co najmniej API 36.","sdk_order":"Min SDK nie może być wyższe od Target SDK.","play_target_api":"Google Play wymaga aktualnego profilu API 36+.","play_release_required":"Przełącz Build mode na Release.","play_aab_recommended":"Do Google Play zalecany jest AAB zamiast APK.","play_signing_required":"Włącz podpisywanie Release.","play_keystore_missing":"Brakuje pliku keystore.","play_alias_missing":"Brakuje aliasu klucza.","play_icon_default":"Używana będzie domyślna ikona Ghost; warto ustawić własną.","play_icon_missing":"Wybrany plik ikony nie istnieje.","play_cleartext_enabled":"Cleartext HTTP jest włączony.","play_backup_enabled":"Android backup jest włączony."}
        labels_en = {
            "app_name_required":"Application name is missing.","package":"Package name is invalid.","version_name":"Version name is invalid.","version_code":"Version code must be positive.","target_sdk":"Target SDK must be API 36 or newer.","sdk_order":"Min SDK cannot exceed Target SDK.","play_target_api":"Google Play requires the current API 36+ profile.","play_release_required":"Switch Build mode to Release.","play_aab_recommended":"AAB is recommended for Google Play instead of APK.","play_signing_required":"Enable Release signing.","play_keystore_missing":"Keystore file is missing.","play_alias_missing":"Key alias is missing.","play_icon_default":"Ghost default icon will be used; a custom icon is recommended.","play_icon_missing":"Selected icon file does not exist.","play_cleartext_enabled":"Cleartext HTTP is enabled.","play_backup_enabled":"Android backup is enabled."}
        labels = labels_pl if pl else labels_en
        if report.ready:
            title = "GOTOWE DLA GOOGLE PLAY" if pl else "READY FOR GOOGLE PLAY"
        else:
            title = "WYMAGA POPRAWEK" if pl else "NEEDS ATTENTION"
        lines = [title, ""]
        if report.errors:
            lines.append("Błędy:" if pl else "Errors:")
            lines.extend(f"• {labels.get(x.code, x.code)}" for x in report.errors)
        if report.warnings:
            lines.append("")
            lines.append("Ostrzeżenia:" if pl else "Warnings:")
            lines.extend(f"• {labels.get(x.code, x.code)}" for x in report.warnings)
        if report.ready:
            messagebox.showinfo("Google Play", "\n".join(lines))
        else:
            messagebox.showwarning("Google Play", "\n".join(lines))

    def _build_ui(self) -> None:
        head = ctk.CTkFrame(self, fg_color=BG)
        head.pack(fill="x", padx=26, pady=(18, 8))
        ctk.CTkLabel(head, text="GHOST", text_color=ACCENT, font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=" APK BUILDER", text_color=TEXT, font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        ctk.CTkLabel(head, text=f" v{VERSION}", text_color=MUTED).pack(side="left", padx=8)
        self.engine_badge = ctk.CTkLabel(head, text=self.t("engine.checking"), fg_color=CARD, corner_radius=12, padx=14, pady=7, text_color=WARNING)
        self.engine_badge.pack(side="right")
        self.language_var = ctk.StringVar(value="PL" if self.lang == "pl" else "EN")
        ctk.CTkSegmentedButton(head, values=["PL", "EN"], variable=self.language_var, command=self._switch_language, selected_color=BLUE).pack(side="right", padx=12)
        self.trw(ctk.CTkLabel(head, text_color=MUTED), "lang.label").pack(side="right")
        simple_label, advanced_label = self._mode_labels()
        self.ui_mode_var = ctk.StringVar(value=simple_label if self.ui_mode == "simple" else advanced_label)
        self.mode_switch = ctk.CTkSegmentedButton(head, values=[simple_label, advanced_label], variable=self.ui_mode_var, command=self._switch_ui_mode, selected_color=ACCENT, selected_hover_color="#18f0d0", unselected_color=CARD)
        self.mode_switch.pack(side="right", padx=(0, 12))
        sub = ctk.CTkFrame(self, fg_color=BG)
        sub.pack(fill="x", padx=28, pady=(0, 8))
        self.trw(ctk.CTkLabel(sub, text_color=MUTED), "app.subtitle").pack(side="left")
        ctk.CTkLabel(sub, text=f"API {ANDROID_API} • Build Tools {BUILD_TOOLS} • AGP 9.4 • Gradle 9.6 • JDK 21", text_color="#617087").pack(side="right")
        self.tabs = ctk.CTkTabview(self, fg_color=SURFACE, corner_radius=16, segmented_button_fg_color=CARD, segmented_button_selected_color=ACCENT)
        self.tabs.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        for key in self.TABS:
            name = self.t(f"tab.{key}")
            self._tab_names[key] = name
            self.tabs.add(name)
        self._home_tab(); self._project_tab(); self._android_tab(); self._kotlin_tab(); self._signing_tab(); self._engine_tab(); self._logs_tab()
        foot = ctk.CTkFrame(self, fg_color=BG)
        foot.pack(fill="x", padx=24, pady=(0, 18))
        self.progress = ctk.CTkProgressBar(foot, progress_color=ACCENT, fg_color="#131d29", height=9)
        self.progress.set(0); self.progress.pack(fill="x", pady=(0, 10))
        self.build_btn = self.trw(ctk.CTkButton(foot, height=50, fg_color=ACCENT, text_color="#03100e", command=self.start_build), "footer.build")
        self.build_btn.pack(side="left", fill="x", expand=True)
        self.trw(ctk.CTkButton(foot, width=120, height=50, fg_color=CARD, command=self.analyze_project), "footer.analyze").pack(side="left", padx=10)
        self.trw(ctk.CTkButton(foot, width=100, height=50, fg_color=CARD, command=self.save_config), "footer.save").pack(side="left")