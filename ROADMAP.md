# Ghost APK Builder v17 Roadmap

This roadmap is the source of truth for v17 development.

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
- [ ] Clean-machine Prepare/Repair CI green.
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
- [ ] Ephemeral signed Release APK/AAB CI gate.
- [ ] Play readiness report and certificate fingerprints.

## M4 — Desktop UI 🚧
- [x] Modern Ghost dark UI and modular UI code.
- [x] Quick Start dashboard with readiness badges.
- [x] First-run bilingual onboarding wizard.
- [x] PL system detection, English fallback and persisted PL/EN switch.
- [x] Thread-safe worker queue and diagnostic logs.
- [ ] Simple / Advanced mode.
- [ ] Recent projects/profiles and `.ghostproject` files.
- [ ] Build history, artifact shortcuts, accessibility and branded graphics.

## M5 — Zero-install Windows release 🚧
- [x] Standalone EXE and Portable workflow definitions.
- [x] Real API 36 smoke-build definition.
- [ ] Windows EXE smoke gate green.
- [ ] API 36 APK gate green.
- [ ] Isolated managed-engine gate green.
- [ ] Full Portable package gate with JDK/Gradle/bundletool green.
- [ ] Public beta, clean Windows 11 test and physical Android test.
- [ ] Stable v17.0.0.

### Zero-install definition
Stable Ghost must not require manual Python, JDK, Gradle, Android Studio, Node.js or Cordova installation. Android SDK is provisioned by Ghost after explicit license acceptance.
