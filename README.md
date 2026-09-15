<div align="center">

# Ghost APK Builder

### Native Kotlin → Android APK / AAB builder for Windows

**Android API 36 • AGP 9.4 • Managed Build Engine • Polish/English UI • Standalone EXE • Portable Runtime**

[![Ghost v17 CI](https://github.com/Swir/Ghost-APK-Builder/actions/workflows/ci.yml/badge.svg)](https://github.com/Swir/Ghost-APK-Builder/actions/workflows/ci.yml)
[![Ghost v17 Release](https://github.com/Swir/Ghost-APK-Builder/actions/workflows/release.yml/badge.svg)](https://github.com/Swir/Ghost-APK-Builder/actions/workflows/release.yml)

</div>

## Current status

**v17.0.0-dev.2 — GitHub foundation / managed-toolchain beta line**

Ghost v17 is a ground-up replacement for the legacy v16.4 architecture. The old application cloned an existing Android Studio project and patched it in place. v17 generates a deterministic Android project from scratch and manages the build toolchain itself.

The end-user target is simple: **download Ghost, open it, build Android apps — without manually installing Python, Android Studio, JDK, Gradle, Node.js or Cordova.**

## Language policy

The GitHub repository is maintained in **English**: README, ROADMAP, CHANGELOG, CI messages and technical documentation.

The desktop application is bilingual:

- **Polish system locale (`pl*`) → Polish UI on first launch.**
- **Any other system locale → English UI.**
- A visible **PL / EN switch** can change the language at any time.
- The manual choice is saved in Ghost configuration and overrides automatic detection on later launches.
- Unsupported languages always fall back to English.

See [`docs/LOCALIZATION.md`](docs/LOCALIZATION.md).

## Why v17 exists

The v16.4 audit found several architectural and security problems that made the old approach unsuitable for a reliable zero-install product:

- required a pre-existing Android Studio project;
- could terminate every `java.exe` process on Windows;
- persisted signing passwords in plain JSON and generated Gradle configuration;
- targeted an obsolete Google Play API level;
- relied on retired Windows Subsystem for Android workflows;
- modified arbitrary existing project structures using regular-expression patching;
- mixed UI, build logic, project mutation and process management in one large file.

The preserved source and detailed audit are available in [`legacy/`](legacy/) and [`AUDIT_V16_4.md`](AUDIT_V16_4.md).

## v17 architecture

Ghost v17 is split into focused modules:

```text
app.py                     Desktop entry point
ghost_builder/__init__.py  Version/toolchain profile
ghost_builder/i18n.py      PL/EN localization and system-language detection
ghost_builder/core.py      Managed/portable JDK, Gradle, Android SDK and bundletool
ghost_builder/model.py     Project model and validation
ghost_builder/generator.py Deterministic Android project and resource generator
ghost_builder/builder.py   Gradle build, validation, signing and ADB deployment
ghost_builder/ui.py        Modern CustomTkinter desktop UI
legacy/                    Preserved v16.4 source
tests/                     Security, localization and generator tests
docs/                      Architecture, localization and portable packaging notes
```

## Core features already implemented

### Native Android generation

- clean Gradle/Android project generated from scratch;
- Android 16 / API 36 target profile;
- Android Gradle Plugin **9.4.0**;
- Gradle **9.6.0**;
- Build Tools **36.0.0**;
- built-in Kotlin support from AGP 9;
- APK and AAB output;
- Debug and Release variants;
- configurable minSdk;
- package/version validation;
- splash screen generation;
- adaptive launcher icon generation from a selected image or Ghost's built-in fallback icon;
- optional assets import;
- orientation, fullscreen, hardware acceleration, cleartext and backup controls;
- Internet, Camera, Location and Microphone permissions;
- automatic runtime permission helper injection for dangerous permissions.

### Managed Build Engine

Ghost searches in this order:

1. runtime embedded in the Portable package;
2. Ghost-managed private runtime in `%LOCALAPPDATA%\GhostAPKBuilder`;
3. compatible system tools (unless strict managed mode is enabled).

The Build Engine can prepare and repair:

- Eclipse Temurin JDK 21 (`java`, `keytool`, `jarsigner`);
- Gradle 9.6.0;
- Android command-line tools;
- Android API 36 platform;
- Android Build Tools 36.0.0 (`aapt2`, `apksigner`);
- Android Platform Tools (`adb`);
- Google bundletool 1.18.3.

Managed downloads use official checksums where available. Incomplete Ghost-managed components can be repaired without touching unrelated system installations.

### Signing and artifact validation

- JKS creation through managed `keytool`;
- session-only signing passwords;
- passwords are stripped from current and legacy config keys;
- signing secrets are passed to Gradle only through process environment variables;
- APK ZIP integrity checks;
- signed APK validation through `apksigner`;
- AAB structural validation through bundletool;
- signed AAB validation through `jarsigner`;
- optional ADB install/launch after APK build.

## Zero-manual-install Windows model

The release pipeline is designed around two downloads:

### Standalone EXE

`Ghost-APK-Builder-<version>-Windows-x64.exe`

Python, CustomTkinter and Pillow are bundled into the executable by PyInstaller. The user does not install Python or Python packages.

### Portable ZIP

`Ghost-APK-Builder-<version>-Portable-Windows-x64.zip`

The Portable archive contains:

- Ghost standalone EXE;
- Eclipse Temurin JDK 21;
- Gradle 9.6.0;
- Google bundletool 1.18.3;
- bundletool license;
- runtime manifest;
- README / ROADMAP / CHANGELOG / SECURITY / notices.

**Android SDK components are intentionally not redistributed inside the GitHub ZIP.** Their license requires explicit acceptance. Ghost handles the complete SDK setup itself after the user accepts the Android SDK terms — there is still no Android Studio or manual SDK installation step.

See [`docs/PORTABLE.md`](docs/PORTABLE.md).

## Build Engine safety rules

Ghost v17 must never:

- run global `taskkill java.exe` operations;
- delete system JDK/Gradle/Android SDK installations;
- persist signing passwords;
- require administrator rights for normal use;
- silently accept the Android SDK license;
- modify unrelated Android Studio projects.

CI contains tests enforcing these rules and a strict managed-toolchain mode (`GHOST_FORCE_MANAGED_TOOLCHAIN=1`) for clean-machine integration tests.

## Running from source (developers only)

End users should use release artifacts. Contributors can run source builds with:

```powershell
py -m pip install -r requirements.txt
py app.py
```

Build a local EXE:

```powershell
./build_windows.ps1
```

## Automated quality gates

GitHub Actions covers:

- Python compilation and unit/security/localization tests;
- Windows standalone EXE build;
- Windows EXE smoke launch;
- real Android API 36 debug APK generation;
- isolated managed Build Engine provisioning and repair;
- exact Portable package assembly;
- JDK / Gradle / bundletool execution checks;
- SHA-256 checksum generation for release assets.

## Security

Read [`SECURITY.md`](SECURITY.md) before using development builds for production signing. Report security-sensitive problems privately rather than publishing secrets or keystore material in an issue.

## Development plan

The full plan lives in [`ROADMAP.md`](ROADMAP.md). The immediate objective is a tested public v17 beta with a zero-manual-install Windows package, followed by stable `v17.0.0` only after every release gate is green.

## Author

Developed by **Swir**.
