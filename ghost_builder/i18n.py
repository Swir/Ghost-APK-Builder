from __future__ import annotations

import locale
import os
import sys
from dataclasses import dataclass

SUPPORTED_LANGUAGES = ("pl", "en")
DEFAULT_LANGUAGE = "en"


def normalize_language(value: str | None) -> str:
    if not value:
        return DEFAULT_LANGUAGE
    code = value.strip().replace("-", "_").lower()
    return "pl" if code == "pl" or code.startswith("pl_") else "en"


def detect_system_language() -> str:
    """Detect Polish on Windows/Linux/macOS, otherwise fall back to English."""
    candidates: list[str] = []
    if sys.platform == "win32":
        try:
            import ctypes
            buffer = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buffer, len(buffer)):
                candidates.append(buffer.value)
        except Exception:
            pass
    try:
        current = locale.getlocale()[0]
        if current:
            candidates.append(current)
    except Exception:
        pass
    for key in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        value = os.environ.get(key)
        if value:
            candidates.append(value.split(":", 1)[0])
    for candidate in candidates:
        if normalize_language(candidate) == "pl":
            return "pl"
    return "en"


STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "app.subtitle": "Native Android builder • API 36 • zero manual toolchain setup",
        "engine.checking": "Build Engine: checking…",
        "engine.ready": "Build Engine: READY",
        "engine.setup": "Build Engine: setup required",
        "lang.label": "Language",
        "tab.project": "Project",
        "tab.kotlin": "Kotlin",
        "tab.android": "Android",
        "tab.signing": "Signing",
        "tab.engine": "Build Engine",
        "tab.logs": "Logs",
        "project.application": "Application",
        "project.application_sub": "Ghost generates a clean Android project from scratch. Android Studio is not required.",
        "project.app_name": "App name",
        "project.package": "Package",
        "project.version": "Version",
        "project.output": "Output",
        "project.output_sub": "APK for direct testing/install, AAB for Google Play.",
        "project.output_folder": "Output folder",
        "project.browse_output": "Browse output folder",
        "project.assets": "Assets folder",
        "project.browse_assets": "Browse assets",
        "project.icon": "App icon",
        "project.browse_icon": "Choose icon",
        "kotlin.description": "Ghost inserts the package declaration automatically. AGP 9.4 uses built-in Kotlin support.",
        "android.target": "Android target",
        "android.target_sub": "Google Play profile: API {api}, Build Tools {build_tools}.",
        "android.min_sdk": "Min SDK",
        "android.target_sdk": "Target SDK",
        "android.orientation": "Orientation",
        "android.permissions": "Permissions & privacy",
        "android.permissions_sub": "Broad legacy storage permissions are not generated. Cleartext HTTP is disabled by default.",
        "android.internet": "Internet",
        "android.camera": "Camera",
        "android.location": "Location",
        "android.microphone": "Microphone",
        "android.cleartext": "Allow cleartext HTTP",
        "android.backup": "Allow Android backup",
        "android.runtime": "Runtime appearance",
        "android.splash": "Splash screen",
        "android.fullscreen": "Fullscreen",
        "android.hardware": "Hardware acceleration",
        "android.adb": "Install APK on connected device after build",
        "android.minify": "Minify/shrink Release build",
        "signing.title": "Release signing",
        "signing.subtitle": "Passwords are session-only and are never written to config or generated Gradle files.",
        "signing.enable": "Sign Release builds",
        "signing.keystore": "Keystore",
        "signing.browse": "Browse keystore",
        "signing.alias": "Key alias",
        "signing.store_password": "Store password",
        "signing.key_password": "Key password",
        "signing.generate": "Generate secure JKS",
        "signing.notice": "Keep the generated password somewhere safe. Ghost deliberately does not save it.",
        "engine.title": "Managed Build Engine",
        "engine.subtitle": "Portable JDK/Gradle/bundletool are preferred. Android SDK is provisioned into Ghost's private user folder after license acceptance.",
        "engine.prepare": "Prepare Build Engine",
        "engine.repair": "Repair Build Engine",
        "engine.refresh": "Refresh status",
        "engine.terms": "Open Android SDK terms",
        "engine.privacy": "No administrator rights, Android Studio, global Java/Gradle changes, Node.js or Cordova are required.",
        "logs.title": "Build & diagnostic logs",
        "logs.copy": "Copy logs",
        "logs.clear": "Clear logs",
        "logs.export": "Export logs",
        "footer.build": "BUILD APPLICATION",
        "footer.analyze": "Analyze",
        "footer.save": "Save",
        "busy.building": "BUILDING…",
        "busy.preparing": "PREPARING BUILD ENGINE…",
        "busy.repairing": "REPAIRING BUILD ENGINE…",
        "msg.project_check": "Project check",
        "msg.project_ready": "Project is ready for Android API {api} generation.",
        "msg.project_passed": "Project validation passed",
        "msg.saved": "Configuration saved to {path}",
        "msg.sdk_license_title": "Android SDK license",
        "msg.sdk_license": "Ghost will download Android command-line tools and SDK components into its private user folder.\n\nBy continuing you confirm that you reviewed and accept the Android SDK terms. Continue?",
        "msg.engine_done": "Build Engine operation completed",
        "msg.engine_unavailable": "keytool is not available. Prepare Build Engine first.",
        "msg.keystore_created_title": "Keystore created",
        "msg.keystore_created": "Keystore created.\n\nAlias: {alias}\nPassword: {password}\n\nSave this password safely. Ghost will NOT save it.",
        "msg.keystore_error": "Keystore error",
        "msg.cannot_build": "Cannot build",
        "msg.engine_not_ready": "Build Engine is not ready. Open the Build Engine tab and prepare it first.",
        "msg.build_complete_title": "Build complete",
        "msg.build_complete": "Application created successfully:\n{path}",
        "msg.build_failed": "Build failed",
        "msg.logs_copied": "Logs copied to clipboard.",
        "msg.logs_exported": "Logs exported to {path}",
        "msg.language_changed": "Language changed to English.",
        "validation.app_name_required": "Application name is required.",
        "validation.app_name_long": "Application name must be 80 characters or fewer.",
        "validation.package": "Package name must look like com.example.app and every segment must start with a letter.",
        "validation.version_name": "Version name contains unsupported characters.",
        "validation.version_code": "Version code must be a positive integer.",
        "validation.min_sdk": "Min SDK must be between 23 and 36 for the v17 build profile.",
        "validation.target_sdk": "Target SDK must be API 36 or newer for current Google Play submission requirements.",
        "validation.sdk_order": "Min SDK cannot be higher than Target SDK.",
        "validation.build_mode": "Build mode must be Debug or Release.",
        "validation.export_format": "Export format must be APK or AAB.",
        "validation.orientation": "Unsupported screen orientation.",
        "validation.splash_color": "Splash background must be a #RRGGBB color.",
        "validation.status_color": "Status bar color must be a #RRGGBB color.",
        "validation.keystore_missing": "Release signing is enabled but the keystore file is missing.",
        "validation.alias_missing": "Release signing is enabled but the key alias is empty.",
        "validation.assets_missing": "Assets folder does not exist.",
        "validation.icon_missing": "Selected app icon does not exist.",
    },
    "pl": {
        "app.subtitle": "Natywny kreator Android • API 36 • bez ręcznej instalacji narzędzi",
        "engine.checking": "Silnik kompilacji: sprawdzanie…",
        "engine.ready": "Silnik kompilacji: GOTOWY",
        "engine.setup": "Silnik kompilacji: wymaga przygotowania",
        "lang.label": "Język",
        "tab.project": "Projekt",
        "tab.kotlin": "Kotlin",
        "tab.android": "Android",
        "tab.signing": "Podpis",
        "tab.engine": "Silnik kompilacji",
        "tab.logs": "Logi",
        "project.application": "Aplikacja",
        "project.application_sub": "Ghost generuje czysty projekt Android od zera. Android Studio nie jest wymagane.",
        "project.app_name": "Nazwa aplikacji",
        "project.package": "Pakiet",
        "project.version": "Wersja",
        "project.output": "Plik wynikowy",
        "project.output_sub": "APK do testów i instalacji, AAB do Google Play.",
        "project.output_folder": "Folder zapisu",
        "project.browse_output": "Wybierz folder zapisu",
        "project.assets": "Folder Assets",
        "project.browse_assets": "Wybierz Assets",
        "project.icon": "Ikona aplikacji",
        "project.browse_icon": "Wybierz ikonę",
        "kotlin.description": "Ghost automatycznie dodaje deklarację pakietu. AGP 9.4 korzysta z wbudowanej obsługi Kotlina.",
        "android.target": "Docelowy Android",
        "android.target_sub": "Profil Google Play: API {api}, Build Tools {build_tools}.",
        "android.min_sdk": "Min SDK",
        "android.target_sdk": "Target SDK",
        "android.orientation": "Orientacja",
        "android.permissions": "Uprawnienia i prywatność",
        "android.permissions_sub": "Stare szerokie uprawnienia pamięci nie są generowane. HTTP bez TLS jest domyślnie wyłączony.",
        "android.internet": "Internet",
        "android.camera": "Aparat",
        "android.location": "Lokalizacja",
        "android.microphone": "Mikrofon",
        "android.cleartext": "Zezwól na zwykły HTTP",
        "android.backup": "Zezwól na kopię Android",
        "android.runtime": "Wygląd i działanie",
        "android.splash": "Ekran startowy",
        "android.fullscreen": "Pełny ekran",
        "android.hardware": "Akceleracja sprzętowa",
        "android.adb": "Po kompilacji zainstaluj APK na podłączonym urządzeniu",
        "android.minify": "Minifikuj i zmniejsz build Release",
        "signing.title": "Podpis Release",
        "signing.subtitle": "Hasła istnieją tylko w bieżącej sesji i nigdy nie są zapisywane do konfiguracji ani wygenerowanych plików Gradle.",
        "signing.enable": "Podpisuj buildy Release",
        "signing.keystore": "Keystore",
        "signing.browse": "Wybierz keystore",
        "signing.alias": "Alias klucza",
        "signing.store_password": "Hasło magazynu",
        "signing.key_password": "Hasło klucza",
        "signing.generate": "Wygeneruj bezpieczny JKS",
        "signing.notice": "Zapisz wygenerowane hasło w bezpiecznym miejscu. Ghost celowo go nie zapisuje.",
        "engine.title": "Zarządzany silnik kompilacji",
        "engine.subtitle": "Ghost preferuje przenośne JDK/Gradle/bundletool. Android SDK jest przygotowywany w prywatnym folderze użytkownika po zaakceptowaniu licencji.",
        "engine.prepare": "Przygotuj silnik kompilacji",
        "engine.repair": "Napraw silnik kompilacji",
        "engine.refresh": "Odśwież status",
        "engine.terms": "Otwórz warunki Android SDK",
        "engine.privacy": "Nie są wymagane uprawnienia administratora, Android Studio, globalne zmiany Java/Gradle, Node.js ani Cordova.",
        "logs.title": "Logi kompilacji i diagnostyki",
        "logs.copy": "Kopiuj logi",
        "logs.clear": "Wyczyść logi",
        "logs.export": "Eksportuj logi",
        "footer.build": "ZBUDUJ APLIKACJĘ",
        "footer.analyze": "Analizuj",
        "footer.save": "Zapisz",
        "busy.building": "KOMPILOWANIE…",
        "busy.preparing": "PRZYGOTOWYWANIE SILNIKA…",
        "busy.repairing": "NAPRAWIANIE SILNIKA…",
        "msg.project_check": "Sprawdzenie projektu",
        "msg.project_ready": "Projekt jest gotowy do generowania dla Android API {api}.",
        "msg.project_passed": "Walidacja projektu zakończona pomyślnie",
        "msg.saved": "Konfiguracja zapisana w {path}",
        "msg.sdk_license_title": "Licencja Android SDK",
        "msg.sdk_license": "Ghost pobierze Android command-line tools i wymagane komponenty SDK do prywatnego folderu programu.\n\nKontynuując potwierdzasz, że zapoznałeś się z warunkami Android SDK i je akceptujesz. Kontynuować?",
        "msg.engine_done": "Operacja silnika kompilacji zakończona",
        "msg.engine_unavailable": "keytool jest niedostępny. Najpierw przygotuj silnik kompilacji.",
        "msg.keystore_created_title": "Utworzono keystore",
        "msg.keystore_created": "Utworzono keystore.\n\nAlias: {alias}\nHasło: {password}\n\nZapisz to hasło w bezpiecznym miejscu. Ghost go NIE zapisze.",
        "msg.keystore_error": "Błąd keystore",
        "msg.cannot_build": "Nie można rozpocząć kompilacji",
        "msg.engine_not_ready": "Silnik kompilacji nie jest gotowy. Otwórz kartę Silnik kompilacji i przygotuj go.",
        "msg.build_complete_title": "Kompilacja zakończona",
        "msg.build_complete": "Aplikacja została utworzona pomyślnie:\n{path}",
        "msg.build_failed": "Błąd kompilacji",
        "msg.logs_copied": "Logi skopiowano do schowka.",
        "msg.logs_exported": "Logi wyeksportowano do {path}",
        "msg.language_changed": "Język zmieniono na polski.",
        "validation.app_name_required": "Nazwa aplikacji jest wymagana.",
        "validation.app_name_long": "Nazwa aplikacji może mieć maksymalnie 80 znaków.",
        "validation.package": "Nazwa pakietu musi wyglądać jak com.example.app, a każdy segment musi zaczynać się literą.",
        "validation.version_name": "Nazwa wersji zawiera niedozwolone znaki.",
        "validation.version_code": "Kod wersji musi być dodatnią liczbą całkowitą.",
        "validation.min_sdk": "Min SDK musi mieścić się w zakresie 23–36 dla profilu v17.",
        "validation.target_sdk": "Target SDK musi wynosić co najmniej API 36 zgodnie z aktualnymi wymaganiami Google Play.",
        "validation.sdk_order": "Min SDK nie może być wyższe niż Target SDK.",
        "validation.build_mode": "Tryb kompilacji musi być Debug lub Release.",
        "validation.export_format": "Format eksportu musi być APK lub AAB.",
        "validation.orientation": "Nieobsługiwana orientacja ekranu.",
        "validation.splash_color": "Kolor tła ekranu startowego musi mieć format #RRGGBB.",
        "validation.status_color": "Kolor paska statusu musi mieć format #RRGGBB.",
        "validation.keystore_missing": "Podpis Release jest włączony, ale brakuje pliku keystore.",
        "validation.alias_missing": "Podpis Release jest włączony, ale alias klucza jest pusty.",
        "validation.assets_missing": "Folder Assets nie istnieje.",
        "validation.icon_missing": "Wybrany plik ikony aplikacji nie istnieje.",
    },
}


@dataclass
class Translator:
    language: str = DEFAULT_LANGUAGE

    def __post_init__(self) -> None:
        self.language = normalize_language(self.language)

    def set_language(self, language: str) -> None:
        self.language = normalize_language(language)

    def __call__(self, key: str, **kwargs) -> str:
        table = STRINGS.get(self.language, STRINGS[DEFAULT_LANGUAGE])
        value = table.get(key, STRINGS[DEFAULT_LANGUAGE].get(key, key))
        try:
            return value.format(**kwargs)
        except Exception:
            return value
