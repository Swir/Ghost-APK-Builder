$ErrorActionPreference = "Stop"
py -m pip install -r requirements-build.txt
py -m compileall -q app.py ghost_builder tests
py -m unittest discover -s tests -v
pyinstaller --noconfirm --clean --onefile --windowed --collect-all customtkinter --name "Ghost-APK-Builder" app.py
Write-Host "Built: dist\Ghost-APK-Builder.exe"
