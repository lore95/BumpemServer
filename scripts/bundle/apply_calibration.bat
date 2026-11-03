@echo off
rem Sensor gains from the newest calibration_*.csv (calibrate page) in this folder or Downloads into the saved settings
rem (BumpemServer\settings.json; old one kept as settings.json.bak). Report: calibration_<stamp>_applied.txt next to the CSV.
rem Then: start_server.bat, Connect, Zero sensors with the ropes slack, Save as default.
cd /d "%~dp0BumpemServer"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniconda3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
set PYTHONUTF8=1
"%PYEXE%" scripts\apply_calibration.py %*
pause
