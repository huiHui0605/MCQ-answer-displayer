@echo off
setlocal
cd /d "%~dp0"
py -3 -m venv .venv
if errorlevel 1 goto failed
.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto failed
echo Python dependencies installed.
echo Next: install Ollama, run ollama pull qwen2.5:3b, and copy your PDFs into notes.
pause
exit /b 0
:failed
echo Setup failed. Install Python with Tcl/Tk and the Python launcher, then try again.
pause
exit /b 1
