# Ghost APK Builder v17 Roadmap

This roadmap is the source of truth for v17 development.

## Overall progress — 94%

`███████████████████░ 94%`

The percentage reflects real milestone and release-gate completion rather than CI volume alone.

## M0 — Safe architecture ✅
- [x] Remove global Java termination and persisted signing passwords.
- [x] Replace Android Studio base-project dependency with deterministic generation.
- [x] Modular UI/model/generator/builder/toolchain/localization architecture.
- [x] Android API 36 default profile.

## M1 — Managed Build Engine 🚧
- [x] Portable/managed/system JDK, Gradle, SDK and bundletool discovery.
- [x] Full JDK readiness: java, keytool, jarsigner.
- [x] API 36 + Build Tools 36.0.0 + Platform Tools + apksigner.
- [x] SHA-256 verification, retry/resume and safe Repair.
- [x] Explicit Android SDK license consent.
- [x] Isolated Prepare/Repair CI gate green.
- [ ] Offline cache import/export.

## M2 — Native Android generator 🚧
- [x] AGP 9.4 / Gradle 9.6 APK/AAB generation.
- [x] Debug/Release, runtime permissions, icons, splash, assets and safe defaults.
- [ ] Compile-tested v16 templates.
- [ ] Firebase/AdMob/Billing validation.
- [ ] Modern WebView template.

## M3 — Signing and validation 🚧
- [x] Session-only signing secrets and managed keytool.
- [x] APK/AAB validation paths.
- [x] Ephemeral signed Release APK/AAB CI gate.
- [x] Google Play readiness report for package/API/version/signing/icon/output/security checks.
- [x] SHA-1 / SHA-256 certificate fingerprint viewer.
- [x] keytool passwords removed from command-line arguments and passed via process environment.
- [ ] Rich Play readiness export/report file.

## M4 — Desktop UI ✅
- [x] Modern Ghost dark UI and modular UI code.
- [x] Quick Start dashboard with readiness badges.
- [x] First-run bilingual onboarding wizard.
- [x] PL system detection, English fallback and persisted PL/EN switch.
- [x] Thread-safe worker queue and diagnostic logs.
- [x] Simple / Advanced mode with persisted preference.
- [x] `.ghostproject` project profiles with Kotlin source persistence and secret filtering.
- [x] Recent Projects list with quick reopen.
- [x] Persistent Build History with artifact SHA-256, size, duration, mode and signing state.
- [x] Build-history artifact folder shortcut.
- [x] Rich post-build result panel with file/folder/path/SHA-256 actions.
- [x] Basic accessibility polish for the result flow: keyboard focus and Escape-to-close behavior.

## M5 — Zero-install Windows release 🚧
- [x] Standalone EXE and Portable workflow definitions.
- [x] Real API 36 smoke-build definition.
- [x] Windows EXE smoke gate green with branded executable icon.
- [x] API 36 APK gate green.
- [x] Isolated managed-engine gate green.
- [x] Full Portable package gate with JDK/Gradle/bundletool green.
- [x] Signed Release APK/AAB validation gate green.
- [x] Publish `v17.0.0-beta.1`.
- [x] Clean Windows 11 user test reported successful.
- [x] One-click physical-device verification workflow implemented: ADB detection, install, package verification, launch verification and local PASS report.
- [ ] Run the physical Android-device verification on real user hardware.
- [ ] Stable v17.0.0.

### Zero-install definition

Stable Ghost must not require manual Python, JDK, Gradle, Android Studio, Node.js or Cordova installation. Everything legally redistributable is packaged with Ghost. Official Android SDK components remain the licensing exception: Ghost provisions the required components itself after explicit Android SDK terms acceptance rather than redistributing them in the public archive.
