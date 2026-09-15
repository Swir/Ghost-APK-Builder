from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

from . import ANDROID_API, APP_NAME, BUILD_TOOLS, BUNDLETOOL_VERSION, GRADLE_VERSION, VERSION

JDK_META_URL = "https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jdk&os=windows&vendor=eclipse&heap_size=normal"
ANDROID_TOOLS_URL = "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip"
ANDROID_TOOLS_SHA256 = "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a"
GRADLE_URL = f"https://services.gradle.org/distributions/gradle-{GRADLE_VERSION}-bin.zip"
ANDROID_LICENSE_URL = "https://developer.android.com/studio/terms"
BUNDLETOOL_URL = f"https://github.com/google/bundletool/releases/download/{BUNDLETOOL_VERSION}/bundletool-all-{BUNDLETOOL_VERSION}.jar"
BUNDLETOOL_SHA256 = "a099cfa1543f55593bc2ed16a70a7c67fe54b1747bb7301f37fdfd6d91028e29"

Emit = Callable[[str, str], None]


class Paths:
    def __init__(self, root_override: str | Path | None = None):
        if root_override is not None:
            base = Path(root_override)
        else:
            local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA") or str(Path.home())
            base = Path(local) / "GhostAPKBuilder"
        self.root = base
        self.app_dir = Path(sys.executable).resolve().parent if getattr(sys, "frozen", False) else Path(__file__).resolve().parent.parent
        self.portable = self.app_dir / "runtime"
        self.portable_jdk = self.portable / "jdk"
        self.portable_gradle = self.portable / "gradle"
        self.portable_sdk = self.portable / "android-sdk"
        self.portable_bundletool = self.portable / "bundletool" / f"bundletool-all-{BUNDLETOOL_VERSION}.jar"
        self.toolchain = self.root / "toolchain"
        self.jdk = self.toolchain / "jdk"
        self.sdk = self.toolchain / "android-sdk"
        self.gradle = self.toolchain / "gradle"
        self.bundletool = self.toolchain / "bundletool" / f"bundletool-all-{BUNDLETOOL_VERSION}.jar"
        self.workspace = self.root / "workspace"
        self.downloads = self.root / "downloads"
        self.config = self.root / "config.json"
        for p in (self.root, self.toolchain, self.workspace, self.downloads):
            p.mkdir(parents=True, exist_ok=True)


class ConfigStore:
    SECRET_KEYS = {"store_password", "key_password", "keystore_pass", "key_pass"}

    def __init__(self, path: Path):
        self.path = path

    def load(self) -> dict:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return {}
            for key in self.SECRET_KEYS:
                data.pop(key, None)
            return data
        except Exception:
            return {}

    def save(self, data: dict) -> None:
        safe = {k: v for k, v in data.items() if k not in self.SECRET_KEYS}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        tmp.write_text(json.dumps(safe, indent=2, ensure_ascii=False), encoding="utf-8")
        tmp.replace(self.path)


