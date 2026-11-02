@echo off
rem Vicon connection report, read-only (changes nothing): network, port 801, Vicon SDK connect, Vicon DLL versions on C:,
rem D-Flow's Vicon settings. Writes vicon_check_<date_time>.txt in this folder: copy it to the USB stick for Claude.
rem Other Nexus address: vicon_check.bat 192.168.10.1:801
cd /d "%~dp0BumpemServer"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniconda3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
set PYTHONUTF8=1
set HOST=%1
if "%HOST%"=="" set HOST=192.168.1.60:801
"%PYEXE%" scripts\vicon_check.py --host %HOST% --out "%~dp0."
pause
