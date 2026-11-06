@echo off
setlocal
cd /d "%~dp0"
rem RapidOCR 1.4.4 requires Python below 3.13. Never use unqualified py -3.
py -3.12 -c "import sys, struct, tkinter; sys.exit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 else 1)"
if errorlevel 1 goto missing_python
if exist .venv-py312 (
  if not exist .venv-py312\Scripts\python.exe goto invalid_env
  .venv-py312\Scripts\python.exe -c "import sys, struct; sys.exit(0 if sys.version_info[:2] == (3, 12) and struct.calcsize('P') == 8 else 1)"
  if errorlevel 1 goto invalid_env
)
py -3.12 -m venv .venv-py312
if errorlevel 1 goto venv_failed
.venv-py312\Scripts\python.exe --version
.venv-py312\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto install_failed
echo Python dependencies installed in .venv-py312. Your old .venv was not changed.
echo Next: install Ollama, run ollama pull qwen2.5:3b, and copy your PDFs into notes.
pause
exit /b 0
:missing_python
echo This app requires 64-bit Python 3.12 with Tcl/Tk and the Python Launcher.
echo Python 3.13 and newer are not compatible with the pinned OCR package.
echo Install the Windows installer 64-bit from:
echo https://www.python.org/downloads/release/python-31210/
echo Keep Tcl/Tk and Python Launcher selected. You do not need to uninstall other Python versions.
echo Then run this script again.
pause
exit /b 1
:invalid_env
echo .venv-py312 exists but is not a usable 64-bit Python 3.12 environment.
echo Rename that folder to preserve it, then run this script again.
pause
exit /b 1
:venv_failed
echo Failed to create .venv-py312. Check folder permissions and Python installation.
pause
exit /b 1
:install_failed
echo Dependency installation failed. Read the pip error above for details.
echo The script used Python 3.12. Your notes and Ollama models were not changed.
pause
exit /b 1
