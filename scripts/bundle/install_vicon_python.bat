@echo off
rem After installing the Vicon DataStream SDK: give this the SDK's Python folder (the one containing vicon_dssdk / setup.py).
rem Example: install_vicon_python.bat "C:\Program Files\Vicon\DataStream SDK\Win64\Python"
cd /d "%~dp0"
if "%~1"=="" (echo Usage: install_vicon_python.bat "path\to\SDK\Python folder" & pause & exit /b 1)
rem pip builds inside the folder it installs from: copy it out of Program Files (read-only for users) first
set SRC=%TEMP%\vicon_dssdk_src
if exist "%SRC%" rmdir /s /q "%SRC%"
xcopy "%~1" "%SRC%" /e /i /q >nul || (echo could not copy "%~1" & pause & exit /b 1)
venv\Scripts\python -m pip install --disable-pip-version-check --no-index --find-links wheels --no-build-isolation "%SRC%"
venv\Scripts\python -c "from vicon_dssdk import ViconDataStream; print('vicon_dssdk OK')"
pause
