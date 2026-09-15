<div align="center">

# Ghost APK Builder

### Native Kotlin → Android APK / AAB builder for Windows

**Android API 36 • AGP 9.4 • Managed Build Engine • Polish/English UI • Standalone EXE • Portable Runtime**

### Project progress

`███████████████████░ 94%`

</div>

## Current status

**v17.0.0-beta.2 — public beta**

Ghost v17 is a ground-up replacement for the legacy v16.4 architecture. It generates a clean Android project from scratch, manages the build toolchain itself, and has passed the core beta release gates.

Verified beta gates include:
- Windows standalone EXE build and smoke launch without a system Python runtime.
- Official branded Ghost icon embedded in the Windows executable.
- Real Android API 36 Debug APK compilation.
- Isolated managed Build Engine Prepare/Repair validation.
- Signed Release APK and AAB builds with signature validation.
- Verified Portable Windows package with JDK 21, Gradle 9.6 and bundletool 1.18.3.
- Python 3.11 / 3.12 / 3.13 quality matrix.

Stable v17.0.0 is **not** declared yet. The remaining release gate is a successful physical-device verification on real user hardware.

## Language policy

GitHub documentation is maintained in **English**. The desktop app is bilingual:
- Polish system locale (`pl*`) starts in Polish.
- Every other locale starts in English.
- A visible **PL / EN** switch changes the language at any time.
- The manual language choice is persisted.

## Simple / Advanced mode

Ghost starts in **Simple** mode for a cleaner beginner workflow. Home and Project stay visible while technical Android, Kotlin, signing, Build Engine and diagnostic tabs are hidden.

Switch to **Advanced** at any time to expose the full toolset. Ghost also opens Advanced mode automatically when a workflow requires an advanced screen. The preference is persisted.

## Project profiles and Recent Projects

Ghost supports `.ghostproject` files. A project profile keeps application settings and Kotlin source together so work can be reopened later without rebuilding the setup by hand.

Signing passwords are deliberately excluded from project profiles. Recent Projects keeps a small deduplicated list of valid `.ghostproject` files and exposes quick reopen actions from Home.

## Google Play readiness

A dedicated readiness check evaluates the current project before Play submission. It checks the Android API profile, package/version data, Release mode, signing configuration, keystore/alias, output format, icon state and security-related warnings such as cleartext HTTP.

The result is presented directly in Polish or English as **READY FOR GOOGLE PLAY / GOTOWE DLA GOOGLE PLAY** or as a concrete issue list to fix.

## Build History

Successful builds are recorded locally with artifact path, application/version data, APK/AAB type, Debug/Release mode, signing state, file size, build duration and SHA-256 digest. The History window provides quick access to recent artifacts and their containing folders.

No signing password is stored in Build History.

## Rich post-build result

After a successful build, Ghost opens a dedicated bilingual result panel instead of a basic message box. It shows the artifact name, size, build duration, signing state and SHA-256 checksum.

From the same panel users can:
- open the generated APK/AAB,
- open its folder,
- copy the full artifact path,
- copy the SHA-256 checksum,
- start the physical Android-device verification for APK artifacts,
- jump back to Build History for AAB workflows.

The result panel includes keyboard focus and Escape-to-close behavior for a cleaner keyboard workflow.

## Physical Android-device verification

Ghost includes a one-click device gate for generated APK files. It uses the managed ADB toolchain and performs the complete verification flow:
1. start/check the ADB server,
2. require exactly one authorized Android device,
3. install the APK with `adb install -r`,
4. verify the installed package with `pm path`,
5. launch the generated activity with `am start -W`,
6. save a local `device_test_last.json` PASS report.

Unauthorized/offline devices produce an actionable error instead of a false success. The roadmap does **not** mark the physical-device gate complete until this flow is actually run successfully on real hardware.

## Certificate fingerprints

Ghost can read SHA-1 and SHA-256 fingerprints from the selected signing certificate directly from the UI. SHA-256 is copied to the clipboard for easy Firebase / API configuration workflows.

`keytool` passwords are no longer passed as plain process arguments; they are supplied through the child-process environment for the current session only.

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
- `ghost_builder/project_store.py` — `.ghostproject` persistence and Recent Projects.
- `ghost_builder/readiness.py` — Google Play readiness report.
- `ghost_builder/build_history.py` — local artifact history and SHA-256 metadata.
- `ghost_builder/certificates.py` — certificate fingerprint parsing.
- `ghost_builder/device_test.py` — physical Android-device verification and PASS report.
- `ghost_builder/ui_result.py` — rich post-build result workflow.
- `ghost_builder/i18n.py` — Polish/English localization.
- `ghost_builder/ui.py`, `ui_layout.py`, `ui_actions.py`, `ui_theme.py` — modular desktop UI.

## Safety

Ghost v17 does not globally terminate Java, modify unrelated development tools or persist signing passwords. Signing secrets exist only for the current session and are passed through child-process environment variables when required.

## Development plan

See [`ROADMAP.md`](ROADMAP.md) for the real milestone state. The progress percentage is based on completed product/release gates, not inflated by CI volume alone.

## Author

Developed by **Swir**.
