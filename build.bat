@echo off
echo.
echo  ╔══════════════════════════════╗
echo  ║   WAPI — Build Script        ║
echo  ╚══════════════════════════════╝
echo.
echo Installiere Abhängigkeiten...
pip install -r requirements.txt

echo.
echo Erstelle WAPI.exe ...
pyinstaller ^
  --onefile ^
  --windowed ^
  --icon=assets\icon.ico ^
  --name=WAPI ^
  --add-data="assets;assets" ^
  --clean ^
  main.py

echo.
if exist dist\WAPI.exe (
    echo  ✓ Build erfolgreich!
    echo  → dist\WAPI.exe
) else (
    echo  ✗ Build fehlgeschlagen. Bitte Fehlermeldung oben prüfen.
)
echo.
pause
