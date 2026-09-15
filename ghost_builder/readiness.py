from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .model import ProjectConfig


@dataclass(frozen=True)
class ReadinessIssue:
    code: str
    severity: str


@dataclass(frozen=True)
class ReadinessReport:
    ready: bool
    issues: tuple[ReadinessIssue, ...]

    @property
    def errors(self) -> tuple[ReadinessIssue, ...]:
        return tuple(x for x in self.issues if x.severity == "error")

    @property
    def warnings(self) -> tuple[ReadinessIssue, ...]:
        return tuple(x for x in self.issues if x.severity == "warning")


def check_play_readiness(cfg: ProjectConfig) -> ReadinessReport:
    issues: list[ReadinessIssue] = []
    validation = set(cfg.validation_codes())
    for code in ("app_name_required", "package", "version_name", "version_code", "target_sdk", "sdk_order"):
        if code in validation:
            issues.append(ReadinessIssue(code, "error"))
    if cfg.target_sdk < 36:
        issues.append(ReadinessIssue("play_target_api", "error"))
    if cfg.build_mode != "Release":
        issues.append(ReadinessIssue("play_release_required", "error"))
    if cfg.export_format != "AAB":
        issues.append(ReadinessIssue("play_aab_recommended", "warning"))
    if not cfg.signing_enabled:
        issues.append(ReadinessIssue("play_signing_required", "error"))
    else:
        if not cfg.keystore_path or not Path(cfg.keystore_path).is_file():
            issues.append(ReadinessIssue("play_keystore_missing", "error"))
        if not cfg.key_alias.strip():
            issues.append(ReadinessIssue("play_alias_missing", "error"))
    if not cfg.icon_path:
        issues.append(ReadinessIssue("play_icon_default", "warning"))
    elif not Path(cfg.icon_path).is_file():
        issues.append(ReadinessIssue("play_icon_missing", "error"))
    if cfg.allow_cleartext:
        issues.append(ReadinessIssue("play_cleartext_enabled", "warning"))
    if cfg.allow_backup:
        issues.append(ReadinessIssue("play_backup_enabled", "warning"))
    seen: set[tuple[str, str]] = set()
    unique: list[ReadinessIssue] = []
    for issue in issues:
        key = (issue.code, issue.severity)
        if key not in seen:
            seen.add(key)
            unique.append(issue)
    return ReadinessReport(not any(x.severity == "error" for x in unique), tuple(unique))
