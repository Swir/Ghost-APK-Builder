from __future__ import annotations

import re

_FINGERPRINT_RE = re.compile(r"^\s*(SHA1|SHA256):\s*([0-9A-Fa-f:]+)\s*$", re.MULTILINE)


def parse_keytool_fingerprints(text: str) -> dict[str, str]:
    found = {name.upper(): value.upper() for name, value in _FINGERPRINT_RE.findall(text or "")}
    result: dict[str, str] = {}
    if found.get("SHA1"):
        result["SHA1"] = found["SHA1"]
    if found.get("SHA256"):
        result["SHA256"] = found["SHA256"]
    return result
