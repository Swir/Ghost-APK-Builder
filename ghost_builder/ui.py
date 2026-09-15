from __future__ import annotations

import datetime
import queue
import secrets
import string
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from . import ANDROID_API, APP_NAME, BUILD_TOOLS, VERSION
from .builder import GhostBuilder
from .core import ANDROID_LICENSE_URL, ConfigStore, Paths, ToolchainManager
from .generator import DEFAULT_MAIN
from .i18n import Translator, detect_system_language, normalize_language
from .model import ProjectConfig

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

BG = "#05070b"
SURFACE = "#0a1018"
CARD = "#0e1622"
CARD_ALT = "#111d2a"
ENTRY = "#070c12"
BORDER = "#1c2a3a"
ACCENT = "#00e5c3"
ACCENT_HOVER = "#00bfa5"
BLUE = "#5578ff"
PURPLE = "#7c5cff"
TEXT = "#edf4fb"
MUTED = "#8b9aaf"
WARNING = "#f6bd50"
SUCCESS = "#42ef9a"


class GhostApp(ctk.CTk):
    def __init__(self, smoke_test: bool = False):
        super().__init__()
        self.paths = Paths()
        self.store = ConfigStore(self.paths.config)
        saved = self.store.load()
        self.lang = normalize_language(saved.get("language") or detect_system_language())
        self.t = Translator(self.lang)
        self.events: queue.Queue[tuple[str, str]] = queue.Queue()
        self.toolchain = ToolchainManager(self.paths, self._emit)
        self.builder = GhostBuilder(self.toolchain, self._emit)
        self._busy = False
        self._translated: list[tuple[object, str, dict]] = []
        self._tab_names: dict[str, str] = {}

        self.title(f"{APP_NAME} {VERSION}")
        self.geometry("1280x840")
        self.minsize(1040, 700)
        self.configure(fg_color=BG)
        self._build_ui()
        self._load_config(saved)
        self.after(80, self._drain_events)
        self.after(150, self.refresh_engine_status)
        if smoke_test:
            self.after(900, self.destroy)

    def trw(self, widget, key: str, **kwargs):
        widget.configure(text=self.t(key, **kwargs))
        self._translated.append((widget, key, kwargs))
        return widget

    def _build_ui(self) -> None:
        header = ctk.CTkFrame(self, fg_color=BG)
        header.pack(fill="x", padx=26, pady=(18, 8))
        brand = ctk.CTkFrame(header, fg_color="transparent")
        brand.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(brand, text="GHOST", text_color=ACCENT, font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        ctk.CTkLabel(brand, text=" APK BUILDER", text_color=TEXT, font=ctk.CTkFont(size=30, weight="bold")).pack(side="left")
        ctk.CTkLabel(brand, text=f" v{VERSION}", text_color=MUTED, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=8, pady=(11, 0))

        right = ctk.CTkFrame(header, fg_color="transparent")
        right.pack(side="right")
        self.trw(ctk.CTkLabel(right, text_color=MUTED), "lang.label").pack(side="left", padx=(0, 6))
        self.language_var = ctk.StringVar(value="PL" if self.lang == "pl" else "EN")
        ctk.CTkSegmentedButton(
            right, values=["PL", "EN"], variable=self.language_var, command=self._switch_language,
            selected_color=BLUE, selected_hover_color="#4566db", unselected_color=CARD, unselected_hover_color=CARD_ALT,
        ).pack(side="left", padx=(0, 12))
        self.engine_badge = ctk.CTkLabel(right, text=self.t("engine.checking"), fg_color=CARD, corner_radius=12, padx=14, pady=7, text_color=WARNING)
        self.engine_badge.pack(side="left")

        subtitle = ctk.CTkFrame(self, fg_color=BG)
        subtitle.pack(fill="x", padx=28, pady=(0, 10))
        self.trw(ctk.CTkLabel(subtitle, text_color=MUTED, anchor="w"), "app.subtitle").pack(side="left")
        ctk.CTkLabel(subtitle, text=f"API {ANDROID_API} • Build Tools {BUILD_TOOLS} • AGP 9.4 • Gradle 9.6 • JDK 21", text_color="#617087").pack(side="right")

        self.tabs = ctk.CTkTabview(
            self, fg_color=SURFACE, corner_radius=16, segmented_button_fg_color=CARD,
            segmented_button_selected_color=ACCENT, segmented_button_selected_hover_color=ACCENT_HOVER,
            segmented_button_unselected_color=CARD, segmented_button_unselected_hover_color=CARD_ALT,
        )
        self.tabs.pack(fill="both", expand=True, padx=24, pady=(0, 12))
        for key in ("project", "kotlin", "android", "signing", "engine", "logs"):
            name = self.t(f"tab.{key}")
            self._tab_names[key] = name
            self.tabs.add(name)

        self._build_project_tab()
        self._build_kotlin_tab()
        self._build_android_tab()
        self._build_signing_tab()
        self._build_engine_tab()
        self._build_logs_tab()

        footer = ctk.CTkFrame(self, fg_color=BG)
        footer.pack(fill="x", padx=24, pady=(0, 18))
        self.progress = ctk.CTkProgressBar(footer, progress_color=ACCENT, fg_color="#131d29", height=9)
        self.progress.set(0)
        self.progress.pack(fill="x", pady=(0, 10))
        self.build_btn = self.trw(ctk.CTkButton(
            footer, height=50, corner_radius=13, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            text_color="#03100e", font=ctk.CTkFont(size=15, weight="bold"), command=self.start_build,
        ), "footer.build")
        self.build_btn.pack(side="left", fill="x", expand=True)
        self.trw(ctk.CTkButton(footer, width=120, height=50, fg_color=CARD, hover_color=CARD_ALT, command=self.analyze_project), "footer.analyze").pack(side="left", padx=(10, 0))
        self.trw(ctk.CTkButton(footer, width=100, height=50, fg_color=CARD, hover_color=CARD_ALT, command=self.save_config), "footer.save").pack(side="left", padx=(10, 0))

    def _tab(self, key: str):
        return self.tabs.tab(self._tab_names[key])

    def _section(self, parent, title_key: str, subtitle_key: str | None = None, **subtitle_values):
        card = ctk.CTkFrame(parent, fg_color=CARD, corner_radius=15, border_width=1, border_color="#152131")
        card.pack(fill="x", padx=12, pady=10)
        self.trw(ctk.CTkLabel(card, text_color=TEXT, anchor="w", font=ctk.CTkFont(size=16, weight="bold")), title_key).pack(fill="x", padx=18, pady=(15, 2))
        if subtitle_key:
            self.trw(ctk.CTkLabel(card, text_color=MUTED, anchor="w", justify="left", wraplength=1040), subtitle_key, **subtitle_values).pack(fill="x", padx=18, pady=(0, 10))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=18, pady=(4, 16))
        return body

    def _field(self, parent, key: str, default: str = "", show: str | None = None):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", pady=6)
        self.trw(ctk.CTkLabel(row, width=160, anchor="w", text_color=MUTED), key).pack(side="left")
        entry = ctk.CTkEntry(row, fg_color=ENTRY, border_color=BORDER, text_color=TEXT, corner_radius=10, show=show)
        entry.pack(side="left", fill="x", expand=True)
        if default:
            entry.insert(0, default)
        return entry

    def _build_project_tab(self) -> None:
        tab = self._tab("project")
        body = self._section(tab, "project.application", "project.application_sub")
        self.app_name = self._field(body, "project.app_name", "Ghost App")
        self.package_name = self._field(body, "project.package", "com.swir.ghostapp")
        self.icon_path = self._field(body, "project.icon")
        self.trw(ctk.CTkButton(body, fg_color=CARD_ALT, hover_color="#1a2a3b", command=self._pick_icon), "project.browse_icon").pack(anchor="w", padx=(160, 0), pady=4)
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x", pady=6)
        self.trw(ctk.CTkLabel(row, width=160, anchor="w", text_color=MUTED), "project.version").pack(side="left")
        self.version_name = ctk.CTkEntry(row, width=170, fg_color=ENTRY, border_color=BORDER)
        self.version_name.insert(0, "1.0.0")
        self.version_name.pack(side="left")
        self.version_code = ctk.CTkEntry(row, width=110, fg_color=ENTRY, border_color=BORDER)
        self.version_code.insert(0, "1")
        self.version_code.pack(side="left", padx=10)

        out = self._section(tab, "project.output", "project.output_sub")
        self.format_var = ctk.StringVar(value="APK")
        self.mode_var = ctk.StringVar(value="Debug")
        chooser = ctk.CTkFrame(out, fg_color="transparent")
        chooser.pack(fill="x", pady=5)
        ctk.CTkSegmentedButton(chooser, values=["APK", "AAB"], variable=self.format_var, selected_color=ACCENT, selected_hover_color=ACCENT_HOVER).pack(side="left")
        ctk.CTkSegmentedButton(chooser, values=["Debug", "Release"], variable=self.mode_var, selected_color=BLUE, selected_hover_color="#4566db").pack(side="left", padx=12)
        self.output_dir = self._field(out, "project.output_folder", str(Path.home() / "Desktop"))
        self.trw(ctk.CTkButton(out, fg_color=CARD_ALT, hover_color="#1a2a3b", command=self._pick_output), "project.browse_output").pack(anchor="w", padx=(160, 0), pady=4)

    def _build_kotlin_tab(self) -> None:
        tab = self._tab("kotlin")
        ctk.CTkLabel(tab, text="MainActivity.kt", text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=14, pady=(12, 3))
        self.trw(ctk.CTkLabel(tab, text_color=MUTED, anchor="w"), "kotlin.description").pack(anchor="w", padx=14, pady=(0, 8))
        self.code = ctk.CTkTextbox(tab, font=("Cascadia Mono", 13), fg_color="#060a0f", text_color="#d8e8e5", border_width=1, border_color=BORDER, corner_radius=12, undo=True)
        self.code.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.code.insert("1.0", DEFAULT_MAIN)

    def _build_android_tab(self) -> None:
        tab = self._tab("android")
        sdk = self._section(tab, "android.target", "android.target_sub", api=ANDROID_API, build_tools=BUILD_TOOLS)
        row = ctk.CTkFrame(sdk, fg_color="transparent")
        row.pack(fill="x")
        self.trw(ctk.CTkLabel(row, text_color=MUTED), "android.min_sdk").pack(side="left")
        self.min_sdk = ctk.CTkEntry(row, width=75, fg_color=ENTRY, border_color=BORDER)
        self.min_sdk.insert(0, "24")
        self.min_sdk.pack(side="left", padx=(8, 24))
        self.trw(ctk.CTkLabel(row, text_color=MUTED), "android.target_sdk").pack(side="left")
        self.target_sdk = ctk.CTkEntry(row, width=75, fg_color=ENTRY, border_color=BORDER)
        self.target_sdk.insert(0, str(ANDROID_API))
        self.target_sdk.pack(side="left", padx=(8, 24))
        self.trw(ctk.CTkLabel(row, text_color=MUTED), "android.orientation").pack(side="left")
        self.orientation = ctk.StringVar(value="unspecified")
        ctk.CTkOptionMenu(row, values=["unspecified", "portrait", "landscape"], variable=self.orientation, fg_color=CARD_ALT).pack(side="left", padx=8)

        perms = self._section(tab, "android.permissions", "android.permissions_sub")
        self.internet = ctk.BooleanVar(value=True)
        self.camera = ctk.BooleanVar(value=False)
        self.location = ctk.BooleanVar(value=False)
        self.microphone = ctk.BooleanVar(value=False)
        self.cleartext = ctk.BooleanVar(value=False)
        self.backup = ctk.BooleanVar(value=False)
        for key, var in (("android.internet", self.internet), ("android.camera", self.camera), ("android.location", self.location), ("android.microphone", self.microphone), ("android.cleartext", self.cleartext), ("android.backup", self.backup)):
            self.trw(ctk.CTkCheckBox(perms, variable=var, fg_color=ACCENT, hover_color=ACCENT_HOVER), key).pack(side="left", padx=(0, 16), pady=8)

        runtime = self._section(tab, "android.runtime")
        self.splash = ctk.BooleanVar(value=True)
        self.fullscreen = ctk.BooleanVar(value=False)
        self.hardware = ctk.BooleanVar(value=True)
        self.minify = ctk.BooleanVar(value=False)
        self.adb_deploy = ctk.BooleanVar(value=False)
        for key, var in (("android.splash", self.splash), ("android.fullscreen", self.fullscreen), ("android.hardware", self.hardware), ("android.minify", self.minify), ("android.adb", self.adb_deploy)):
            self.trw(ctk.CTkCheckBox(runtime, variable=var, fg_color=ACCENT, hover_color=ACCENT_HOVER), key).pack(side="left", padx=(0, 14), pady=8)
        self.assets = self._field(runtime, "project.assets")
        self.trw(ctk.CTkButton(runtime, fg_color=CARD_ALT, hover_color="#1a2a3b", command=self._pick_assets), "project.browse_assets").pack(anchor="w", padx=(160, 0), pady=4)

    def _build_signing_tab(self) -> None:
        tab = self._tab("signing")
        body = self._section(tab, "signing.title", "signing.subtitle")
        self.signing = ctk.BooleanVar(value=False)
        self.trw(ctk.CTkCheckBox(body, variable=self.signing, fg_color=ACCENT, hover_color=ACCENT_HOVER), "signing.enable").pack(anchor="w", pady=(0, 10))
        self.keystore = self._field(body, "signing.keystore")
        self.trw(ctk.CTkButton(body, fg_color=CARD_ALT, hover_color="#1a2a3b", command=self._pick_keystore), "signing.browse").pack(anchor="w", padx=(160, 0), pady=4)
        self.alias = self._field(body, "signing.alias", "ghost_key")
        self.store_password = self._field(body, "signing.store_password", show="•")
        self.key_password = self._field(body, "signing.key_password", show="•")
        self.trw(ctk.CTkButton(body, fg_color=PURPLE, hover_color="#6749e0", command=self.generate_keystore), "signing.generate").pack(anchor="w", padx=(160, 0), pady=(8, 4))
        self.trw(ctk.CTkLabel(body, text_color=MUTED, wraplength=760, justify="left"), "signing.notice").pack(anchor="w", padx=(160, 0))

    def _build_engine_tab(self) -> None:
        tab = self._tab("engine")
        body = self._section(tab, "engine.title", "engine.subtitle")
        self.engine_text = ctk.CTkTextbox(body, height=245, fg_color="#060a0f", border_width=1, border_color=BORDER, text_color=TEXT, font=("Cascadia Mono", 12))
        self.engine_text.pack(fill="x", pady=(0, 12))
        self.engine_text.configure(state="disabled")
        row = ctk.CTkFrame(body, fg_color="transparent")
        row.pack(fill="x")
        self.trw(ctk.CTkButton(row, fg_color=CARD_ALT, hover_color="#1a2a3b", command=self.refresh_engine_status), "engine.refresh").pack(side="left")
        self.trw(ctk.CTkButton(row, fg_color=ACCENT, hover_color=ACCENT_HOVER, text_color="#04100e", command=self.prepare_engine), "engine.prepare").pack(side="left", padx=10)
        self.trw(ctk.CTkButton(row, fg_color=PURPLE, hover_color="#6749e0", command=self.repair_engine), "engine.repair").pack(side="left")
        self.trw(ctk.CTkButton(row, fg_color=CARD_ALT, hover_color="#1a2a3b", command=lambda: webbrowser.open(ANDROID_LICENSE_URL)), "engine.terms").pack(side="right")
        self.trw(ctk.CTkLabel(body, text_color=MUTED, anchor="w", justify="left"), "engine.privacy").pack(fill="x", pady=(12, 0))

    def _build_logs_tab(self) -> None:
        tab = self._tab("logs")
        header = ctk.CTkFrame(tab, fg_color="transparent")
        header.pack(fill="x", padx=14, pady=(12, 4))
        self.trw(ctk.CTkLabel(header, text_color=TEXT, font=ctk.CTkFont(size=16, weight="bold")), "logs.title").pack(side="left")
        self.trw(ctk.CTkButton(header, width=100, fg_color=CARD_ALT, command=self._copy_logs), "logs.copy").pack(side="right")
        self.trw(ctk.CTkButton(header, width=100, fg_color=CARD_ALT, command=self._clear_logs), "logs.clear").pack(side="right", padx=8)
        self.trw(ctk.CTkButton(header, width=100, fg_color=CARD_ALT, command=self._export_logs), "logs.export").pack(side="right")
        self.logs = ctk.CTkTextbox(tab, font=("Cascadia Mono", 12), fg_color="#05080c", text_color="#c9d5e4", border_width=1, border_color=BORDER)
        self.logs.pack(fill="both", expand=True, padx=14, pady=(4, 14))
        self.logs.configure(state="disabled")

    def _switch_language(self, display_value: str) -> None:
        new = "pl" if display_value == "PL" else "en"
        if new == self.lang:
            return
        self.lang = new
        self.t.set_language(new)
        data = self.store.load()
        data["language"] = new
        self.store.save(data)
        for widget, key, kwargs in self._translated:
            try:
                widget.configure(text=self.t(key, **kwargs))
            except Exception:
                pass
        for key in list(self._tab_names):
            old = self._tab_names[key]
            new_name = self.t(f"tab.{key}")
            try:
                self.tabs.rename(old, new_name)
                self._tab_names[key] = new_name
            except Exception:
                pass
        self.refresh_engine_status()
        self._append_log("info", self.t("msg.language_changed"))

    def _emit(self, level: str, message: str) -> None:
        self.events.put((level, message))

    def _drain_events(self) -> None:
        try:
            while True:
                level, message = self.events.get_nowait()
                if level == "progress" and ":" in message:
                    try:
                        self.progress.set(max(0, min(1, int(message.rsplit(":", 1)[1]) / 100)))
                    except ValueError:
                        pass
                elif level == "__engine_done__":
                    self._set_busy(False)
                    self.refresh_engine_status()
                elif level == "__build_success__":
                    self.progress.set(1)
                    self._set_busy(False)
                    self._append_log("success", message)
                    messagebox.showinfo(self.t("msg.build_complete_title"), self.t("msg.build_complete", path=message))
                elif level == "__build_error__":
                    self.progress.set(0)
                    self._set_busy(False)
                    self._append_log("error", message)
                    messagebox.showerror(self.t("msg.build_failed"), message)
                else:
                    self._append_log(level, message)
        except queue.Empty:
            pass
        self.after(80, self._drain_events)

    def _append_log(self, level: str, message: str) -> None:
        stamp = datetime.datetime.now().strftime("%H:%M:%S")
        self.logs.configure(state="normal")
        self.logs.insert("end", f"[{stamp}] {level.upper():7} {message}\n")
        self.logs.see("end")
        self.logs.configure(state="disabled")

    def _set_busy(self, busy: bool, key: str | None = None) -> None:
        self._busy = busy
        self.build_btn.configure(state="disabled" if busy else "normal", text=self.t(key or "busy.building") if busy else self.t("footer.build"))

    def _copy_logs(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.logs.get("1.0", "end").strip())
        self._append_log("info", self.t("msg.logs_copied"))

    def _clear_logs(self) -> None:
        self.logs.configure(state="normal")
        self.logs.delete("1.0", "end")
        self.logs.configure(state="disabled")

    def _export_logs(self) -> None:
        path = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")], initialfile=f"Ghost-Logs-{datetime.datetime.now():%Y%m%d-%H%M%S}.txt")
        if path:
            Path(path).write_text(self.logs.get("1.0", "end"), encoding="utf-8")
            self._append_log("success", self.t("msg.logs_exported", path=path))

    def _pick_output(self) -> None:
        self._set_entry_from_dialog(self.output_dir, filedialog.askdirectory())

    def _pick_assets(self) -> None:
        self._set_entry_from_dialog(self.assets, filedialog.askdirectory())

    def _pick_icon(self) -> None:
        self._set_entry_from_dialog(self.icon_path, filedialog.askopenfilename(filetypes=[("PNG/JPEG", "*.png *.jpg *.jpeg *.webp")]))

    def _pick_keystore(self) -> None:
        self._set_entry_from_dialog(self.keystore, filedialog.askopenfilename(filetypes=[("Java Keystore", "*.jks *.keystore")]))

    @staticmethod
    def _set_entry_from_dialog(entry, value: str) -> None:
        if value:
            entry.delete(0, "end")
            entry.insert(0, value)

    @staticmethod
    def _int_or(value: str, fallback: int = 0) -> int:
        try:
            return int(value.strip())
        except Exception:
            return fallback

    def _config(self) -> ProjectConfig:
        return ProjectConfig(
            app_name=self.app_name.get().strip(), package_name=self.package_name.get().strip(),
            version_name=self.version_name.get().strip(), version_code=self._int_or(self.version_code.get()),
            min_sdk=self._int_or(self.min_sdk.get()), target_sdk=self._int_or(self.target_sdk.get()),
            build_mode=self.mode_var.get(), export_format=self.format_var.get(), orientation=self.orientation.get(),
            fullscreen=self.fullscreen.get(), hardware_accel=self.hardware.get(), allow_backup=self.backup.get(),
            allow_cleartext=self.cleartext.get(), permission_internet=self.internet.get(), permission_camera=self.camera.get(),
            permission_location=self.location.get(), permission_microphone=self.microphone.get(), use_splash=self.splash.get(),
            minify_release=self.minify.get(), signing_enabled=self.signing.get(), keystore_path=self.keystore.get().strip(),
            key_alias=self.alias.get().strip(), output_dir=self.output_dir.get().strip(), custom_source=self.code.get("1.0", "end"),
            extra_assets=self.assets.get().strip(), icon_path=self.icon_path.get().strip(), deploy_adb=self.adb_deploy.get(),
        )

    def _validation_messages(self, cfg: ProjectConfig) -> list[str]:
        return [self.t(f"validation.{code}") for code in cfg.validation_codes()]

    def analyze_project(self) -> None:
        errors = self._validation_messages(self._config())
        if errors:
            for error in errors:
                self._append_log("error", error)
            messagebox.showerror(self.t("msg.project_check"), "\n\n".join(errors))
        else:
            self._append_log("success", self.t("msg.project_passed"))
            messagebox.showinfo(self.t("msg.project_check"), self.t("msg.project_ready", api=ANDROID_API))

    def save_config(self) -> None:
        data = self._config().to_persisted_dict()
        data["language"] = self.lang
        self.store.save(data)
        self._append_log("success", self.t("msg.saved", path=self.paths.config))

    def _load_config(self, data: dict) -> None:
        entries = {
            "app_name": self.app_name, "package_name": self.package_name, "version_name": self.version_name,
            "version_code": self.version_code, "output_dir": self.output_dir, "keystore_path": self.keystore,
            "key_alias": self.alias, "extra_assets": self.assets, "icon_path": self.icon_path,
            "min_sdk": self.min_sdk, "target_sdk": self.target_sdk,
        }
        for key, widget in entries.items():
            if data.get(key) not in (None, ""):
                widget.delete(0, "end")
                widget.insert(0, str(data[key]))
        for key, var in {"build_mode": self.mode_var, "export_format": self.format_var, "orientation": self.orientation}.items():
            if key in data:
                var.set(data[key])
        bools = {
            "permission_internet": self.internet, "permission_camera": self.camera, "permission_location": self.location,
            "permission_microphone": self.microphone, "allow_cleartext": self.cleartext, "allow_backup": self.backup,
            "use_splash": self.splash, "fullscreen": self.fullscreen, "hardware_accel": self.hardware,
            "minify_release": self.minify, "signing_enabled": self.signing, "deploy_adb": self.adb_deploy,
        }
        for key, var in bools.items():
            if key in data:
                var.set(bool(data[key]))

    def refresh_engine_status(self) -> None:
        status = self.toolchain.status()
        ready = self.toolchain.ready()
        self.engine_badge.configure(text=self.t("engine.ready") if ready else self.t("engine.setup"), text_color=SUCCESS if ready else WARNING)
        self.engine_text.configure(state="normal")
        self.engine_text.delete("1.0", "end")
        for key, value in status.items():
            self.engine_text.insert("end", f"{key:25} {value}\n")
        self.engine_text.configure(state="disabled")

    def prepare_engine(self) -> None:
        if self._busy:
            return
        if not messagebox.askyesno(self.t("msg.sdk_license_title"), self.t("msg.sdk_license")):
            return
        self._run_engine(lambda: self.toolchain.provision(accept_android_sdk_license=True), "busy.preparing")

    def repair_engine(self) -> None:
        if self._busy:
            return
        if not messagebox.askyesno(self.t("msg.sdk_license_title"), self.t("msg.sdk_license")):
            return
        self._run_engine(lambda: self.toolchain.repair(accept_android_sdk_license=True), "busy.repairing")

    def _run_engine(self, operation, label_key: str) -> None:
        self._set_busy(True, label_key)
        self.tabs.set(self._tab_names["logs"])
        def worker() -> None:
            try:
                operation()
                self.events.put(("success", self.t("msg.engine_done")))
            except Exception as exc:
                self.events.put(("error", str(exc)))
            finally:
                self.events.put(("__engine_done__", ""))
        threading.Thread(target=worker, daemon=True).start()

    def generate_keystore(self) -> None:
        if not self.toolchain.keytool_exe():
            messagebox.showerror(self.t("tab.engine"), self.t("msg.engine_unavailable"))
            return
        path = filedialog.asksaveasfilename(defaultextension=".jks", filetypes=[("Java Keystore", "*.jks")], initialfile="ghost-release.jks")
        if not path:
            return
        alphabet = string.ascii_letters + string.digits + "-_"
        password = "".join(secrets.choice(alphabet) for _ in range(24))
        alias = self.alias.get().strip() or "ghost_key"
        try:
            self.builder.generate_keystore(Path(path), password, alias)
            self._set_entry_from_dialog(self.keystore, path)
            self.alias.delete(0, "end"); self.alias.insert(0, alias)
            self.store_password.delete(0, "end"); self.store_password.insert(0, password)
            self.key_password.delete(0, "end"); self.key_password.insert(0, password)
            self.signing.set(True)
            messagebox.showinfo(self.t("msg.keystore_created_title"), self.t("msg.keystore_created", alias=alias, password=password))
        except Exception as exc:
            messagebox.showerror(self.t("msg.keystore_error"), str(exc))

    def start_build(self) -> None:
        if self._busy:
            return
        cfg = self._config()
        errors = self._validation_messages(cfg)
        if errors:
            messagebox.showerror(self.t("msg.cannot_build"), "\n\n".join(errors))
            return
        if not self.toolchain.ready():
            messagebox.showwarning(self.t("tab.engine"), self.t("msg.engine_not_ready"))
            self.tabs.set(self._tab_names["engine"])
            return
        store_pw, key_pw = self.store_password.get(), self.key_password.get()
        self.save_config()
        self.progress.set(0.08)
        self._set_busy(True, "busy.building")
        self.tabs.set(self._tab_names["logs"])
        def worker() -> None:
            try:
                path = self.builder.build(cfg, store_pw, key_pw)
                self.events.put(("__build_success__", str(path)))
            except Exception as exc:
                self.events.put(("__build_error__", str(exc)))
        threading.Thread(target=worker, daemon=True).start()
