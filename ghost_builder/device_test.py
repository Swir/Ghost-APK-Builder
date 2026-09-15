from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .core import ToolchainManager


@dataclass(frozen=True)
class DeviceState:
    serial: str
    state: str


@dataclass(frozen=True)
class DeviceTestReport:
    passed: bool
    serial: str
    package_name: str
    artifact: str
    package_path: str
    launch_output: str
    timestamp: str


def parse_adb_devices(text: str) -> tuple[DeviceState, ...]:
    items: list[DeviceState] = []
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line or line.startswith("List of devices attached") or line.startswith("*"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            items.append(DeviceState(parts[0], parts[1]))
    return tuple(items)


def save_device_test_report(path: Path, report: DeviceTestReport) -> Path:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(asdict(report), indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(target)
    return target


class PhysicalDeviceVerifier:
    def __init__(self, toolchain: ToolchainManager):
        self.toolchain = toolchain

    def _run(self, args: list[str]) -> subprocess.CompletedProcess[str]:
        adb = self.toolchain.adb_exe()
        if not adb:
            raise RuntimeError("ADB is unavailable. Prepare Build Engine first.")
        return subprocess.run(
            [str(adb), *args],
            env=self.toolchain.env(),
            capture_output=True,
            text=True,
            shell=False,
        )

    def run(self, apk: Path, package_name: str, activity: str) -> DeviceTestReport:
        apk = Path(apk)
        if not apk.is_file():
            raise FileNotFoundError(f"APK not found: {apk}")
        if apk.suffix.lower() != ".apk":
            raise ValueError("Physical device verification requires an APK artifact.")

        start = self._run(["start-server"])
        if start.returncode != 0:
            raise RuntimeError((start.stdout + "\n" + start.stderr).strip())

        devices_result = self._run(["devices"])
        if devices_result.returncode != 0:
            raise RuntimeError((devices_result.stdout + "\n" + devices_result.stderr).strip())
        devices = parse_adb_devices(devices_result.stdout)
        ready = [item for item in devices if item.state == "device"]
        blocked = [item for item in devices if item.state in {"unauthorized", "offline"}]
        if not ready:
            if blocked:
                states = ", ".join(f"{item.serial}: {item.state}" for item in blocked)
                raise RuntimeError(f"No authorized Android device is ready ({states}). Unlock the phone and allow USB debugging.")
            raise RuntimeError("No Android device detected. Connect one phone with USB debugging enabled.")
        if len(ready) > 1:
            raise RuntimeError("More than one Android device is connected. Leave one test device connected and try again.")

        serial = ready[0].serial
        install = self._run(["-s", serial, "install", "-r", str(apk)])
        if install.returncode != 0 or "Success" not in (install.stdout + install.stderr):
            raise RuntimeError("APK install failed:\n" + install.stdout + install.stderr)

        package_check = self._run(["-s", serial, "shell", "pm", "path", package_name])
        package_path = package_check.stdout.strip()
        if package_check.returncode != 0 or not package_path.startswith("package:"):
            raise RuntimeError("Package verification failed after install:\n" + package_check.stdout + package_check.stderr)

        component = f"{package_name}/{package_name}{activity}"
        launch = self._run(["-s", serial, "shell", "am", "start", "-W", "-n", component])
        launch_text = (launch.stdout + "\n" + launch.stderr).strip()
        if launch.returncode != 0 or "Error" in launch_text:
            raise RuntimeError("App launch verification failed:\n" + launch_text)

        return DeviceTestReport(
            passed=True,
            serial=serial,
            package_name=package_name,
            artifact=str(apk.resolve()),
            package_path=package_path,
            launch_output=launch_text,
            timestamp=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
