# Changelog

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
