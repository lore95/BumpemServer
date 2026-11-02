@echo off
rem Bump'em update. Run it from the NEW folder (BumpemUpdate_<date> or BumpemLab_<date>), not from the installed one.
rem Replaces the code of the installed folder; keeps settings.json, force_logger_cal.json, Logs\, sim\ and Python.
rem The old code goes to backup\<date_time>\ in the installed folder (rollback: README.txt).
setlocal
set SRC=%~dp0
set SRC=%SRC:~0,-1%
set DEST=%USERPROFILE%\BumpemLab
if not exist "%DEST%\BumpemServer\bumpem\" if exist "C:\Users\operator\BumpemLab\BumpemServer\bumpem\" set DEST=C:\Users\operator\BumpemLab
if not exist "%SRC%\BumpemServer\bumpem\" (echo This folder has no Bump'em code to install from. & pause & exit /b 1)
if exist "%SRC%\venv\" goto :installed
if not exist "%DEST%\BumpemServer\bumpem\" (
  echo No installation found in %DEST%
  set /p DEST=Type or paste the installed folder ^(where 1_install.bat ran^), then Enter:
)
set DEST=%DEST:"=%
if /i "%SRC%"=="%DEST%" goto :installed
if not exist "%DEST%\BumpemServer\bumpem\" (echo Not a Bump'em installation: %DEST% & pause & exit /b 1)

rem --- check the installation
set PYEXE=%DEST%\venv\Scripts\python.exe
if not exist "%PYEXE%" set PYEXE=%USERPROFILE%\miniconda3\envs\BumpemHome\python.exe
if not exist "%PYEXE%" (echo Python of the installation not found: run 1_install.bat in %DEST% first & pause & exit /b 1)
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul && (echo The Bump'em server is running: close its black window, then run update.bat again. & pause & exit /b 1)
echo Installed in %DEST%:
type "%DEST%\VERSION.txt" 2>nul || echo   unknown version ^(installed before update.bat existed^)
echo This update:
type "%SRC%\VERSION.txt"
echo Kept: BumpemServer\settings.json, force_logger_cal.json, Logs\, sim\, Python.
choice /c YN /m "Update now"
if errorlevel 2 exit /b 0

rem --- old code to backup\<date_time>
for /f "usebackq delims=" %%t in (`""%PYEXE%" -c "import time; print(time.strftime('%%Y%%m%%d_%%H%%M%%S'))""`) do set STAMP=%%t
if "%STAMP%"=="" (echo could not read the time from Python & pause & exit /b 1)
set OLD=%DEST%\backup\%STAMP%
mkdir "%OLD%" || (echo cannot create %OLD% & pause & exit /b 1)
move "%DEST%\BumpemServer" "%OLD%\BumpemServer" >nul || (echo BumpemServer is in use ^(a window or file open?^): close it and retry. Nothing changed. & pause & exit /b 1)
move "%DEST%\BumpemUI" "%OLD%\BumpemUI" >nul || (move "%OLD%\BumpemServer" "%DEST%\BumpemServer" >nul & echo BumpemUI is in use: close it and retry. Nothing changed. & pause & exit /b 1)

rem --- new code, then the lab's own files back
robocopy "%SRC%\BumpemServer" "%DEST%\BumpemServer" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail
robocopy "%SRC%\BumpemUI" "%DEST%\BumpemUI" /E /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 goto :copyfail
for %%f in (settings.json force_logger_cal.json) do if exist "%OLD%\BumpemServer\%%f" copy /y "%OLD%\BumpemServer\%%f" "%DEST%\BumpemServer\" >nul
if exist "%OLD%\BumpemServer\Logs\" robocopy "%OLD%\BumpemServer\Logs" "%DEST%\BumpemServer\Logs" /E /MOVE /NFL /NDL /NJH /NJS /NP >nul
if errorlevel 8 (echo Logs could not be moved back: they are in %OLD%\BumpemServer\Logs & pause)

rem --- launchers, readme, guide, packages
for %%f in ("%SRC%\*.bat" "%SRC%\*.txt" "%SRC%\*.pdf") do copy /y "%%~f" "%DEST%\" >nul
robocopy "%SRC%\wheels" "%DEST%\wheels" /E /NFL /NDL /NJH /NJS /NP >nul
"%PYEXE%" -m pip install --disable-pip-version-check --no-index --find-links "%SRC%\wheels" -r "%SRC%\requirements.txt" || (echo package install failed: rollback in README.txt & pause & exit /b 1)
cd /d "%DEST%\BumpemServer"
"%PYEXE%" -c "import bumpem.server, serial, fastapi, uvicorn, websockets, tkinter; print('All packages OK')" || (echo check failed: rollback in README.txt & pause & exit /b 1)
echo.
echo Updated. Old code: %OLD%   ^(delete it once the new version works^)
echo Start as before: start_server.bat in %DEST%
pause
exit /b 0

:copyfail
echo Copying the new code failed. Putting the old code back...
if exist "%DEST%\BumpemServer" rmdir /s /q "%DEST%\BumpemServer"
if exist "%DEST%\BumpemUI" rmdir /s /q "%DEST%\BumpemUI"
move "%OLD%\BumpemServer" "%DEST%\BumpemServer" >nul
move "%OLD%\BumpemUI" "%DEST%\BumpemUI" >nul
echo Old version restored. Nothing changed.
pause
exit /b 1

:installed
echo This is the installed folder. To update: copy the new BumpemUpdate_^<date^>.zip to this PC, unzip it
echo ^(right-click ^> Extract All^), open the unzipped folder and double-click update.bat there.
pause
exit /b 1
