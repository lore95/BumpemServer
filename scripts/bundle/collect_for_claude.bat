@echo off
rem Everything Claude needs after a session in one zip: error logs, delay reports, the newest 3 recordings, version,
rem settings, the server's state. Output: ForClaude_<date_time>.zip in this folder: copy it to the USB stick (D51).
cd /d "%~dp0BumpemServer"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniconda3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
set PYTHONUTF8=1
"%PYEXE%" scripts\collect_for_claude.py %*
start "" "%~dp0"
pause
