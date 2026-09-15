from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

_PACKAGE_RE = re.compile(r"^[a-z][a-z0-9_]*(?:\.[a-z][a-z0-9_]*)+$")
_VERSION_RE = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._+-]{0,63}$")

VALIDATION_MESSAGES_EN = {
    "app_name_required": "Application name is required.",
    "app_name_long": "Application name must be 80 characters or fewer.",
    "package": "Package name must look like com.example.app and every segment must start with a letter.",
    "version_name": "Version name contains unsupported characters.",
    "version_code": "Version code must be a positive integer.",
    "min_sdk": "Min SDK must be between 23 and 36 for the v17 build profile.",
    "target_sdk": "Target SDK must be API 36 or newer for current Google Play submission requirements.",
    "sdk_order": "Min SDK cannot be higher than Target SDK.",
    "build_mode": "Build mode must be Debug or Release.",
    "export_format": "Export format must be APK or AAB.",
    "orientation": "Unsupported screen orientation.",
    "splash_color": "Splash background must be a #RRGGBB color.",
    "status_color": "Status bar color must be a #RRGGBB color.",
    "keystore_missing": "Release signing is enabled but the keystore file is missing.",
    "alias_missing": "Release signing is enabled but the key alias is empty.",
    "assets_missing": "Assets folder does not exist.",
    "icon_missing": "Selected app icon does not exist.",
}


@dataclass
class ProjectConfig:
    app_name: str = "Ghost App"
    package_name: str = "com.swir.ghostapp"
    version_name: str = "1.0.0"
    version_code: int = 1
    min_sdk: int = 24
    target_sdk: int = 36
    build_mode: str = "Debug"
    export_format: str = "APK"
    orientation: str = "unspecified"
    fullscreen: bool = False
    dark_mode: bool = True
    hardware_accel: bool = True
    allow_backup: bool = False
    allow_cleartext: bool = False
    permission_internet: bool = True
    permission_camera: bool = False
    permission_location: bool = False
    permission_microphone: bool = False
    use_splash: bool = True
    splash_background: str = "#080B12"
    status_bar_color: str = "#080B12"
    minify_release: bool = False
    signing_enabled: bool = False
    keystore_path: str = ""
    key_alias: str = ""
    output_dir: str = ""
    custom_source: str = ""
    extra_assets: str = ""
    icon_path: str = ""
    deploy_adb: bool = False
    metadata: dict = field(default_factory=dict)

    def validation_codes(self) -> list[str]:
        errors: list[str] = []
        if not self.app_name.strip():
            errors.append("app_name_required")
        if len(self.app_name.strip()) > 80:
            errors.append("app_name_long")
        if not _PACKAGE_RE.fullmatch(self.package_name.strip()):
            errors.append("package")
        if not _VERSION_RE.fullmatch(self.version_name.strip()):
            errors.append("version_name")
        if not isinstance(self.version_code, int) or self.version_code < 1:
            errors.append("version_code")
        try:
            min_sdk = int(self.min_sdk)
            target_sdk = int(self.target_sdk)
        except (TypeError, ValueError):
            min_sdk, target_sdk = 0, 0
        if not (23 <= min_sdk <= 36):
            errors.append("min_sdk")
        if target_sdk < 36:
            errors.append("target_sdk")
        if min_sdk > target_sdk:
            errors.append("sdk_order")
        if self.build_mode not in {"Debug", "Release"}:
            errors.append("build_mode")
        if self.export_format not in {"APK", "AAB"}:
            errors.append("export_format")
        if self.orientation not in {"unspecified", "portrait", "landscape"}:
            errors.append("orientation")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", self.splash_background):
            errors.append("splash_color")
        if not re.fullmatch(r"#[0-9A-Fa-f]{6}", self.status_bar_color):
            errors.append("status_color")
        if self.signing_enabled:
            if not self.keystore_path or not Path(self.keystore_path).is_file():
                errors.append("keystore_missing")
            if not self.key_alias.strip():
                errors.append("alias_missing")
        if self.extra_assets and not Path(self.extra_assets).is_dir():
            errors.append("assets_missing")
        if self.icon_path and not Path(self.icon_path).is_file():
            errors.append("icon_missing")
        return errors

    def validate(self) -> list[str]:
        return [VALIDATION_MESSAGES_EN[code] for code in self.validation_codes()]

    def to_persisted_dict(self) -> dict:
        data = asdict(self)
        data.pop("custom_source", None)
        return data
