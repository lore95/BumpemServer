@echo off
rem One load cell, live plot + CSV (tower D by default; e.g. force_logger.bat --tower B). Stop the server first.
cd /d "%~dp0BumpemServer"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniforge3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
set PYTHONUTF8=1
"%PYEXE%" scripts\force_logger.py %*
pause
