@echo off
rem Alternative to 1_install.bat: Miniforge (conda, conda-forge packages) for this user, a conda env "BumpemHome"
rem (Python 3.12, like the Mac), then the packages from wheels\. No admin, no internet. Use ONE of the two installs.
setlocal
cd /d "%~dp0"
set MF=%USERPROFILE%\miniforge3
set CONDA=%MF%\Scripts\conda.exe
set ENVPY=%MF%\envs\BumpemHome\python.exe
if not exist "%CONDA%" (
  echo Installing Miniforge for this user, takes a few minutes...
  start /wait "" installers\Miniforge3-25.11.0-1-Windows-x86_64.exe /S /InstallationType=JustMe /AddToPath=0 /RegisterPython=0 /D=%MF%
)
if not exist "%CONDA%" (
  echo.
  echo Miniforge did not install. Run installers\Miniforge3-25.11.0-1-Windows-x86_64.exe by hand: "Just Me", no PATH, no "register as default Python".
  echo If that is blocked too, the PC has app lockdown: ask the administrator.
  pause & exit /b 1
)
if not exist "%ENVPY%" (
  echo Creating the conda env BumpemHome offline...
  "%CONDA%" create -y --offline -n BumpemHome python=3.12
)
if not exist "%ENVPY%" (
  echo That did not work offline: cloning the base env instead...
  "%CONDA%" create -y --offline -n BumpemHome --clone base
)
if not exist "%ENVPY%" (echo Could not create the conda env BumpemHome & pause & exit /b 1)
"%ENVPY%" -c "import sys; assert sys.version_info[:2] == (3, 12), sys.version; print('Python', sys.version.split()[0])" || (echo The env is not Python 3.12: the wheels need 3.12 & pause & exit /b 1)
"%ENVPY%" -m pip install --disable-pip-version-check --no-index --find-links wheels -r requirements.txt || (echo package install failed & pause & exit /b 1)
"%ENVPY%" -c "import serial, fastapi, uvicorn, websockets, tkinter; print('All packages OK')" || (echo check failed & pause & exit /b 1)
echo.
echo Done. conda env: %MF%\envs\BumpemHome. Next: start_simulator.bat (no hardware) or start_server.bat (Teensy plugged in).
echo To use it by hand: open "Miniforge Prompt" from the Start menu, then  conda activate BumpemHome
pause
