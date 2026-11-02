@echo off
rem Bump'em offline install: Python 3.12 for this user (no admin), then a venv with the packages from wheels\.
setlocal
cd /d "%~dp0"
set PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe
if not exist "%PY%" (
  echo Installing Python 3.12 for this user, takes about a minute...
  installers\python-3.12.10-amd64.exe /quiet InstallAllUsers=0 PrependPath=0 Include_launcher=0 Include_test=0 Include_tcltk=1 Shortcuts=0
)
if not exist "%PY%" (
  echo.
  echo Python did not install. Run installers\python-3.12.10-amd64.exe by hand: "Install for this user only", untick "Add to PATH".
  echo If that is blocked too, the PC has app lockdown: ask the administrator.
  pause & exit /b 1
)
if not exist venv\Scripts\python.exe (
  "%PY%" -m venv venv
  if errorlevel 1 (echo venv failed & pause & exit /b 1)
)
venv\Scripts\python -m pip install --no-index --find-links wheels -r requirements.txt || (echo package install failed & pause & exit /b 1)
venv\Scripts\python -c "import serial, fastapi, uvicorn, websockets, tkinter; print('All packages OK')" || (echo check failed & pause & exit /b 1)
echo.
echo Done. Next: start_simulator.bat (no hardware) or start_server.bat (Teensy plugged in).
pause
