from __future__ import annotations

import os
import threading
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

from .ui_theme import ACCENT, BG, BLUE, CARD, MUTED, SUCCESS, SURFACE, TEXT


def format_bytes(size: int) -> str:
    value = max(0, int(size or 0))
    units = ("B", "KB", "MB", "GB")
    number = float(value)
    for unit in units:
        if number < 1024 or unit == units[-1]:
            return f"{number:.0f} {unit}" if unit == "B" else f"{number:.2f} {unit}"
        number /= 1024
    return f"{value} B"


def result_summary(item: dict) -> dict[str, str]:
    return {
        "artifact": str(item.get("artifact", "")),
        "app": str(item.get("app_name", "Ghost App")),
        "version": str(item.get("version_name", "?")),
        "format": str(item.get("format", "?")),
        "mode": str(item.get("mode", "?")),
        "size": format_bytes(int(item.get("size_bytes", 0) or 0)),
        "duration": f"{float(item.get('duration_seconds', 0) or 0):.2f} s",
        "sha256": str(item.get("sha256", "")),
        "signed": "yes" if item.get("signed") else "no",
    }


class BuildResultMixin:
    def _copy_result_value(self, value: str, label: str) -> None:
        self.clipboard_clear()
        self.clipboard_append(value)
        self._append_log("info", f"Copied {label}")

    @staticmethod
    def _open_result_file(path: Path) -> None:
        if path.exists() and os.name == "nt":
            os.startfile(str(path))

    @staticmethod
    def _open_result_folder(path: Path) -> None:
        folder = path.parent
        if folder.exists() and os.name == "nt":
            os.startfile(str(folder))

    def _install_result_apk(self, path: Path, cfg, button) -> None:
        pl = self.lang == "pl"
        button.configure(state="disabled", text="Instalowanie…" if pl else "Installing…")

        def worker():
            try:
                activity = ".SplashActivity" if cfg.use_splash else ".MainActivity"
                self.builder.deploy_to_connected_device(path, cfg.package_name, activity)
                self.after(0, lambda: messagebox.showinfo("ADB", "APK zainstalowany i uruchomiony." if pl else "APK installed and launched."))
            except Exception as exc:
                self.after(0, lambda: messagebox.showerror("ADB", str(exc)))
            finally:
                self.after(0, lambda: button.configure(state="normal", text="Zainstaluj przez ADB" if pl else "Install via ADB"))

        threading.Thread(target=worker, daemon=True).start()

    def show_build_result(self, item: dict, cfg) -> None:
        pl = self.lang == "pl"
        data = result_summary(item)
        artifact = Path(data["artifact"])

        win = ctk.CTkToplevel(self)
        win.title("Build ukończony" if pl else "Build complete")
        win.geometry("760x590")
        win.minsize(700, 540)
        win.configure(fg_color=BG)
        win.transient(self)
        win.grab_set()
        win.bind("<Escape>", lambda _event: win.destroy())

        ctk.CTkLabel(win, text="✓", text_color=SUCCESS, font=ctk.CTkFont(size=46, weight="bold")).pack(pady=(24, 0))
        ctk.CTkLabel(
            win,
            text="BUILD GOTOWY" if pl else "BUILD COMPLETE",
            text_color=TEXT,
            font=ctk.CTkFont(size=25, weight="bold"),
        ).pack(pady=(0, 4))
        ctk.CTkLabel(
            win,
            text=f"{data['app']}  •  v{data['version']}  •  {data['mode']} {data['format']}",
            text_color=MUTED,
        ).pack(pady=(0, 16))

        card = ctk.CTkFrame(win, fg_color=SURFACE, corner_radius=16, border_width=1, border_color="#173044")
        card.pack(fill="x", padx=24, pady=6)

        rows = [
            ("Plik" if pl else "Artifact", artifact.name),
            ("Rozmiar" if pl else "Size", data["size"]),
            ("Czas builda" if pl else "Build time", data["duration"]),
            ("Podpisany" if pl else "Signed", "Tak" if item.get("signed") and pl else "Yes" if item.get("signed") else "Nie" if pl else "No"),
            ("SHA-256", data["sha256"]),
        ]
        for index, (label, value) in enumerate(rows):
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=(10 if index == 0 else 4, 10 if index == len(rows) - 1 else 4))
            ctk.CTkLabel(row, text=label, width=120, anchor="w", text_color=MUTED).pack(side="left")
            ctk.CTkLabel(row, text=value, anchor="w", text_color=TEXT, wraplength=540, justify="left").pack(side="left", fill="x", expand=True)

        actions = ctk.CTkFrame(win, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(18, 8))
        ctk.CTkButton(
            actions,
            text="Otwórz plik" if pl else "Open file",
            fg_color=ACCENT,
            text_color="#04100e",
            command=lambda: BuildResultMixin._open_result_file(artifact),
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))
        ctk.CTkButton(
            actions,
            text="Otwórz folder" if pl else "Open folder",
            fg_color=BLUE,
            command=lambda: BuildResultMixin._open_result_folder(artifact),
        ).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkButton(
            actions,
            text="Kopiuj ścieżkę" if pl else "Copy path",
            fg_color=CARD,
            command=lambda: BuildResultMixin._copy_result_value(self, str(artifact), "artifact path"),
        ).pack(side="left", fill="x", expand=True, padx=(5, 0))

        second = ctk.CTkFrame(win, fg_color="transparent")
        second.pack(fill="x", padx=24, pady=4)
        ctk.CTkButton(
            second,
            text="Kopiuj SHA-256" if pl else "Copy SHA-256",
            fg_color=CARD,
            command=lambda: BuildResultMixin._copy_result_value(self, data["sha256"], "SHA-256"),
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        if cfg.export_format == "APK":
            adb_btn = ctk.CTkButton(
                second,
                text="Zainstaluj przez ADB" if pl else "Install via ADB",
                fg_color=BLUE,
            )
            adb_btn.configure(command=lambda: BuildResultMixin._install_result_apk(self, artifact, cfg, adb_btn))
            adb_btn.pack(side="left", fill="x", expand=True, padx=(5, 0))
        else:
            ctk.CTkButton(
                second,
                text="Historia buildów" if pl else "Build history",
                fg_color=BLUE,
                command=lambda: (win.destroy(), self.show_build_history()),
            ).pack(side="left", fill="x", expand=True, padx=(5, 0))

        close_btn = ctk.CTkButton(win, text="Zamknij" if pl else "Close", fg_color=CARD, command=win.destroy, height=42)
        close_btn.pack(fill="x", padx=24, pady=(12, 20))
        close_btn.focus_set()
