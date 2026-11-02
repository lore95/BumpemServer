@echo off
rem Bump'em server with the real board (production mode, all four towers). Pick the Teensy's COM port in the page, Connect.
cd /d "%~dp0BumpemServer"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniforge3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
set PYTHONUTF8=1
rem open the page 4 s later, once the server is up
start "" /min cmd /c "timeout /t 4 >nul & start http://127.0.0.1:8000/ui/"
"%PYEXE%" -m bumpem.cli serve --production --modules ABCD
pause
