# Security

## Signing secrets
Ghost v17 does not persist keystore passwords. Passwords exist only in the running process and are passed to Gradle through `GHOST_STORE_PASSWORD` / `GHOST_KEY_PASSWORD` environment variables. Do not add passwords, keystores or release credentials to the repository.

## Managed toolchain
Ghost-managed downloads live under `%LOCALAPPDATA%\GhostAPKBuilder`. Repair actions must only modify that managed directory. System JDK/Gradle/Android installations must never be deleted or terminated.

## Reporting
Do not publish signing keys, Google service credentials or private application configuration in a public issue. Report reproducible security problems without secrets.
