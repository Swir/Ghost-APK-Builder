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
