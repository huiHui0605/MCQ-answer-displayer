@echo off
setlocal
cd /d "%~dp0"
if not exist .venv-py312\Scripts\python.exe goto needs_setup
.venv-py312\Scripts\python.exe -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 goto needs_setup
.venv-py312\Scripts\python.exe check_setup.py
if errorlevel 1 (
  pause
  exit /b 1
)
.venv-py312\Scripts\python.exe app.py
if errorlevel 1 (
  pause
  exit /b 1
)
exit /b 0
:needs_setup
echo Run setup_windows.bat first. A 64-bit Python 3.12 environment in .venv-py312 is required.
pause
exit /b 1
