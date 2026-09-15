from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from .model import ProjectConfig


class BuildHistoryStore:
    def __init__(self, path: Path, limit: int = 50):
        self.path = Path(path)
        self.limit = max(1, int(limit))

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest().lower()

    def load(self) -> list[dict]:
        try:
            raw = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(raw, list):
                return []
            return [item for item in raw if isinstance(item, dict)][: self.limit]
        except Exception:
            return []

    def record(self, artifact: Path, cfg: ProjectConfig, duration_seconds: float | None = None) -> dict:
        artifact = Path(artifact)
        item = {
            "timestamp": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "artifact": str(artifact.resolve()),
            "app_name": cfg.app_name,
            "package_name": cfg.package_name,
            "version_name": cfg.version_name,
            "version_code": cfg.version_code,
            "format": cfg.export_format,
            "mode": cfg.build_mode,
            "signed": bool(cfg.signing_enabled),
            "size_bytes": artifact.stat().st_size if artifact.exists() else 0,
            "sha256": self._sha256(artifact) if artifact.exists() else "",
        }
        if duration_seconds is not None:
            item["duration_seconds"] = round(max(0.0, float(duration_seconds)), 2)
        history = [item]
        history.extend(entry for entry in self.load() if entry.get("artifact") != item["artifact"])
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(history[: self.limit], indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)
        return item
