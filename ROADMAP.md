# Ghost APK Builder v17 Roadmap

This roadmap is the source of truth for v17 development. Items are marked complete only when the implementation exists and has an appropriate test or CI gate.

## M0 — Audit and safe architecture ✅

- [x] Preserve v16.4 under `legacy/`.
- [x] Full v16.4 source audit.
- [x] Remove global Java process termination from the new architecture.
- [x] Stop persisting JKS passwords.
- [x] Replace Android Studio base-project dependency with deterministic project generation.
- [x] Separate UI, model, generator, builder, toolchain and localization modules.
- [x] Validate package/version/API inputs before build.
- [x] Move the default Google Play profile to Android API 36.
- [x] Remove retired WSA workflow from the main product path.

## M1 — Managed Build Engine 🚧

- [x] Portable / Ghost-managed / compatible-system JDK discovery.
- [x] Require a complete JDK (`java`, `keytool`, `jarsigner`).
- [x] Portable / managed / system Gradle discovery.
- [x] Android SDK command-line tool provisioning.
- [x] Android API 36 + Build Tools 36.0.0 + Platform Tools provisioning.
- [x] `apksigner` readiness check.
- [x] SHA-256 verification for Android command-line tools and bundletool.
- [x] Official checksum verification for managed JDK and Gradle downloads.
- [x] Resume/retry managed downloads.
- [x] Safe Repair limited to Ghost-managed components.
- [x] Strict `GHOST_FORCE_MANAGED_TOOLCHAIN=1` mode for isolated testing.
- [x] Explicit Android SDK license consent required before SDK package installation.
- [ ] Full clean-machine Prepare/Repair CI gate green on the repository.
- [ ] Offline cache export/import for user-provided SDK/toolchain caches.
- [ ] Optional Stable / Preview toolchain channels.

## M2 — Native Android generator 🚧

- [x] Clean AGP 9.4 / Gradle 9.6 project generation.
- [x] AGP built-in Kotlin compilation model.
- [x] APK / AAB output.
- [x] Debug / Release variants.
- [x] API 36 target and configurable minSdk.
- [x] Safe XML escaping and package validation.
- [x] Internet / Camera / Location / Microphone manifest permissions.
- [x] Runtime permission helper generation for Camera / Location / Microphone.
- [x] Cleartext HTTP disabled by default.
- [x] Splash generation.
- [x] Assets import.
- [x] Default launcher icon generation.
- [x] Custom image → launcher/adaptive icon generation.
- [x] Fullscreen/status-bar setup injection into generated MainActivity.
- [ ] Template/snippet migration from v16.4 with compile tests.
- [ ] Firebase configuration validator.
- [ ] Current AdMob/Billing modules with policy-safe defaults.
- [ ] WebView template with camera/microphone/location/file-upload bridges.
- [ ] Richer resource editor (colors, themes, splash timing, adaptive icon safe-zone preview).

## M3 — Signing and release validation 🚧

- [x] Session-only signing passwords.
- [x] Environment-variable Gradle signing.
- [x] Managed `keytool` JKS generation.
- [x] APK `apksigner` validation.
- [x] AAB bundletool validation.
- [x] Signed AAB `jarsigner` validation.
- [ ] Ephemeral-keystore signed Release APK/AAB CI gate.
- [ ] Play readiness report.
- [ ] Automatic versionCode strategy.
- [ ] Signing-certificate fingerprint display.
- [ ] Keystore backup warning/export helper.

## M4 — Ghost desktop UI 🚧

- [x] Modern CustomTkinter dark UI foundation.
- [x] Responsive 1280×840 window with 1040×700 minimum.
- [x] Project / Kotlin / Android / Signing / Build Engine / Logs separation.
- [x] Thread-safe worker → UI event queue.
- [x] Build Engine status badge and detailed panel.
- [x] Analyze-before-build validation.
- [x] Log copy / clear / export controls.
- [x] Polish and English UI dictionaries.
- [x] Polish system locale auto-detection.
- [x] English fallback for every non-Polish system locale.
- [x] Manual PL / EN switch with persisted preference.
- [ ] Simple / Advanced mode.
- [ ] Recent projects and reusable profiles.
- [ ] Project import/export (`.ghostproject`).
- [ ] First-run setup wizard.
- [ ] Build history with artifact shortcuts.
- [ ] High-DPI and keyboard accessibility pass.
- [ ] Dedicated branded app icon and installer graphics.

## M5 — Zero-install Windows release 🚧

- [x] PyInstaller one-file configuration in CI.
- [x] Portable package workflow design.
- [x] Portable runtime includes EXE + JDK 21 + Gradle 9.6 + bundletool 1.18.3.
- [x] Runtime manifest and third-party notices.
- [x] SHA-256 release asset generation.
- [x] Portable EXE smoke-test step defined.
- [x] Real API 36 APK smoke-build job defined.
- [ ] Repository CI green for Windows EXE smoke test.
- [ ] Repository CI green for real API 36 APK build.
- [ ] Repository CI green for isolated managed Build Engine Prepare/Repair.
- [ ] Repository release-package workflow green.
- [ ] Public `v17.0.0-beta.1` GitHub Release.
- [ ] Test beta on a clean Windows 11 machine.
- [ ] Test APK install on a physical Android device.
- [ ] Stable `v17.0.0` after all release criteria pass.

### Zero-install definition

Stable Ghost v17 must not require the user to manually install Python, Python packages, JDK, Gradle, Android Studio, Node.js or Cordova. Android SDK components are provisioned by Ghost after explicit SDK-license acceptance; they are not redistributed in the GitHub Portable archive.

## M6 — Post-v17 quality and ecosystem

- [ ] Plugin API.
- [ ] Template marketplace/import format.
- [ ] Optional Play Console workflow where account/API permissions allow it.
- [ ] SBOM and dependency/license inventory per release.
- [ ] Reproducibility/determinism report.
- [ ] Optional Authenticode signing when a suitable certificate is available.
- [ ] Linux/macOS desktop builds where the managed Android toolchain is validated.

## Stable v17.0.0 release criteria

Stable release is blocked until all of the following are true:

1. Windows EXE launches without Python installed or present in runtime paths.
2. Portable ZIP launches and finds its bundled JDK, Gradle and bundletool.
3. Managed Build Engine can provision Android API 36 into an empty Ghost user-data directory.
4. Repair restores deliberately damaged Ghost-managed components without touching unrelated system tools.
5. A generated project builds a real API 36 Debug APK in CI.
6. Signed Release APK and AAB builds pass signature and bundle validation.
7. Signing passwords never appear in config, generated Gradle files or repository files.
8. Polish locale launches in Polish; every unsupported locale launches in English; manual PL/EN switch persists.
9. README, ROADMAP, CHANGELOG, SECURITY, migration and third-party notices match actual product behavior.
10. Public beta has been tested on a clean Windows 11 machine and at least one physical Android device.
