from __future__ import annotations

import queue

import customtkinter as ctk

from . import ANDROID_API, APP_NAME, BUILD_TOOLS, VERSION
from .builder import GhostBuilder
from .core import ConfigStore, Paths, ToolchainManager
from .i18n import Translator, detect_system_language, normalize_language
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
        self._load_config(saved)
        self._apply_ui_mode(self.ui_mode, persist=False)
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

    def save_config(self, quiet=False):
        ActionsMixin.save_config(self, quiet=quiet)
        data = self.store.load()
        data["ui_mode"] = self.ui_mode
        self.store.save(data)

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
        self.mode_switch = ctk.CTkSegmentedButton(
            head,
            values=[simple_label, advanced_label],
            variable=self.ui_mode_var,
            command=self._switch_ui_mode,
            selected_color=ACCENT,
            selected_hover_color="#18f0d0",
            unselected_color=CARD,
        )
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
