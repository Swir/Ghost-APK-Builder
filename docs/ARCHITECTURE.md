# Architecture

Ghost v17 intentionally avoids the v16.4 monolithic design.

## Modules

- `model.py` — serializable project settings and validation.
- `generator.py` — deterministic Android/Gradle source and resources.
- `core.py` — toolchain discovery, download, verification, provisioning and repair.
- `builder.py` — Gradle execution, artifact discovery, validation, keystore generation and ADB deployment.
- `i18n.py` — locale detection and translation dictionaries.
- `ui.py` — application shell.
- `ui_layout.py` — Quick Start and configuration views.
- `ui_actions.py` — thread-safe user actions and orchestration.
- `ui_theme.py` — Ghost desktop visual constants.

## Data boundaries

Passwords are never part of `ProjectConfig.to_persisted_dict()`. The UI passes passwords directly to `GhostBuilder.build()` for the active build. `GhostBuilder` exposes them to Gradle only through temporary process environment variables.

## Workspace

Generated projects live in Ghost's private workspace under the application user-data directory. The generator recreates the current workspace instead of patching arbitrary Android Studio projects.

## Process safety

Ghost invokes Gradle, keytool, adb, bundletool, jarsigner and apksigner with argument arrays. It does not globally terminate Java or Gradle processes.
