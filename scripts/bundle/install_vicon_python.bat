@echo off
rem Only needed when the bundle had no Vicon SDK wheel (bundles from 2026-11-02 evening on carry it: 1_install / update.bat install it).
rem After installing the Vicon DataStream SDK: give this the SDK's Python folder (containing vicon_dssdk\setup.py).
rem Example: install_vicon_python.bat "C:\Program Files\Vicon\DataStream SDK\Win64\Python"
cd /d "%~dp0"
rem Python: venv\ from 1_install.bat, else the conda env from 1_install_conda.bat
set PYEXE=%~dp0venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniconda3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Not installed yet: run 1_install.bat or 1_install_conda.bat first & pause & exit /b 1)
if "%~1"=="" (echo Usage: install_vicon_python.bat "path\to\SDK\Python folder" & pause & exit /b 1)
rem pip builds inside the folder it installs from: copy it out of Program Files (read-only for users) first
set SRC=%TEMP%\vicon_dssdk_src
if exist "%SRC%" rmdir /s /q "%SRC%"
xcopy "%~1" "%SRC%" /e /i /q >nul || (echo could not copy "%~1" & pause & exit /b 1)
set PKG=%SRC%
if exist "%SRC%\vicon_dssdk\setup.py" set PKG=%SRC%\vicon_dssdk
rem --no-deps: Vicon's setup.py asks for enum34 (Python 2 only; breaks Python 3)
"%PYEXE%" -m pip install --disable-pip-version-check --no-index --no-deps --find-links wheels --no-build-isolation "%PKG%"
"%PYEXE%" -c "from vicon_dssdk import ViconDataStream; print('vicon_dssdk OK')"
pause
