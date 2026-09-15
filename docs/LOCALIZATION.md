# Localization

Ghost APK Builder keeps repository documentation in English while the desktop application supports Polish and English.

## Startup language

On first launch Ghost checks the system/user locale:

- locale beginning with `pl` → `pl`;
- every other locale → `en`.

The implementation includes a Windows locale API path and portable fallbacks for Python locale/environment values.

## Manual override

The top bar contains a `PL / EN` switch. A manual selection is persisted as `language` in Ghost's configuration file and becomes the preferred language on later launches.

Signing passwords are never stored alongside this preference.

## Fallback rule

English is the mandatory fallback. Missing translation keys also fall back to the English dictionary so the UI never intentionally exposes an empty label because of localization.

## Adding another language later

1. Add a new dictionary to `ghost_builder/i18n.py`.
2. Extend `SUPPORTED_LANGUAGES` and `normalize_language`.
3. Add the language to the UI selector.
4. Add locale-detection tests and translation-key coverage tests.
5. Keep English as the final fallback.
