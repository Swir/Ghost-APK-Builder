# Konofix Android 0.1.0-dev.2: interoperability candidate

A source archive is not an APK. Install only the signed APK in a successful
Konofix-Android-APK workflow artifact. No real Android/PC exchange has been verified.

- ARM64 Android 8 or later; PC protocol baseline is Konofix 0.5.1 pinned to commit 31298cc732c97ff90230c3743cd1c3be17f40b6c.
- Use a different nickname on the PC and phone. Keep both applications open.
- Start with the same Wi-Fi to test discovery, then test phone LTE against PC broadband.
- Send a unique message in #WORLD in BOTH directions. Read it on the actual receiver:
  a local echo and a transport connection count do not prove delivery.
- Keep the phone application visible and the screen on. Background notifications,
  files, private messages, other rooms and audio are not enabled in this test.
- Fully restart the Android application after changing Wi-Fi/LTE so DNS settings
  are recaptured. DNS comes from the active network, with no hard-coded public fallback.
  System Private DNS/VPN behavior has not yet been qualified.
- If the UI fails or peers cannot connect, retain a screenshot of the diagnostics.
  Do not post sensitive chats or private network details publicly.

This branch is an isolated build workspace. Swir/Konofix and Ghost-APK-Builder main
are not modified. Never merge this branch into builder main.