class ToolchainManager:
    def __init__(self, paths: Paths, emit: Emit | None = None):
        self.p = paths
        self.emit = emit or (lambda _level, _message: None)

    @staticmethod
    def _force_managed() -> bool:
        return os.environ.get("GHOST_FORCE_MANAGED_TOOLCHAIN", "").strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def _find(root: Path, name: str) -> Path | None:
        if root.exists():
            for item in root.rglob(name):
                if item.is_file():
                    return item
        return None

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest().lower()

    @staticmethod
    def _json(url: str):
        req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.load(r)

    @staticmethod
    def _text(url: str) -> str:
        req = urllib.request.Request(url, headers={"User-Agent": f"{APP_NAME}/{VERSION}"})
        with urllib.request.urlopen(req, timeout=60) as r:
            return r.read().decode("utf-8").strip()

    @staticmethod
    def _is_full_jdk(home: Path) -> bool:
        return all((home / "bin" / name).exists() for name in ("java.exe", "keytool.exe", "jarsigner.exe"))

    def java_home(self) -> Path | None:
        for root in (self.p.portable_jdk, self.p.jdk):
            exe = self._find(root, "java.exe")
            if exe:
                home = exe.parent.parent
                if self._is_full_jdk(home):
                    return home
        if not self._force_managed():
            env = os.environ.get("JAVA_HOME")
            if env:
                home = Path(env)
                if self._is_full_jdk(home):
                    return home
            found = shutil.which("java")
            if found:
                home = Path(found).resolve().parent.parent
                if self._is_full_jdk(home):
                    return home
        return None

    def java_exe(self) -> Path | None:
        home = self.java_home()
        candidate = home / "bin" / "java.exe" if home else None
        return candidate if candidate and candidate.exists() else None

    def keytool_exe(self) -> Path | None:
        home = self.java_home()
        candidate = home / "bin" / "keytool.exe" if home else None
        if candidate and candidate.exists():
            return candidate
        if not self._force_managed():
            found = shutil.which("keytool")
            return Path(found) if found else None
        return None

    def jarsigner_exe(self) -> Path | None:
        home = self.java_home()
        candidate = home / "bin" / "jarsigner.exe" if home else None
        if candidate and candidate.exists():
            return candidate
        if not self._force_managed():
            found = shutil.which("jarsigner")
            return Path(found) if found else None
        return None

    def sdk_root(self) -> Path | None:
        for root in (self.p.portable_sdk, self.p.sdk):
            if (root / "cmdline-tools" / "latest" / "bin" / "sdkmanager.bat").exists():
                return root
        if not self._force_managed():
            for key in ("ANDROID_SDK_ROOT", "ANDROID_HOME"):
                value = os.environ.get(key)
                if value and Path(value).exists():
                    return Path(value)
            local = Path(os.environ.get("LOCALAPPDATA", "")) / "Android" / "Sdk"
            return local if local.exists() else None
        return None

    def gradle_exe(self) -> Path | None:
        for root in (self.p.portable_gradle, self.p.gradle):
            exe = self._find(root, "gradle.bat")
            if exe:
                return exe
        if not self._force_managed():
            found = shutil.which("gradle")
            return Path(found) if found else None
        return None

    def bundletool_jar(self) -> Path | None:
        for candidate in (self.p.portable_bundletool, self.p.bundletool):
            if candidate.exists():
                return candidate
        return None

    def adb_exe(self) -> Path | None:
        sdk = self.sdk_root()
        candidate = sdk / "platform-tools" / "adb.exe" if sdk else None
        return candidate if candidate and candidate.exists() else None

    def apksigner_exe(self) -> Path | None:
        sdk = self.sdk_root()
        candidate = sdk / "build-tools" / BUILD_TOOLS / "apksigner.bat" if sdk else None
        return candidate if candidate and candidate.exists() else None

    def status(self) -> dict[str, str]:
        sdk = self.sdk_root()
        return {
            "JDK 21": str(self.java_home() or "missing"),
            "keytool": "ready" if self.keytool_exe() else "missing",
            "jarsigner": "ready" if self.jarsigner_exe() else "missing",
            "Gradle": str(self.gradle_exe() or "missing"),
            "Android SDK": str(sdk or "missing"),
            f"Android API {ANDROID_API}": "ready" if sdk and (sdk / f"platforms/android-{ANDROID_API}" / "android.jar").exists() else "missing",
            f"Build Tools {BUILD_TOOLS}": "ready" if sdk and (sdk / "build-tools" / BUILD_TOOLS / "aapt2.exe").exists() else "missing",
            "APK Signer": "ready" if self.apksigner_exe() else "missing",
            "Platform Tools": "ready" if self.adb_exe() else "missing",
            f"bundletool {BUNDLETOOL_VERSION}": str(self.bundletool_jar() or "missing"),
        }

    def ready(self) -> bool:
        return all(value != "missing" for value in self.status().values())

    def env(self) -> dict[str, str]:
        env = os.environ.copy()
        java, sdk = self.java_home(), self.sdk_root()
        if java:
            env["JAVA_HOME"] = str(java)
            env["PATH"] = str(java / "bin") + os.pathsep + env.get("PATH", "")
        if sdk:
            env["ANDROID_SDK_ROOT"] = env["ANDROID_HOME"] = str(sdk)
        return env

    def _download(self, url: str, dest: Path, label: str, expected_sha256: str | None = None, retries: int = 3) -> None:
        dest.parent.mkdir(parents=True, exist_ok=True)
        part = dest.with_suffix(dest.suffix + ".part")
        last_error: Exception | None = None
        for attempt in range(1, retries + 1):
            try:
                start = part.stat().st_size if part.exists() else 0
                headers = {"User-Agent": f"{APP_NAME}/{VERSION}"}
                if start:
                    headers["Range"] = f"bytes={start}-"
                    self.emit("info", f"Resuming {label} from {start / 1024 / 1024:.1f} MB")
                else:
                    self.emit("info", f"Downloading {label}")
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=90) as r:
                    status = getattr(r, "status", None) or r.getcode()
                    resumed = start > 0 and status == 206
                    mode = "ab" if resumed else "wb"
                    if start and not resumed:
                        start = 0
                    remaining = int(r.headers.get("Content-Length") or 0)
                    total = start + remaining if remaining else 0
                    got = start
                    with part.open(mode) as f:
                        while True:
                            chunk = r.read(1024 * 1024)
                            if not chunk:
                                break
                            f.write(chunk)
                            got += len(chunk)
                            if total:
                                self.emit("progress", f"{label}:{min(100, got * 100 // total)}")
                part.replace(dest)
                if expected_sha256:
                    actual = self._sha256(dest)
                    if actual != expected_sha256.lower():
                        dest.unlink(missing_ok=True)
                        part.unlink(missing_ok=True)
                        raise RuntimeError(f"SHA-256 verification failed for {label}")
                    self.emit("success", f"Verified {label}")
                return
            except (OSError, urllib.error.URLError, urllib.error.HTTPError, RuntimeError) as exc:
                last_error = exc
                if attempt < retries:
                    self.emit("warning", f"{label} download failed ({attempt}/{retries}): {exc}")
                    time.sleep(2 ** (attempt - 1))
        raise RuntimeError(f"Unable to download {label}: {last_error}")

    def _extract_by_marker(self, archive: Path, target: Path, marker: str) -> None:
        temp = Path(tempfile.mkdtemp(prefix="ghost-", dir=self.p.root))
        try:
            with zipfile.ZipFile(archive) as z:
                z.extractall(temp)
            marker_path = self._find(temp, marker)
            if not marker_path:
                raise RuntimeError(f"Invalid archive: {marker} missing")
            root = marker_path.parent.parent
            shutil.rmtree(target, ignore_errors=True)
            shutil.copytree(root, target)
        finally:
            shutil.rmtree(temp, ignore_errors=True)

    def _jdk_package(self) -> tuple[str, str]:
        data = self._json(JDK_META_URL)
        if not data:
            raise RuntimeError("No Temurin JDK package metadata returned")
        pkg = data[0]["binary"]["package"]
        return pkg["link"], pkg["checksum"]

    def provision(self, accept_android_sdk_license: bool = False) -> None:
        if not self.java_home():
            url, checksum = self._jdk_package()
            archive = self.p.downloads / "jdk.zip"
            self._download(url, archive, "Temurin JDK 21", checksum)
            self._extract_by_marker(archive, self.p.jdk, "java.exe")
            archive.unlink(missing_ok=True)

        if not self.gradle_exe():
            checksum = self._text(GRADLE_URL + ".sha256").split()[0]
            archive = self.p.downloads / "gradle.zip"
            self._download(GRADLE_URL, archive, f"Gradle {GRADLE_VERSION}", checksum)
            temp = Path(tempfile.mkdtemp(prefix="ghost-gradle-", dir=self.p.root))
            try:
                with zipfile.ZipFile(archive) as z:
                    z.extractall(temp)
                root = next(x for x in temp.iterdir() if x.is_dir() and x.name.startswith("gradle-"))
                shutil.rmtree(self.p.gradle, ignore_errors=True)
                shutil.copytree(root, self.p.gradle)
            finally:
                shutil.rmtree(temp, ignore_errors=True)
                archive.unlink(missing_ok=True)

        sdk = self.sdk_root()
        if not sdk or not (sdk / "cmdline-tools" / "latest" / "bin" / "sdkmanager.bat").exists():
            archive = self.p.downloads / "android-tools.zip"
            self._download(ANDROID_TOOLS_URL, archive, "Android command-line tools", ANDROID_TOOLS_SHA256)
            temp = Path(tempfile.mkdtemp(prefix="ghost-sdk-", dir=self.p.root))
            try:
                with zipfile.ZipFile(archive) as z:
                    z.extractall(temp)
                src = temp / "cmdline-tools"
                if not (src / "bin" / "sdkmanager.bat").exists():
                    raise RuntimeError("Invalid Android command-line tools archive")
                target = self.p.sdk / "cmdline-tools" / "latest"
                shutil.rmtree(target, ignore_errors=True)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copytree(src, target)
            finally:
                shutil.rmtree(temp, ignore_errors=True)
                archive.unlink(missing_ok=True)
            sdk = self.p.sdk

        if not self.bundletool_jar():
            self._download(BUNDLETOOL_URL, self.p.bundletool, f"bundletool {BUNDLETOOL_VERSION}", BUNDLETOOL_SHA256)

        sdk = self.sdk_root() or self.p.sdk
        if not accept_android_sdk_license:
            raise PermissionError("Android SDK license acceptance is required before provisioning SDK packages")
        sdkmanager = sdk / "cmdline-tools" / "latest" / "bin" / "sdkmanager.bat"
        env = self.env()
        env["ANDROID_SDK_ROOT"] = env["ANDROID_HOME"] = str(sdk)
        command = [
            str(sdkmanager),
            f"--sdk_root={sdk}",
            "platform-tools",
            f"platforms;android-{ANDROID_API}",
            f"build-tools;{BUILD_TOOLS}",
        ]
        result = subprocess.run(command, input="y\n" * 50, text=True, capture_output=True, env=env)
        if result.returncode != 0:
            raise RuntimeError((result.stdout + "\n" + result.stderr)[-5000:])
        if not self.ready():
            raise RuntimeError("Build Engine provisioning finished but required components are still missing")
        self.emit("success", "Ghost Build Engine is ready")

    def repair(self, accept_android_sdk_license: bool = False) -> list[str]:
        actions: list[str] = []
        if self.p.jdk.exists():
            java = self._find(self.p.jdk, "java.exe")
            home = java.parent.parent if java else self.p.jdk
            if not java or not self._is_full_jdk(home):
                shutil.rmtree(self.p.jdk, ignore_errors=True)
                actions.append("Removed incomplete managed JDK")
        if self.p.gradle.exists() and not self._find(self.p.gradle, "gradle.bat"):
            shutil.rmtree(self.p.gradle, ignore_errors=True)
            actions.append("Removed incomplete managed Gradle")
        sdk = self.p.sdk
        checks = [
            (sdk / "cmdline-tools", sdk / "cmdline-tools" / "latest" / "bin" / "sdkmanager.bat", "Android command-line tools"),
            (sdk / f"platforms/android-{ANDROID_API}", sdk / f"platforms/android-{ANDROID_API}" / "android.jar", f"Android API {ANDROID_API}"),
            (sdk / f"build-tools/{BUILD_TOOLS}", sdk / f"build-tools/{BUILD_TOOLS}" / "aapt2.exe", f"Build Tools {BUILD_TOOLS}"),
            (sdk / "platform-tools", sdk / "platform-tools" / "adb.exe", "Platform Tools"),
        ]
        for folder, marker, label in checks:
            if folder.exists() and not marker.exists():
                shutil.rmtree(folder, ignore_errors=True)
                actions.append(f"Removed incomplete {label}")
        build_tools = sdk / f"build-tools/{BUILD_TOOLS}"
        if build_tools.exists() and not (build_tools / "apksigner.bat").exists():
            shutil.rmtree(build_tools, ignore_errors=True)
            actions.append(f"Removed Build Tools {BUILD_TOOLS} without apksigner")
        if self.p.bundletool.exists() and self._sha256(self.p.bundletool) != BUNDLETOOL_SHA256:
            self.p.bundletool.unlink(missing_ok=True)
            actions.append("Removed invalid managed bundletool")
        for action in actions:
            self.emit("warning", action)
        self.provision(accept_android_sdk_license=accept_android_sdk_license)
        return actions
