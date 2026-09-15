# Contributing

Repository-facing content is written in English. User-facing desktop strings belong in `ghost_builder/i18n.py` and must include both English and Polish until the localization policy changes.

Before opening a pull request:

```powershell
py -m pip install -r requirements-build.txt
py -m py_compile app.py ghost_builder/*.py
py -m unittest discover -s tests -v
```

Do not commit keystores, signing passwords, generated APK/AAB files, local toolchains or SDK license acceptance state.

Changes to the Build Engine should include a test proving they do not modify unrelated system installations.
