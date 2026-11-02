@echo off
rem Bump'em server with the real board (production mode, all four towers). Pick the Teensy's COM port in the page, Connect.
cd /d "%~dp0BumpemServer"
set PYTHONUTF8=1
rem open the page 4 s later, once the server is up
start "" /min cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/ui/"
..\venv\Scripts\python -m bumpem.cli serve --production --modules ABCD
pause
