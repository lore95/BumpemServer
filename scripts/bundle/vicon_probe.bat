@echo off
rem Read-only Vicon DataStream check. Nexus must be in Live mode. On the Nexus PC itself: 127.0.0.1:801 (default here).
rem From another PC: vicon_probe.bat 192.168.1.60:801
cd /d "%~dp0BumpemServer"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniforge3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
set PYTHONUTF8=1
set HOST=%1
if "%HOST%"=="" set HOST=127.0.0.1:801
"%PYEXE%" scripts\vicon_probe.py --host %HOST% --seconds 10
pause
