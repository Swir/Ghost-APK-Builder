# Portable and zero-manual-install model

Ghost's Windows distribution is designed so the user does not manually install development tools.

## Standalone EXE

PyInstaller bundles Python, CustomTkinter, Pillow and Ghost source into the Windows executable.

## Portable ZIP

The Portable release additionally contains:

- Eclipse Temurin JDK 21;
- Gradle 9.6.0;
- Google bundletool 1.18.3;
- bundletool Apache 2.0 license;
- runtime manifest and project documentation.

Ghost prefers these portable tools before looking at managed or system installations.

## Android SDK

Android SDK packages are license-gated and are therefore not redistributed as part of Ghost's public Portable ZIP. Ghost asks the user to review/accept the Android SDK terms, then downloads and installs the required command-line tools, Platform Tools, API 36 and Build Tools 36.0.0 into `%LOCALAPPDATA%\GhostAPKBuilder\toolchain`.

This is still a zero-manual-install workflow: the user does not install Android Studio or configure SDK environment variables.

## Repair

Repair only deletes/recreates Ghost-managed toolchain folders. It must never delete a system JDK, Android Studio SDK, Gradle installation or unrelated project.

## Checksums

Release packaging verifies the upstream JDK and Gradle checksums, uses pinned checksums for Android command-line tools and bundletool, then emits `.sha256` files for Ghost EXE and Portable ZIP assets.
