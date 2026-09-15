from __future__ import annotations

import os
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Callable

from .certificates import parse_keytool_fingerprints
from .core import ToolchainManager
from .generator import AndroidProjectGenerator
from .model import ProjectConfig

Emit = Callable[[str, str], None]


class GhostBuilder:
    def __init__(self, toolchain: ToolchainManager, emit: Emit | None = None):
        self.toolchain = toolchain
        self.emit = emit or (lambda _level, _message: None)
        self.generator = AndroidProjectGenerator()

    def build(self, cfg: ProjectConfig, store_password: str = "", key_password: str = "") -> Path:
        errors = cfg.validate()
        if errors:
            raise ValueError("\n".join(errors))
        if not self.toolchain.ready():
            raise RuntimeError("Build Engine is not ready. Run Prepare Build Engine first.")

        workspace = self.toolchain.p.workspace / "current"
        self.emit("info", "Generating a clean Android project")
        self.generator.generate(workspace, cfg)
        gradle = self.toolchain.gradle_exe()
        if not gradle:
            raise RuntimeError("Gradle is unavailable")

        task = ("assemble" if cfg.export_format == "APK" else "bundle") + cfg.build_mode
        env = self.toolchain.env()
        if cfg.signing_enabled:
            if not store_password or not key_password:
                raise ValueError("Signing passwords are required for this build but are never saved to disk.")
            env.update(
                GHOST_STORE_FILE=str(Path(cfg.keystore_path).resolve()),
                GHOST_STORE_PASSWORD=store_password,
                GHOST_KEY_ALIAS=cfg.key_alias,
                GHOST_KEY_PASSWORD=key_password,
            )
        self.emit("info", f"Running Gradle task {task}")
        process = subprocess.Popen(
            [str(gradle), "--no-daemon", "--stacktrace", task],
            cwd=workspace,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
        )
        assert process.stdout is not None
        tail: list[str] = []
        for line in process.stdout:
            text = line.rstrip()
            tail.append(text)
            if len(tail) > 120:
                tail.pop(0)
            self.emit("detail", text)
        code = process.wait()
        if code != 0:
            raise RuntimeError("Gradle build failed.\n" + "\n".join(tail[-35:]))

        artifact = self._find_artifact(workspace, cfg)
        out = Path(cfg.output_dir or (Path.home() / "Desktop"))
        out.mkdir(parents=True, exist_ok=True)
        safe_name = "".join(ch if ch.isalnum() or ch in "-_" else "_" for ch in cfg.app_name).strip("_") or "GhostApp"
        suffix = cfg.export_format.lower()
        dest = out / f"{safe_name}-{cfg.build_mode.lower()}-v{cfg.version_name}.{suffix}"
        shutil.copy2(artifact, dest)
        self.validate_artifact(dest, cfg)
        self.emit("success", f"Build complete: {dest}")

        if cfg.deploy_adb and cfg.export_format == "APK":
            self.deploy_to_connected_device(dest, cfg.package_name, ".SplashActivity" if cfg.use_splash else ".MainActivity")
        return dest

    @staticmethod
    def _find_artifact(workspace: Path, cfg: ProjectConfig) -> Path:
        mode = cfg.build_mode.lower()
        if cfg.export_format == "AAB":
            expected = workspace / "app" / "build" / "outputs" / "bundle" / mode / f"app-{mode}.aab"
            if expected.exists():
                return expected
        else:
            folder = workspace / "app" / "build" / "outputs" / "apk" / mode
            preferred = folder / f"app-{mode}.apk"
            if preferred.exists():
                return preferred
            candidates = sorted(folder.glob("*.apk")) if folder.exists() else []
            if candidates:
                return candidates[0]
        raise FileNotFoundError(f"Gradle succeeded but no {cfg.export_format} artifact was found")

    def validate_artifact(self, path: Path, cfg: ProjectConfig) -> None:
        try:
            with zipfile.ZipFile(path) as z:
                bad = z.testzip()
                if bad:
                    raise RuntimeError(f"Corrupt archive entry: {bad}")
        except zipfile.BadZipFile as exc:
            raise RuntimeError(f"Invalid {cfg.export_format} archive") from exc

        if cfg.export_format == "APK" and cfg.signing_enabled:
            signer = self.toolchain.apksigner_exe()
            if not signer:
                raise RuntimeError("apksigner is missing")
            result = subprocess.run([str(signer), "verify", "--verbose", str(path)], env=self.toolchain.env(), capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("APK signature validation failed:\n" + result.stdout + result.stderr)
        elif cfg.export_format == "AAB":
            java, bundletool = self.toolchain.java_exe(), self.toolchain.bundletool_jar()
            if not java or not bundletool:
                raise RuntimeError("Java/bundletool is missing")
            result = subprocess.run([str(java), "-jar", str(bundletool), "validate", f"--bundle={path}"], env=self.toolchain.env(), capture_output=True, text=True)
            if result.returncode != 0:
                raise RuntimeError("AAB bundletool validation failed:\n" + result.stdout + result.stderr)
            if cfg.signing_enabled:
                jarsigner = self.toolchain.jarsigner_exe()
                if not jarsigner:
                    raise RuntimeError("jarsigner is missing")
                result = subprocess.run([str(jarsigner), "-verify", str(path)], env=self.toolchain.env(), capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError("AAB signature validation failed:\n" + result.stdout + result.stderr)

    def generate_keystore(self, path: Path, password: str, alias: str) -> None:
        keytool = self.toolchain.keytool_exe()
        if not keytool:
            raise RuntimeError("keytool is not available. Prepare Build Engine first.")
        path.parent.mkdir(parents=True, exist_ok=True)
        env = self.toolchain.env()
        env["GHOST_KEYTOOL_STOREPASS"] = password
        env["GHOST_KEYTOOL_KEYPASS"] = password
        result = subprocess.run(
            [
                str(keytool), "-genkeypair", "-v", "-keystore", str(path), "-alias", alias,
                "-keyalg", "RSA", "-keysize", "3072", "-validity", "10000",
                "-storepass:env", "GHOST_KEYTOOL_STOREPASS", "-keypass:env", "GHOST_KEYTOOL_KEYPASS",
                "-dname", "CN=Ghost App, OU=Ghost Builder, O=Swir, L=Local, ST=Local, C=NO",
            ],
            env=env,
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            raise RuntimeError(result.stdout + result.stderr)

    def certificate_fingerprints(self, path: Path, password: str, alias: str) -> dict[str, str]:
        keytool = self.toolchain.keytool_exe()
        if not keytool:
            raise RuntimeError("keytool is not available. Prepare Build Engine first.")
        if not Path(path).is_file():
            raise FileNotFoundError(f"Keystore not found: {path}")
        if not alias.strip():
            raise ValueError("Key alias is required.")
        if not password:
            raise ValueError("Keystore password is required for this session.")
        env = self.toolchain.env()
        env["GHOST_KEYTOOL_STOREPASS"] = password
        result = subprocess.run(
            [str(keytool), "-list", "-v", "-keystore", str(path), "-alias", alias.strip(), "-storepass:env", "GHOST_KEYTOOL_STOREPASS"],
            env=env,
            capture_output=True,
            text=True,
            shell=False,
        )
        if result.returncode != 0:
            raise RuntimeError((result.stdout + "\n" + result.stderr).strip())
        fingerprints = parse_keytool_fingerprints(result.stdout + "\n" + result.stderr)
        if "SHA1" not in fingerprints or "SHA256" not in fingerprints:
            raise RuntimeError("Could not read SHA-1/SHA-256 certificate fingerprints.")
        return fingerprints

    def deploy_to_connected_device(self, apk: Path, package_name: str, activity: str) -> None:
        adb = self.toolchain.adb_exe()
        if not adb:
            raise RuntimeError("ADB is unavailable")
        env = self.toolchain.env()
        install = subprocess.run([str(adb), "install", "-r", str(apk)], env=env, capture_output=True, text=True)
        if install.returncode != 0:
            raise RuntimeError("ADB install failed:\n" + install.stdout + install.stderr)
        launch = subprocess.run([str(adb), "shell", "am", "start", "-n", f"{package_name}/{package_name}{activity}"], env=env, capture_output=True, text=True)
        if launch.returncode != 0:
            raise RuntimeError("ADB launch failed:\n" + launch.stdout + launch.stderr)