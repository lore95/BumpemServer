@echo off
rem Bump'em server with the simulator: try the page without hardware. Saved settings and logs are kept apart.
cd /d "%~dp0BumpemServer"
set PYTHONUTF8=1
rem open the page 4 s later, once the server is up
start "" /min cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/ui/"
..\venv\Scripts\python -m bumpem.cli serve --board sim --production --modules ABCD --settings "%~dp0sim\settings.json" --log-dir "%~dp0sim\Logs"
pause
