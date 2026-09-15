from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .model import ProjectConfig

PROFILE_FORMAT = "ghostproject"
PROFILE_VERSION = 1
SECRET_KEYS = {"store_password", "key_password", "keystore_pass", "key_pass"}


def _clean_mapping(data: dict) -> dict:
    safe: dict = {}
    for key, value in data.items():
        if key in SECRET_KEYS:
            continue
        if isinstance(value, dict):
            safe[key] = _clean_mapping(value)
        else:
            safe[key] = value
    return safe


def save_project(path: str | Path, config: ProjectConfig) -> Path:
    target = Path(path)
    if target.suffix.lower() != ".ghostproject":
        target = target.with_suffix(".ghostproject")
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "format": PROFILE_FORMAT,
        "version": PROFILE_VERSION,
        "project": _clean_mapping(asdict(config)),
    }
    tmp = target.with_suffix(target.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)
    return target


def load_project(path: str | Path) -> ProjectConfig:
    source = Path(path)
    raw = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or raw.get("format") != PROFILE_FORMAT:
        raise ValueError("Unsupported Ghost project profile.")
    if int(raw.get("version", 0)) != PROFILE_VERSION:
        raise ValueError("Unsupported Ghost project profile version.")
    data = raw.get("project")
    if not isinstance(data, dict):
        raise ValueError("Ghost project profile is missing project data.")
    cleaned = _clean_mapping(data)
    allowed = set(ProjectConfig.__dataclass_fields__)
    filtered = {k: v for k, v in cleaned.items() if k in allowed}
    return ProjectConfig(**filtered)


class RecentProjects:
    def __init__(self, path: str | Path, limit: int = 8):
        self.path = Path(path)
        self.limit = max(1, int(limit))

    def load(self) -> list[str]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
        except Exception:
            return []
        result: list[str] = []
        for item in raw:
            if not isinstance(item, str):
                continue
            p = Path(item)
            if p.exists() and p.suffix.lower() == ".ghostproject":
                text = str(p)
                if text not in result:
                    result.append(text)
            if len(result) >= self.limit:
                break
        return result

    def add(self, path: str | Path) -> None:
        value = str(Path(path))
        items = [x for x in self.load() if x != value]
        items.insert(0, value)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items[: self.limit], indent=2, ensure_ascii=False), encoding="utf-8")

    def remove(self, path: str | Path) -> None:
        value = str(Path(path))
        items = [x for x in self.load() if x != value]
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(items, indent=2, ensure_ascii=False), encoding="utf-8")
