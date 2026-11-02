Bump'em lab bundle (offline install for Windows 10 x64)
=======================================================
Built: @BUILT@   BumpemServer @SERVER@   BumpemUI @UI@

1. Copy this whole folder to the PC, e.g. C:\Users\<you>\BumpemLab
   (install it where it will stay: the venv cannot be moved afterwards).
2. Install ONE of the two (both: for this user only, no admin, no internet; both end with "All packages OK"):
   a) 1_install.bat        Python 3.12 from python.org + venv\ in this folder (smaller, simpler)
   b) 1_install_conda.bat  Miniconda (Anaconda) + conda env "BumpemHome", Python 3.12, like the Mac.
                           Asks you to accept Anaconda's Terms of Service first (free under 200 employees: IBMS has 6).
                           By hand: Start menu > Anaconda Prompt > conda activate BumpemHome
   The .bat launchers below use venv\ if it exists, else the conda env.
   If the install is blocked or gone after a reboot: the PC has app lockdown / a write filter: ask the administrator.
3. Double-click start_simulator.bat: the browser opens http://127.0.0.1:8000/ui/ with a simulated board.
   Close the black window to stop the server.
4. With the Teensy on USB: start_server.bat, then in the page pick the COM port and press Connect.
   Windows 10 needs no Teensy driver. COM port: Device Manager > Ports (COM & LPT).
   The lab's saved settings (BumpemServer\settings.json, from the Mac) are written to the board at every connect.
   Recordings: BumpemServer\Logs\ (and downloaded by the browser at Stop recording).

Other tools
- force_logger.bat            one load cell, live plot + CSV (tower D; force_logger.bat --tower B). Server must be stopped.
- vicon_probe.bat             Vicon DataStream check (Nexus in Live mode). On the Nexus PC: no argument.
                              From another PC: vicon_probe.bat 192.168.1.60:801
- install_vicon_python.bat    after installing the Vicon DataStream SDK (vicon.com, needs an account; put its
                              installer in vicon\ before copying): install_vicon_python.bat "<SDK's Python folder>"

Never on this PC: flashing the Teensy (needs PlatformIO + internet: do it from the Mac).

Update (new version from the Mac, keeps this PC's settings)
- Copy BumpemUpdate_<date>.zip to this PC, right-click > Extract All, open the unzipped folder, double-click update.bat.
  It finds the installation (C:\Users\<you>\BumpemLab, else asks), shows installed vs new version (VERSION.txt),
  moves the old code to backup\<date_time>\, copies the new code, puts back BumpemServer\settings.json,
  force_logger_cal.json and Logs\, installs changed packages and checks them. Close the server first.
- Rollback: delete BumpemServer and BumpemUI in the installed folder, move the two from backup\<date_time>\ back.
  Recordings made after the update are in the new BumpemServer\Logs: move them out first.
- A full reinstall is only needed when Python itself changes (README of that bundle says so).

Remove everything
- a) Settings > Apps > "Python 3.12.10" > Uninstall.   b) Settings > Apps > "Miniconda3" > Uninstall (removes the env too).
- Delete this folder.
