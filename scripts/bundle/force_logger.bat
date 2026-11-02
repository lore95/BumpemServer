@echo off
rem One load cell, live plot + CSV (tower D by default; e.g. force_logger.bat --tower B). Stop the server first.
cd /d "%~dp0BumpemServer"
set PYTHONUTF8=1
..\venv\Scripts\python scripts\force_logger.py %*
pause
