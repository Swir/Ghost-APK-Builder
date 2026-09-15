<div align="center">

# Ghost APK Builder

### Native Kotlin → Android APK / AAB builder for Windows

**Android API 36 • AGP 9.4 • Managed Build Engine • Polish/English UI • Standalone EXE • Portable Runtime**

### Project progress

`███████████████░░░░░ 75%`

</div>

## Current status

**v17.0.0-beta.1 — public beta candidate**

Ghost v17 is a ground-up replacement for the legacy v16.4 architecture. It generates a clean Android project from scratch, manages the build toolchain itself, and has now passed the core beta release gates.

Verified beta gates include:
- Windows standalone EXE build and smoke launch without a system Python runtime.
- Official branded Ghost icon embedded in the Windows executable.
- Real Android API 36 Debug APK compilation.
- Isolated managed Build Engine Prepare/Repair validation.
- Signed Release APK and AAB builds with signature validation.
- Verified Portable Windows package with JDK 21, Gradle 9.6 and bundletool 1.18.3.
- Python 3.11 / 3.12 / 3.13 quality matrix.

Stable v17.0.0 is **not** declared yet. It remains blocked on clean Windows 11 user testing and a physical Android-device test.

## Language policy

GitHub documentation is maintained in **English**. The desktop app is bilingual:
- Polish system locale (`pl*`) starts in Polish.
- Every other locale starts in English.
- A visible **PL / EN** switch changes the language at any time.
- The manual language choice is persisted.

## Simple / Advanced mode

Ghost starts in **Simple** mode for a cleaner beginner workflow. Home and Project stay visible while technical Android, Kotlin, signing, Build Engine and diagnostic tabs are hidden.

Switch to **Advanced** at any time to expose the full toolset. Ghost also opens Advanced mode automatically when a workflow requires an advanced screen. The preference is persisted.

## Easy first-run workflow

Ghost opens on a Quick Start dashboard instead of dropping a new user into advanced settings. A bilingual first-run wizard explains three steps: configure the project, prepare the private Build Engine, and build APK/AAB. Live Project and Build Engine readiness badges show what still needs attention.

## Zero-manual-install Windows model

The release provides a standalone EXE plus a Portable ZIP. Python and GUI dependencies are embedded in the EXE. The Portable package also carries JDK 21, Gradle 9.6 and bundletool 1.18.3.

Users do **not** need to manually install Python, Java, Gradle, Android Studio, Node.js or Cordova.

Official Android SDK components are the licensing exception: Ghost provisions the required SDK components itself after explicit Android SDK terms acceptance instead of redistributing them inside the public archive.

## Architecture

- `ghost_builder/core.py` — managed toolchain and private runtime.
- `ghost_builder/model.py` — project validation.
- `ghost_builder/generator.py` — deterministic native Android project generation.
- `ghost_builder/builder.py` — build, signing and artifact validation.
- `ghost_builder/i18n.py` — Polish/English localization.
- `ghost_builder/ui.py`, `ui_layout.py`, `ui_actions.py`, `ui_theme.py` — modular desktop UI.

## Safety

Ghost v17 does not globally terminate Java, modify unrelated development tools or persist signing passwords. Signing secrets exist only for the current session and are passed to Gradle through process environment variables.

## Development plan

See [`ROADMAP.md`](ROADMAP.md) for the real milestone state. The progress percentage is based on completed product/release gates, not inflated by CI volume alone.

## Author

Developed by **Swir**.
