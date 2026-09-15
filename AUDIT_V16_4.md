# Ghost APK Builder v16.4 — Technical Audit

Date: 2026-09-15

This audit records the reasons for the v17 architecture reboot. The original source is preserved unchanged in `legacy/Ghost_APK_Builder_v16_4.py`.

## Critical

### 1. Global Java termination
v16.4 executes `taskkill /F /IM java.exe /T` before a build. This can terminate Android Studio, Gradle builds, Java servers and unrelated user applications.

**v17:** removed completely. Ghost controls only the Gradle process it starts.

### 2. Signing passwords stored in plaintext
v16.4 writes `keystore_pass` and `key_pass` into `ghost_apex_config.json`, reloads them on startup and injects real passwords into generated Gradle scripts.

**v17:** password keys are stripped from persisted configuration. Signing secrets exist only in memory and are passed via process environment variables.

### 3. Android Studio base project is mandatory
v16.4 searches `~/AndroidStudioProjects`, picks the first Gradle project and clones it into `Ghost_Apex_Workspace`. With no compatible base project the build engine cannot initialize.

**v17:** generates a deterministic Android project from scratch. Android Studio is not required.

## High

### 4. Google Play target is outdated and UI target can be ignored
v16.4 defaults to target SDK 34. Its Gradle patcher updates minSdk but does not reliably apply the targetSdk field.

**v17:** API 36 is a validated build invariant for the current Google Play profile.

### 5. Fragile regex mutation of arbitrary Gradle projects
The old builder patches unknown Gradle/Kotlin/Groovy syntax with text replacement. Results depend on whichever project happened to be cloned.

**v17:** owns the complete generated project structure and versions.

### 6. Tkinter accessed from worker threads
Build and initialization threads call logging/progress/widget methods directly. Tkinter widgets are not designed for arbitrary background-thread mutation.

**v17:** worker threads publish events to a queue; the main UI loop drains and renders them.

### 7. Shell command construction
Keytool and Gradle commands are assembled as shell strings with `shell=True` in several paths.

**v17:** subprocesses use argument arrays and `shell=False` for user-controlled paths/secrets.

## Medium

### 8. Retired WSA path
v16.4 contains a Windows Subsystem for Android path with a hard-coded localhost port.

**v17:** removes WSA from the primary product. Managed ADB deployment targets connected Android devices.

### 9. Broad legacy storage permissions
v16.4 can add `WRITE_EXTERNAL_STORAGE` and `READ_EXTERNAL_STORAGE`, which are obsolete for modern Android storage models.

**v17:** does not generate those permissions.

### 10. Cleartext HTTP enabled by default
The old default enables `usesCleartextTraffic=true`.

**v17:** cleartext is disabled by default and must be explicitly enabled.

### 11. XML/Kotlin string injection hazards
Raw application names can be inserted into XML/Kotlin source without complete escaping.

**v17:** generated XML uses escaping and project fields are validated before generation.

### 12. Package validation is too weak
The old sanitizer removes invalid characters but can still produce invalid package structures (empty segments, numeric-leading segments, etc.).

**v17:** validates every package segment before writing files.

### 13. Artifact selection can choose the wrong output
v16.4 recursively searches all APK/AAB files and chooses the first/closest mode match.

**v17:** resolves the expected Gradle output directory/task and validates the artifact before reporting success.

## Product/UI

### 14. Fixed large window and dense tabs
The old UI is hard-coded to 1500×950 and uses many fixed side-by-side frames.

**v17:** uses a responsive modern CustomTkinter layout with Quick Start, status cards and separate advanced tabs.

### 15. Configuration location
v16.4 stores its config directly in the user home directory.

**v17:** uses `%LOCALAPPDATA%\GhostAPKBuilder` for config, toolchain, downloads and workspace.

## v17 release gates before stable

The v17 line will not be called stable until CI proves:

- standalone Windows EXE startup without Python runtime paths;
- real API 36 debug APK build;
- signed Release APK/AAB build and verification;
- clean managed Build Engine provisioning/repair;
- verified Portable runtime package;
- no persisted signing passwords;
- no global Java/process termination behavior.
