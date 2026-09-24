@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m pytest tests -q
if errorlevel 1 goto fail
.venv\Scripts\python.exe -m PyInstaller MCRank.spec --noconfirm
if errorlevel 1 goto fail
echo Ready: dist\MCRank\MCRank.exe
pause
exit /b 0
:fail
echo Build failed. See messages above.
pause
exit /b 1
