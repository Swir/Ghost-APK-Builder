# Changelog

All notable changes to Ghost APK Builder v17 are documented here.

## 17.0.0-dev.2 — 2026-09-15

### Added
- Polish and English desktop UI.
- Automatic system-language detection: Polish locales use Polish; all other locales fall back to English.
- Manual PL/EN switch with persisted preference.
- Dedicated `ghost_builder.i18n` module.
- Runtime permission helper generation for Camera, Location and Microphone.
- Default launcher icon and custom image → adaptive launcher icon generation.
- MainActivity runtime setup injection for status bar, fullscreen and dangerous permission requests.
- Full JDK readiness checks for `java`, `keytool` and `jarsigner`.
- `apksigner` Build Engine readiness check.
- Strict managed-toolchain mode for isolated CI.
- Explicit Android SDK license acceptance requirement before SDK package provisioning.
- Log copy, clear and export controls.
- Expanded security/localization/generator test coverage.
- Architecture, localization and portable-runtime documentation.

### Changed
- Updated desktop layout to a cleaner 1280×840 Ghost dark interface.
- Build Engine status is stricter and will not report READY if signing/validation tooling is incomplete.
- Roadmap now defines explicit stable-release gates.

## 17.0.0-dev.1 — 2026-09-15

### Added
- Ground-up v17 modular architecture.
- Deterministic Android project generator.
- Android API 36 / AGP 9.4.0 / Gradle 9.6.0 profile.
- Managed JDK/Gradle/Android SDK/bundletool discovery and provisioning.
- Safe managed-component repair.
- APK/AAB build and validation pipeline.
- Session-only signing secrets.
- Initial CustomTkinter UI.
- Preserved v16.4 source and audit.
