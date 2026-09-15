<div align="center">

# Ghost APK Builder

### Native Kotlin → Android APK / AAB builder for Windows

**Android API 36 • AGP 9.4 • Managed Build Engine • Polish/English UI • Standalone EXE • Portable Runtime**

</div>

## Current status

**v17.0.0-dev.2 — managed-toolchain beta foundation**

Ghost v17 is a ground-up replacement for the legacy v16.4 architecture. It generates a clean Android project from scratch and manages the build toolchain itself.

The end-user target is simple: **download Ghost, open it, build Android apps — without manually installing Python, Android Studio, JDK, Gradle, Node.js or Cordova.**

## Language policy

GitHub documentation is maintained in **English**. The desktop app is bilingual: Polish system locale (`pl*`) starts in Polish; every other locale starts in English. A visible **PL / EN** switch changes the language at any time and the manual choice persists.

## Easy first-run workflow

Ghost opens on a **Quick Start** dashboard instead of dropping a new user into advanced settings. A bilingual first-run wizard explains three steps: configure the project, prepare the private Build Engine, and build APK/AAB. Live Project and Build Engine readiness badges show what still needs attention.

## Architecture

`ghost_builder/core.py` manages the toolchain, `model.py` validates settings, `generator.py` creates Android projects, `builder.py` builds/validates artifacts, `i18n.py` handles PL/EN, and the desktop UI is split into `ui.py`, `ui_layout.py`, `ui_actions.py` and `ui_theme.py`.

## Zero-manual-install Windows model

The final release provides a standalone EXE plus a Portable ZIP. Python and GUI dependencies are embedded in the EXE; the Portable package also carries JDK 21, Gradle 9.6 and bundletool 1.18.3. Android SDK is provisioned automatically by Ghost after explicit SDK license acceptance rather than redistributed inside the archive.

## Safety

Ghost v17 does not globally terminate Java, modify unrelated development tools or persist signing passwords. Signing secrets exist only for the current session and are passed to Gradle through process environment variables.

## Development plan

See [`ROADMAP.md`](ROADMAP.md). Stable v17.0.0 remains blocked until Windows EXE, Portable, managed-engine, real API 36 APK and signed Release APK/AAB gates are all green.

## Author

Developed by **Swir**.
