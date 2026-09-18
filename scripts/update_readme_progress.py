from __future__ import annotations

import argparse
import math
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROADMAP = ROOT / "ROADMAP.md"
README = ROOT / "README.md"
CARD = ROOT / "assets/readme/progress-card.svg"
MINI = ROOT / "assets/readme/progress-mini.svg"

PROGRESS_RE = re.compile(r"^## Overall progress — ([0-9]+(?:\.[0-9]+)?)%$", re.MULTILINE)
LEGACY_PATTERNS = (
    re.compile(r"[█▓▒░]{4,}"),
    re.compile(r"\[(?:[#=\-]{4,})\]"),
)


def progress() -> float:
    match = PROGRESS_RE.search(ROADMAP.read_text(encoding="utf-8"))
    if not match:
        raise ValueError("ROADMAP.md is missing the authoritative Overall progress heading")
    value = float(match.group(1))
    if not math.isfinite(value) or not 0.0 <= value <= 100.0:
        raise ValueError(f"invalid roadmap progress: {value}")
    return value


def card_svg(value: float) -> str:
    fill = 1100.0 * value / 100.0
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="180" viewBox="0 0 1200 180" role="img" aria-labelledby="title desc">
  <title id="title">Ghost APK Builder v17 roadmap progress</title>
  <desc id="desc">Ghost APK Builder v17 documented roadmap progress is {value:.1f} percent under the repository's existing milestone and release-gate model. Stable release remains blocked on real physical-device verification.</desc>
  <defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop stop-color="#02050A"/><stop offset="1" stop-color="#07111C"/></linearGradient><linearGradient id="fill" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#0088FF"/><stop offset="1" stop-color="#62E5FF"/></linearGradient><pattern id="grid" width="36" height="36" patternUnits="userSpaceOnUse"><path d="M36 0H0V36" fill="none" stroke="#62E5FF" stroke-opacity=".05"/></pattern></defs>
  <rect x="1" y="1" width="1198" height="178" rx="22" fill="url(#bg)" stroke="#62E5FF" stroke-opacity=".24"/><rect x="1" y="1" width="1198" height="178" rx="22" fill="url(#grid)"/>
  <text x="50" y="38" fill="#62E5FF" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="700" letter-spacing="3">SWIR PROGRESS</text>
  <text x="50" y="76" fill="#F4FAFF" font-family="Segoe UI,Arial,sans-serif" font-size="27" font-weight="800">Ghost APK Builder · v17 roadmap</text>
  <text x="50" y="103" fill="#8DA8B8" font-family="Segoe UI,Arial,sans-serif" font-size="14">Documented milestone / release-gate model · stable hardware gate still pending</text>
  <text x="1150" y="76" text-anchor="end" fill="#F4FAFF" font-family="Segoe UI,Arial,sans-serif" font-size="32" font-weight="800">{value:.1f}%</text>
  <rect x="50" y="120" width="1100" height="16" rx="8" fill="#0B1928" stroke="#62E5FF" stroke-opacity=".16"/>
  <rect x="50" y="120" width="{fill:g}" height="16" rx="8" fill="url(#fill)"/>
  <text x="50" y="160" fill="#8DA8B8" font-family="Segoe UI,Arial,sans-serif" font-size="12">PUBLIC BETA · source: ROADMAP.md · stable v17.0.0 is not yet released</text>
</svg>
'''


def mini_svg(value: float) -> str:
    fill = 570.0 * value / 100.0
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="900" height="72" viewBox="0 0 900 72" role="img" aria-labelledby="title desc">
  <title id="title">Ghost APK Builder v17 roadmap progress</title><desc id="desc">Documented v17 roadmap progress is {value:.1f} percent. Stable release still requires real physical-device verification.</desc>
  <defs><linearGradient id="fill" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#0088FF"/><stop offset="1" stop-color="#62E5FF"/></linearGradient></defs>
  <rect x="1" y="1" width="898" height="70" rx="16" fill="#02050A" stroke="#62E5FF" stroke-opacity=".25"/>
  <text x="24" y="27" fill="#F4FAFF" font-family="Segoe UI,Arial,sans-serif" font-size="14" font-weight="700">Ghost v17 · documented roadmap</text>
  <rect x="220" y="28" width="570" height="12" rx="6" fill="#0B1928"/><rect x="220" y="28" width="{fill:g}" height="12" rx="6" fill="url(#fill)"/>
  <text x="868" y="43" text-anchor="end" fill="#62E5FF" font-family="Segoe UI,Arial,sans-serif" font-size="22" font-weight="800">{value:.1f}%</text>
  <text x="24" y="55" fill="#8DA8B8" font-family="Segoe UI,Arial,sans-serif" font-size="11">PUBLIC BETA · physical-device stable gate pending</text>
</svg>
'''


def validate_svg(text: str) -> None:
    root = ET.fromstring(text)
    values = root.attrib.get("viewBox", "").split()
    if root.tag.rsplit("}", 1)[-1] != "svg" or len(values) != 4:
        raise ValueError("invalid SVG root/viewBox")
    for value in values:
        if not math.isfinite(float(value)):
            raise ValueError("non-finite viewBox")


def expected() -> dict[Path, str]:
    value = progress()
    return {CARD: card_svg(value), MINI: mini_svg(value)}


def check() -> int:
    errors: list[str] = []
    value = progress()
    for path, text in expected().items():
        validate_svg(text)
        if not path.exists() or path.read_text(encoding="utf-8") != text:
            errors.append(f"stale generated file: {path.relative_to(ROOT)}")
    for path in (README, ROADMAP):
        text = path.read_text(encoding="utf-8")
        if any(pattern.search(text) for pattern in LEGACY_PATTERNS):
            errors.append(f"legacy progress meter detected in {path.relative_to(ROOT)}")
    if "assets/readme/progress-card.svg" not in README.read_text(encoding="utf-8"):
        errors.append("README does not embed progress-card.svg")
    if "assets/readme/progress-mini.svg" not in ROADMAP.read_text(encoding="utf-8"):
        errors.append("ROADMAP.md does not embed progress-mini.svg")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(f"Ghost APK Builder v17 roadmap: {value:.1f}% (documented milestone/release-gate model)")
    return 0


def write() -> None:
    for path, text in expected().items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        validate_svg(text)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        write()
    return check()


if __name__ == "__main__":
    raise SystemExit(main())
