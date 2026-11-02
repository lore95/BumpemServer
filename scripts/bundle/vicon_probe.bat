@echo off
rem Read-only Vicon DataStream check. Nexus must be in Live mode. On the Nexus PC itself: 127.0.0.1:801 (default here).
rem From another PC: vicon_probe.bat 192.168.1.60:801
cd /d "%~dp0BumpemServer"
set PYTHONUTF8=1
set HOST=%1
if "%HOST%"=="" set HOST=127.0.0.1:801
..\venv\Scripts\python scripts\vicon_probe.py --host %HOST% --seconds 10
pause
