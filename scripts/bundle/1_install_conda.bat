@echo off
rem Alternative to 1_install.bat: Miniconda (Anaconda) for this user, a conda env "BumpemHome" (Python 3.12, like the Mac),
rem then the packages from wheels\. No admin, no internet. Use ONE of the two installs.
setlocal
cd /d "%~dp0"
set MC=%USERPROFILE%\miniconda3
set CONDA=%MC%\Scripts\conda.exe
set ENVPY=%MC%\envs\BumpemHome\python.exe
set MCX=installers\Miniconda3-py312_26.9.4-0-Windows-x86_64.exe
if not exist "%CONDA%" (
  echo Miniconda is Anaconda software. Installing it means accepting Anaconda's Terms of Service:
  echo   https://www.anaconda.com/legal/terms/terms-of-service
  echo Free for organisations with fewer than 200 employees, IBMS confirmed 2026-11-02.
  choice /c YN /m "Do you accept Anaconda's Terms of Service"
  if errorlevel 2 (echo Not installed. Use 1_install.bat instead: no Anaconda terms. & pause & exit /b 1)
  echo Installing Miniconda for this user, takes a few minutes...
  start /wait "" %MCX% /S /InstallationType=JustMe /AddToPath=0 /RegisterPython=0 /D=%MC%
)
if not exist "%CONDA%" (
  echo.
  echo Miniconda did not install. Run %MCX% by hand: "Just Me", no PATH, no "register as default Python".
  echo If that is blocked too, the PC has app lockdown: ask the administrator.
  pause & exit /b 1
)
rem the terms were accepted above; this lets conda use its channels' cached packages without asking again
set CONDA_PLUGINS_AUTO_ACCEPT_TOS=yes
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
echo Done. conda env: %MC%\envs\BumpemHome. Next: start_simulator.bat (no hardware) or start_server.bat (Teensy plugged in).
echo To use it by hand: Start menu, "Anaconda Prompt", then  conda activate BumpemHome
pause
