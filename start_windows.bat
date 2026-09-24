@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  py -3 -m venv .venv
  if errorlevel 1 goto fail
)
if not exist ".venv\mcrank-ready" (
  .venv\Scripts\python.exe -m pip install -r requirements.txt
  if errorlevel 1 goto fail
  echo ready> .venv\mcrank-ready
)
.venv\Scripts\python.exe run.py
if errorlevel 1 goto fail
exit /b 0
:fail
echo MCRank could not start. Check Python 64-bit, network and the error above.
pause
exit /b 1
