Bump'em lab bundle (offline install for Windows 10 x64)
=======================================================
Built: @BUILT@   BumpemServer @SERVER@   BumpemUI @UI@

1. Copy this whole folder to the PC, e.g. C:\Users\<you>\BumpemLab
   (install it where it will stay: the venv cannot be moved afterwards).
2. Double-click 1_install.bat. Installs Python 3.12 for this user only (no admin, no internet)
   and the packages into venv\. Ends with "All packages OK".
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
