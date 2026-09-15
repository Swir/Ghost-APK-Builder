# Changelog

## 17.0.0-beta.1 — 2026-09-15

### Added
- Simple / Advanced desktop UI mode with persisted preference.
- Official Ghost application icon for Windows EXE and Portable packaging.
- Signed Release APK and AAB CI gate with real signature validation.
- Standalone Windows EXE smoke launch without a system Python runtime.
- Real Android API 36 APK build gate.
- Isolated managed Build Engine Prepare/Repair gate.
- Verified Portable Windows packaging gate with JDK 21, Gradle 9.6 and bundletool 1.18.3.

### Improved
- Polish/English workflow remains automatic: Polish system locales start in Polish, other locales start in English, and the PL/EN switch is always available.
- Beginner workflow hides advanced Android, Kotlin, signing, engine and diagnostics tabs until Advanced mode is selected or an advanced action requires them.
- Release signing secrets remain session-only and are checked for accidental persistence during CI.

### Validation
- Python 3.11 / 3.12 / 3.13 quality matrix.
- `apksigner` verification for signed Release APK.
- `bundletool validate` and `jarsigner -verify` for signed AAB.

### Known beta limitation
- Official Android SDK components are provisioned by Ghost after Android SDK terms acceptance; they are not bundled in the public Portable archive.

## 17.0.0-dev.2 — 2026-09-15

### Added
- Polish/English UI with system-language detection and persisted manual switch.
- Quick Start three-step dashboard.
- Bilingual first-run onboarding wizard.
- Live Project and Build Engine readiness badges.
- Modular UI shell/layout/actions/theme split.
- Runtime Camera/Location/Microphone permissions and adaptive icons.
- Full JDK/apksigner readiness checks and managed-toolchain mode.
- Explicit Android SDK license consent and expanded security/localization tests.

### Changed
- Replaced the v16 Android Studio clone/patch model with clean project generation.
- Updated profile to Android API 36 / AGP 9.4 / Gradle 9.6 / Build Tools 36.0.0 / JDK 21.
- Signing passwords are session-only and never written to config or generated Gradle files.
