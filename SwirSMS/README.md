# SwirSMS 0.3 Standalone

Real, local Android SMS sender. No DEMO mode, HTTP client, external API, account or INTERNET permission.

## Features
- Compose Material 3 dark UI, original chat/lightning launcher icon.
- Individual Android contact picker without READ_CONTACTS; manual numbers; selected recipients with deduplication and favourites.
- Up to 20 recipients per confirmed batch, each receiving an individual SMS.
- Explicit active SIM selection; no silent fallback when a selected SIM disappears.
- SmsManager multipart sending (max 10 parts), GSM-7/Unicode estimate and actual SIM segment count in the confirmation.
- Durable SQLite outbox, WorkManager scheduling and cancellation before the job claims a message.
- Per-segment SENT and delivery-report callbacks. SENT is never presented as DELIVERED. Duplicate callback protection and receiver token verification.
- Atomic claim blocks automatic resending after a crash; uncertain attempts need human verification.
- Searchable local history, reusable templates, groups, favourite numbers, saved draft.
- Optional biometric/device-credential app lock. Screenshots blocked only when app lock is enabled.
- Polish / English. System language detection, English fallback.
- No Android cloud backup or app-data device transfer.

## Installation and first use (PL)
Instaluj plik APK. Ta wersja ma osobny identyfikator `com.swir.swirsms.standalone` i może działać obok starszej wersji 0.2. Starsza historia i konfiguracja API nie są importowane.
Otwórz aplikację, zezwól na SMS i dostęp do stanu SIM, wybierz kartę, numer kontaktu i wiadomość. Sprawdź podsumowanie i zatwierdź wysyłkę. Operator nalicza swoje opłaty, również w roamingu. Testuj najpierw na własnym drugim numerze.

## What this does not claim
This is an outgoing SMS app, not the phone's default SMS/MMS inbox; replies remain in the system messaging app. It has no alphanumeric sender name or Flash/Class 0 switch: these are not available through the ordinary standalone Android SMS sending interface. No hidden gateway is used.

Scheduling is **not exact**: WorkManager can be delayed by Android. The phone must be on, unlocked after boot, have permission, an active selected SIM and service. Force-stop can prevent scheduled execution until the app is reopened. If execution is over 24 hours late the message is expired instead of sent. There is no automatic resend on no-service, errors or uncertain outcomes. Scheduled jobs already approved by the user can run while the UI is locked. Cancellation is effective only before a job claims the message.

The UI lock does not provide end-to-end encryption for SMS. Local data is in Android's private app storage. Uninstalling removes this data. Clearing SwirSMS history does not clear messages in other SMS apps or recipients' devices.

## Build
JDK 17, Gradle 9.6.0, Android SDK 36; dependencies are pinned in Gradle files. From this directory:
```
gradle :app:assembleDebug :app:testDebugUnitTest :app:lintDebug
```
Use Android Studio's installed Gradle or a locally installed Gradle 9.6.0. No incomplete/encoded source payload is used. CI also builds Android instrumentation tests and runs them on an emulator. Check `VERIFICATION` artifacts for actual results; no real carrier delivery can be verified on an emulator.

Debug-signed beta for device testing, not a production/store-signed stable release. New release signing identity and physical SIM/dual-SIM/device-lock tests are required before calling a release stable.

## Authoritative Android references
- https://developer.android.com/reference/android/telephony/SmsManager
- https://developer.android.com/develop/background-work/background-tasks/persistent/getting-started/define-work
- https://developer.android.com/identity/sign-in/biometric-auth

by Swir
