@echo off
rem After installing the Vicon DataStream SDK: give this the SDK's Python folder (the one containing vicon_dssdk / setup.py).
rem Example: install_vicon_python.bat "C:\Program Files\Vicon\DataStream SDK\Win64\Python"
cd /d "%~dp0"
if "%~1"=="" (echo Usage: install_vicon_python.bat "path\to\SDK\Python folder" & pause & exit /b 1)
venv\Scripts\python -m pip install --no-index --find-links wheels --no-build-isolation "%~1"
venv\Scripts\python -c "from vicon_dssdk import ViconDataStream; print('vicon_dssdk OK')"
pause
