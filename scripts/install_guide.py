"""Installation guide for the offline Windows bundle (scripts/bundle/, D28-D30), step by step with screen mock-ups.
Run: python scripts/install_guide.py  ->  scripts/bundle/INSTALL_GUIDE.pdf (copied into the bundle by build_bundle.sh).
Needs matplotlib. PREVIEW=<dir> also writes one PNG per page."""
import os
import textwrap
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, Rectangle

OUT = Path(__file__).resolve().parent / "bundle" / "INSTALL_GUIDE.pdf"
A4 = (8.27, 11.69)
DARK, MUTED, OK, WARN, ACCENT = "#1b1f23", "#6a737d", "#1a7f37", "#cf222e", "#0969da"
MONO = "DejaVu Sans Mono"


class Pages:
    def __init__(self, path):
        self.pdf, self.n = PdfPages(path), 0
        self.preview = os.environ.get("PREVIEW")

    def save(self, fig):
        self.n += 1
        fig.text(0.93, 0.025, f"{self.n}", fontsize=9, color=MUTED, ha="right")
        fig.text(0.07, 0.025, "Bump'em lab bundle: installation guide", fontsize=9, color=MUTED)
        self.pdf.savefig(fig)
        if self.preview:
            fig.savefig(Path(self.preview) / f"install_{self.n}.png", dpi=70)
        plt.close(fig)

    def close(self):
        self.pdf.close()


def page(title, steps, top=0.90):
    """Title + numbered/bold ("#") lines; returns the figure and the y where the text ended."""
    fig = plt.figure(figsize=A4)
    fig.text(0.07, 0.955, title, fontsize=18, weight="bold", va="top")
    y = top
    for s in steps:
        head, warn = s.startswith("#"), s.startswith("!")
        s = wrap(s.lstrip("#!"), 80 if head or warn else 100)
        fig.text(0.07, y, s, fontsize=11.5 if head else 10.5, weight="bold" if head or warn else "normal",
                 color=WARN if warn else DARK, va="top")
        y -= 0.0165 * (s.count("\n") + 1) + (0.012 if head else 0.007)
    return fig, y


def wrap(s, width):
    """Wrap each line to width, continuation lines indented like the line (plus 3 after a bullet / number)."""
    out = []
    for ln in s.split("\n"):
        body = ln.lstrip(" ")
        ind = " " * (len(ln) - len(body))
        cont = ind + ("   " if body[:2] in ("• ", "1.", "2.", "3.", "4.", "5.") else "")
        out += textwrap.wrap(ln, width, subsequent_indent=cont) or [""]
    return "\n".join(l.rstrip() for l in out)


def axes(fig, rect, w=10, h=5):
    ax = fig.add_axes(rect); ax.axis("off"); ax.set_xlim(0, w); ax.set_ylim(0, h)
    return ax


def window(ax, x, y, w, h, title, dark=False):
    """A Windows-style window frame; returns the inner top-left corner."""
    ax.add_patch(Rectangle((x, y), w, h, fc="#0c0c0c" if dark else "white", ec="#8c959f", lw=1.2))
    ax.add_patch(Rectangle((x, y + h - 0.42), w, 0.42, fc="#f0f0f0", ec="#8c959f", lw=1.2))
    ax.text(x + 0.15, y + h - 0.21, title, fontsize=8.5, va="center")
    for i, c in enumerate(("—", "□", "✕")):
        ax.text(x + w - 0.95 + i * 0.32, y + h - 0.21, c, fontsize=8, va="center", ha="center")
    return x + 0.15, y + h - 0.6


def console(ax, x, y, w, h, title, lines, size=7.6):
    tx, ty = window(ax, x, y, w, h, title, dark=True)
    for i, ln in enumerate(lines):
        col = "#cccccc"
        if ln.startswith("+"):
            ln, col = ln[1:], "#3fb950"
        elif ln.startswith("?"):
            ln, col = ln[1:], "#f2cc60"
        ax.text(tx, ty - i * 0.27, ln, fontsize=size, family=MONO, color=col, va="top")


def callout(ax, x, y, text, tx, ty, color=WARN):
    ax.annotate(text, xy=(x, y), xytext=(tx, ty), fontsize=9, color=color, weight="bold",
                arrowprops=dict(arrowstyle="->", color=color, lw=1.6), va="center")


def box(ax, x, y, w, h, text, fc="#f6f8fa", ec="#d0d7de", size=9.5, weight="normal", color=DARK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.06", fc=fc, ec=ec, lw=1.2))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=size, weight=weight, color=color)


def arrow(ax, x0, y0, x1, y1):
    ax.annotate("", xy=(x1, y1), xytext=(x0, y0), arrowprops=dict(arrowstyle="-|>", color=MUTED, lw=1.5))


# ---------------------------------------------------------------- pages
def p_overview(P):
    fig, y = page("Installing Bump'em on a lab PC", [
        "#What this does",
        "Puts the Bump'em server, the test page and the force logger on a Windows 10/11 PC that has NO internet (e.g. the Vicon PC). Everything installs for your Windows user only: no admin rights, nothing in C:\\Program Files, no system settings changed. It can be removed completely in 2 minutes (last page).",
        "#What you need",
        "•  the bundle folder BumpemLab_<date> (or its .zip) on a USB stick",
        "•  optional, for the Vicon steps: the Vicon DataStream SDK installer (vicon.com, needs an account)",
        "•  about 20 minutes, the Teensy USB cable for step 5",
        "#Before you start",
        "!•  Ask the PC's administrator first: is there app lockdown or a write filter? (installs may be blocked or vanish at reboot). Do not change ESET or any security setting yourself.",
        "•  Do it when nobody is recording on that PC.",
    ])
    ax = axes(fig, (0.07, 0.10, 0.86, y - 0.14), 10, 6); ax.set_xlim(-0.2, 10.2)
    steps = [("1  Copy + unzip", "into your user folder"), ("2  Install", "a) python.org  OR\nb) Miniconda"),
             ("3  Check", '"All packages OK"'), ("4  Simulator", "test page, no hardware"),
             ("5  Real board", "Teensy on USB"), ("6  Extras", "force logger, Vicon")]
    for i, (h, t) in enumerate(steps):
        cx, cy = (i % 3) * 3.4, 3.3 if i < 3 else 0.4
        box(ax, cx, cy, 2.9, 2.0, "", fc="#ddf4ff" if i < 4 else "#f6f8fa", ec=ACCENT if i < 4 else "#d0d7de")
        ax.text(cx + 1.45, cy + 1.45, h, ha="center", fontsize=11, weight="bold")
        ax.text(cx + 1.45, cy + 0.65, t, ha="center", va="center", fontsize=9.5, color=MUTED)
        if i % 3 < 2:
            arrow(ax, cx + 2.95, cy + 1.0, cx + 3.35, cy + 1.0)
    P.save(fig)


def p_copy(P):
    fig, y = page("Step 1: copy the folder to the PC", [
        "1.  Plug in the USB stick. Open File Explorer.",
        "2.  If you have the .zip: right-click it > Extract All... > choose  C:\\Users\\<you>  > Extract.",
        "    If you have the folder: copy it to  C:\\Users\\<you>  (Ctrl+C, Ctrl+V).",
        "3.  Rename the folder to  BumpemLab  (optional, shorter).",
        "4.  If you have the Vicon SDK installer: copy it into the  vicon  folder inside.",
        "!Install it where it will stay. After step 2 the folder must not be moved or renamed.",
        "!Do not run anything from inside the .zip or from the USB stick.",
    ])
    ax = axes(fig, (0.07, 0.08, 0.86, y - 0.11), 10, 7.5)
    tx, ty = window(ax, 0, 0, 10, 7.3, "File Explorer  —  C:\\Users\\<you>\\BumpemLab")
    files = [("BumpemServer", "folder"), ("BumpemUI", "folder"), ("installers", "folder: Python + Miniconda"),
             ("vicon", "folder: put the Vicon SDK installer here"), ("wheels", "folder: the Python packages"),
             ("1_install.bat", "install option a"), ("1_install_conda.bat", "install option b"),
             ("start_simulator.bat", "step 4"), ("start_server.bat", "step 5"), ("force_logger.bat", "extras"),
             ("vicon_probe.bat", "extras"), ("install_vicon_python.bat", "extras"), ("INSTALL_GUIDE.pdf", "this guide"),
             ("README.txt", "short version")]
    for i, (n, d) in enumerate(files):
        yy = ty - 0.12 - i * 0.46
        folder = "." not in n
        ax.add_patch(Rectangle((tx + 0.1, yy - 0.15), 0.32, 0.26, fc="#e3b341" if folder else "#d0d7de", ec="none"))
        ax.text(tx + 0.6, yy, n, fontsize=9.5, va="center", weight="bold" if n.endswith(".bat") and "1_" in n else "normal")
        ax.text(5.6, yy, d, fontsize=8.5, va="center", color=MUTED)
    P.save(fig)


def p_choose(P):
    fig, y = page("Step 2: install, choose ONE of the two", [
        "Both install Python 3.12 and the same packages, offline, for your user only. Pick one and only one.",
        "#a)  1_install.bat  (recommended if you don't need conda)",
        "    Python from python.org + a small environment inside the BumpemLab folder. Smaller, fewer steps.",
        "#b)  1_install_conda.bat  (if you want conda, like on the lab Mac)",
        "    Anaconda's Miniconda + a conda environment called BumpemHome. You must accept Anaconda's Terms of Service (it asks). Free for organisations under 200 employees: IBMS has 6.",
        "#How to run a .bat file",
        "Double-click it in File Explorer. A black window opens and shows what happens. Read the last lines.",
        "#If Windows shows a blue box \"Windows protected your PC\"",
        "Click  More info  >  Run anyway  (these are your own files from the bundle).",
        "!If there is no \"Run anyway\", or ESET blocks it: stop and ask the administrator. Do not change settings.",
    ])
    ax = axes(fig, (0.12, 0.07, 0.76, y - 0.10), 10, 6)
    ax.add_patch(Rectangle((0, 0), 10, 6, fc="#0067b8"))
    ax.text(0.5, 5.2, "Windows protected your PC", fontsize=15, color="white", weight="bold")
    ax.text(0.5, 4.3, "Microsoft Defender SmartScreen prevented an unrecognized app\nfrom starting...", fontsize=9.5,
            color="white", va="top")
    ax.text(0.5, 3.0, "More info", fontsize=10, color="white", weight="bold", style="italic")
    ax.add_patch(Rectangle((5.6, 0.4), 2.0, 0.7, fc="none", ec="white", lw=1.5))
    ax.text(6.6, 0.75, "Run anyway", fontsize=9.5, color="white", ha="center", va="center")
    ax.add_patch(Rectangle((7.8, 0.4), 1.8, 0.7, fc="none", ec="white", lw=1.5))
    ax.text(8.7, 0.75, "Don't run", fontsize=9.5, color="white", ha="center", va="center")
    callout(ax, 2.0, 3.0, "1. click", 3.2, 3.0, "#ffd33d")
    callout(ax, 6.6, 1.15, "2. then this button appears", 4.0, 2.0, "#ffd33d")
    P.save(fig)


def p_install_a(P):
    fig, y = page("Step 2a: 1_install.bat", [
        "1.  Double-click  1_install.bat. Wait: Python installs silently (about 1 minute, nothing to click).",
        "2.  Then the packages install from the wheels folder (about 30 s).",
        "#Done when the last lines are:",
        "    All packages OK",
        "    Done. Next: start_simulator.bat ...",
        "3.  Press any key to close the window. Go to step 4.",
        "#If it stops with a message instead",
        "•  \"Python did not install\": run  installers\\python-3.12.10-amd64.exe  by hand: tick \"Install for this user only\" if offered, untick \"Add python.exe to PATH\", Install. Then run 1_install.bat again.",
        "•  \"package install failed\": photograph the window (all red lines) and send it to Claude.",
        "•  Running it twice is safe: it skips what is already installed.",
    ])
    ax = axes(fig, (0.07, 0.07, 0.86, y - 0.10), 10, 6.2)
    console(ax, 0, 0, 10, 6.2, "C:\\Windows\\System32\\cmd.exe", [
        "Installing Python 3.12 for this user, takes about a minute...",
        "Looking in links: wheels",
        "Processing .\\wheels\\pyserial-3.5-py2.py3-none-any.whl",
        "Processing .\\wheels\\fastapi-0.142.2-py3-none-any.whl",
        "   ...",
        "Installing collected packages: ... pyserial, fastapi, uvicorn, websockets",
        "+Successfully installed annotated-types-0.8.0 anyio-4.15.1 ... websockets-17.2",
        "+All packages OK",
        "",
        "Done. Next: start_simulator.bat (no hardware) or start_server.bat (Teensy plugged in).",
        "Press any key to continue . . .",
    ])
    ax.text(2.0, 5.6 - 7 * 0.27, "◀  this line = success", fontsize=9.5, color=OK, weight="bold", va="top")
    P.save(fig)


def p_install_b(P):
    fig, y = page("Step 2b: 1_install_conda.bat", [
        "1.  Double-click  1_install_conda.bat.",
        "2.  It shows the link to Anaconda's Terms of Service and asks:  Do you accept ... [Y,N]?",
        "    Press  Y  to accept and continue,  N  to stop (then use 1_install.bat instead).",
        "3.  Miniconda installs silently (a few minutes, nothing to click), then the conda environment BumpemHome is created and the packages are installed into it.",
        "#Done when the last lines are:   All packages OK   and   Done. conda env: ...",
        "#Use the environment by hand (optional)",
        "Start menu > Anaconda Prompt >  conda activate BumpemHome   (the .bat files find it by themselves).",
        "#If it stops with a message",
        "•  \"Miniconda did not install\": run the Miniconda installer in  installers  by hand: Just Me, untick \"Add to PATH\" and \"Register as default Python\". Then run 1_install_conda.bat again.",
        "•  \"Could not create the conda env\" or \"not Python 3.12\": photograph the window, send it to Claude, and use 1_install.bat meanwhile.",
    ])
    ax = axes(fig, (0.07, 0.07, 0.86, y - 0.10), 10, 6.2)
    console(ax, 0, 0, 10, 6.2, "C:\\Windows\\System32\\cmd.exe", [
        "Miniconda is Anaconda software. Installing it means accepting Anaconda's Terms of Service:",
        "  https://www.anaconda.com/legal/terms/terms-of-service",
        "Free for organisations with fewer than 200 employees, IBMS confirmed 2026-11-02.",
        "?Do you accept Anaconda's Terms of Service [Y,N]?Y",
        "Installing Miniconda for this user, takes a few minutes...",
        "Creating the conda env BumpemHome offline...",
        "Python 3.12.x",
        "+Successfully installed ... websockets-17.2",
        "+All packages OK",
        "Done. conda env: C:\\Users\\<you>\\miniconda3\\envs\\BumpemHome. Next: ...",
        "Press any key to continue . . .",
    ])
    ax.text(5.1, 5.6 - 3 * 0.27, "◀  press Y", fontsize=9.5, color="#9a6700", weight="bold", va="top")
    P.save(fig)


def p_sim(P):
    fig, y = page("Step 4: test with the simulator (no hardware)", [
        "1.  Double-click  start_simulator.bat. A black window opens and stays open: that IS the server.",
        "2.  After about 4 s the browser opens  http://127.0.0.1:8000/ui/  by itself (if not, type that address).",
        "3.  Top shows  sim  and  DISARMED. Try it:",
        "    Arm  >  Record (green, top right)  >  set Angle and Amplitude  >  Perturb now  >  watch the graphs  >  Stop rec (blue).",
        "    The force CSV downloads to your Downloads folder. The simulator also fakes the two treadmill plates.",
        "4.  To stop: close the black window.",
        "#Nothing here talks to the Teensy or the motors. Saved settings and logs go to the  sim  folder.",
        "!If the black window closes at once or shows red text: photograph it and send it to Claude.",
    ])
    ax = axes(fig, (0.07, 0.06, 0.86, y - 0.09), 10, 7.4)
    tx, ty = window(ax, 0, 0, 10, 7.4, "Bump'em Test  —  127.0.0.1:8000/ui/")
    ax.text(tx, ty - 0.1, "Bump'em test", fontsize=11, weight="bold", va="top")
    ax.text(3.0, ty - 0.12, "simulator ▾   sim · DISARMED", fontsize=8, va="top", family=MONO)
    for i, (lab, c) in enumerate((("Arm", "#f6f8fa"), ("Record", "#dafbe1"), ("Release…", "#fff8c5"), ("STOP Esc", "#ffebe9"))):
        box(ax, 6.05 + i * 0.98, ty - 0.45, 0.85, 0.36, lab, fc=c, size=7.5)
    box(ax, 0.2, 3.55, 4.6, 2.0, "DIRECTION\n(dial, angle)", size=8.5)
    box(ax, 0.2, 1.25, 4.6, 2.05, "PERTURBATION\n(amplitude, timing)\n[Perturb now]", size=8.5)
    box(ax, 0.2, 0.15, 9.6, 0.85, "BOARD SETTINGS (baseline, max force, kff, zero, save)  — at the bottom", size=8.5)
    for k, (y0, lab, col) in enumerate(((3.55, "ROPE FORCE (tower sensors)", "#4fd1a5"), (1.25, "GROUND FORCE (GRAIL plates, Vicon)", "#5ec8f2"))):
        box(ax, 5.1, y0, 4.7, 2.0 if k == 0 else 2.05, "", fc="#0d1117", ec="#30363d")
        xs = [5.3 + i * 0.043 for i in range(100)]
        ys = [y0 + 0.45 + ((1.0 if 62 < i < 72 else 0) if k == 0 else 1.1 * max(0, __import__("math").sin(i / 4.5))) for i in range(100)]
        ax.plot(xs, ys, color=col, lw=1.3)
        ax.text(5.25, y0 + 1.85, lab, color="#8b9690", fontsize=7.5, va="top")
    callout(ax, 9.3, ty - 0.5, "STOP / Esc: always top right", 4.0, ty - 0.85)
    P.save(fig)


def p_board(P):
    fig, y = page("Step 5: with the real board", [
        "1.  Close the simulator window if it is open (only one server at a time).",
        "2.  Plug the Teensy into the PC's USB. Windows needs no driver for it.",
        "3.  Find its COM port: right-click Start > Device Manager > Ports (COM & LPT): a  USB Serial Device (COMx). Unplug and replug the Teensy: the line that disappears and comes back is the Teensy.",
        "4.  Double-click  start_server.bat. The page opens. Choose that COM port in the list, press  Connect. The lab's saved settings (calibration, gains, max force) are written to the board at every connect.",
        "5.  Same page as on the Mac. Recordings: Downloads + BumpemServer\\Logs.",
        "#Safety (same rules as on the Mac)",
        "!•  STOP button or Esc = drivers off at once, ropes go slack. Stop the treadmill first unless it is an emergency.",
        "!•  Arm only with the 48 V supplies on and nobody in the ropes until you are ready.",
        "•  If the USB link drops: replug the Teensy, then Disconnect + Connect in the page.",
    ])
    ax = axes(fig, (0.12, 0.07, 0.76, y - 0.10), 10, 6.5)
    tx, ty = window(ax, 0, 0, 10, 6.5, "Device Manager")
    rows = [("▸ Batteries", 0), ("▸ Computer", 0), ("▸ Keyboards", 0), ("▾ Ports (COM & LPT)", 0),
            ("USB Serial Device (COM4)", 1), ("▸ Processors", 0), ("▸ Universal Serial Bus controllers", 0)]
    for i, (t, ind) in enumerate(rows):
        ax.text(tx + 0.2 + ind * 0.6, ty - 0.2 - i * 0.6, t, fontsize=10, va="top", weight="bold" if ind else "normal")
    callout(ax, 6.0, ty - 2.65, "the Teensy (number varies)", 6.4, ty - 4.0, ACCENT)
    P.save(fig)


def p_extras(P):
    fig, y = page("Step 6: extras", [
        "#Force logger (one load cell, live plot, CSV)",
        "1.  Close the server window (the logger needs the Teensy for itself).",
        "2.  Double-click  force_logger.bat  (tower D). Other tower: open a command prompt in the folder and type:",
        "    force_logger.bat --tower B",
        "3.  First time, and after moving the sensor to another amplifier: press  Calibrate  and follow the two steps with the 12 kg weight. With the weight on it must read about 118 N / 12.00 kg.",
        "4.  Start > Stop > Save CSV. Threshold line: type a force in the box under the graph.",
        "#Vicon (Nexus must be open in Live mode)",
        "1.  Nothing to install: the Vicon SDK comes with this bundle (1_install / update.bat print  Vicon SDK OK).",
        "2.  vicon_probe.bat  (on the Nexus PC itself). From another PC: open a command prompt in BumpemLab and type",
        "    vicon_probe.bat 192.168.1.60:801",
        "3.  Stand on one belt during the 10 s: note which plate is the LEFT belt (standing reads negative, about minus your weight in N). Send the output to Claude.",
        "4.  In the page: Ground force card > address (127.0.0.1:801 on the Nexus PC) > Connect. Record (next to Arm) records it with the rope forces.",
    ])
    P.save(fig)


def p_update(P):
    fig, y = page("Updating to a new version", [
        "When the software changes on the Mac, Claude builds a small update package: BumpemUpdate_<date>.zip (code and packages, no installers). Your settings, calibration and recordings stay.",
        "1.  Close the Bump'em server window and the force logger.",
        "2.  Copy the zip to the PC, right-click it > Extract All. Open the unzipped folder.",
        "3.  Double-click  update.bat  in THAT folder (not the one in BumpemLab).",
        "4.  It shows the installed and the new version and asks  Update now [Y,N]?  Press  Y.",
        "#Done when it prints   All packages OK   and   Updated.",
        "5.  Start as before with  start_server.bat  in BumpemLab. Delete the unzipped update folder.",
        "#What it does",
        "•  finds BumpemLab in your user folder (else asks you to paste its path)",
        "•  moves the old code to  BumpemLab\\backup\\<date_time>,  copies the new code",
        "•  puts back  settings.json,  force_logger_cal.json  and  Logs  (your recordings)",
        "•  installs only the Python packages that changed, then checks them",
        "#Go back to the old version",
        "Delete BumpemServer and BumpemUI in BumpemLab and move the two folders from  backup\\<date_time>  back (recordings made after the update: move them out of the new BumpemServer\\Logs first).",
    ])
    ax = axes(fig, (0.07, 0.06, 0.86, y - 0.09), 10, 5.4)
    console(ax, 0, 0, 10, 5.4, "C:\\Windows\\System32\\cmd.exe", [
        "Installed in C:\\Users\\<you>\\BumpemLab:",
        "built 2026-11-02 11:40   BumpemServer 35fa83b   BumpemUI bd67152",
        "This update:",
        "built 2026-11-03 09:15   BumpemServer ca3ecde   BumpemUI 56b6d31",
        "Kept: BumpemServer\\settings.json, force_logger_cal.json, Logs\\, sim\\, Python.",
        "?Update now [Y,N]?Y",
        "Requirement already satisfied: pyserial==3.5 ...",
        "+All packages OK",
        "",
        "Updated. Old code: C:\\Users\\<you>\\BumpemLab\\backup\\20261103_091702",
        "Press any key to continue . . .",
    ])
    ax.text(3.4, 4.8 - 5 * 0.27, "◀  press Y", fontsize=9.5, color="#9a6700", weight="bold", va="top")
    P.save(fig)


def p_trouble(P):
    fig, y = page("If something goes wrong, and how to remove it", [])
    rows = [
        ("Blue box \"Windows protected your PC\"", "More info > Run anyway. No \"Run anyway\" button: ask the administrator."),
        ("ESET warning / file quarantined", "Do not change ESET. Tell the administrator which file; ask them to allow it."),
        ("Installed, but gone after a reboot", "The PC has a write filter. The administrator must allow or commit the install."),
        ("\"Not installed yet: run 1_install...\"", "Step 2 was not done, or the folder was moved after it. Run step 2 again."),
        ("Page does not open", "Wait 5 s, then type 127.0.0.1:8000/ui/ in the browser. The black window must be open."),
        ("Black window: \"address already in use\"", "Another server is still running: close all black windows, try again."),
        ("\"COMx is busy\" / Access is denied", "Another program has the Teensy: close the logger, other servers, ESCON tools."),
        ("No COM port in the list", "Other USB cable or port (some cables are charge-only). Check Device Manager."),
        ("\"no Teensy found\" (force logger)", "Teensy not plugged in, or the server holds it: close the server."),
        ("Values look wrong (force logger)", "Calibrate again with the 12 kg weight; 24 V of that tower on?"),
        ("update.bat: \"server is running\" / \"in use\"", "Close the server and logger windows and any Explorer window inside BumpemLab, run it again."),
    ]
    yy = y - 0.01
    fig.text(0.07, yy, "What you see", fontsize=11, weight="bold"); fig.text(0.45, yy, "What to do", fontsize=11, weight="bold")
    yy -= 0.025
    for a, b in rows:
        a, b = wrap(a, 38), wrap(b, 55)
        n = max(a.count("\n"), b.count("\n")) + 1
        fig.add_artist(plt.Line2D([0.07, 0.93], [yy + 0.008, yy + 0.008], color="#d0d7de", lw=0.6))
        fig.text(0.07, yy, a, fontsize=9.3, va="top")
        fig.text(0.45, yy, b, fontsize=9.3, va="top", color=DARK)
        yy -= 0.0175 * n + 0.014
    yy -= 0.03
    for i, s in enumerate([
        "#Asking for help",
        "Photograph the whole black window (or copy its text: right-click the title bar > Edit > Select All, Enter) and send it to Claude together with which step you were on.",
        "#Remove everything (2 minutes, puts the PC back as it was)",
        "1.  Settings > Apps > \"Python 3.12.10\" > Uninstall   (if you used 1_install.bat)",
        "    Settings > Apps > \"Miniconda3\" > Uninstall   (if you used 1_install_conda.bat; also removes BumpemHome)",
        "2.  Delete the BumpemLab folder.",
    ]):
        head = s.startswith("#")
        s = wrap(s.lstrip("#"), 100)
        fig.text(0.07, yy, s, fontsize=11.5 if head else 10.5, weight="bold" if head else "normal", va="top")
        yy -= (0.022 if head else 0.0165) * (s.count("\n") + 1) + 0.008
    P.save(fig)


def main():
    P = Pages(OUT)
    for f in (p_overview, p_copy, p_choose, p_install_a, p_install_b, p_sim, p_board, p_extras, p_update, p_trouble):
        f(P)
    P.close()
    print(f"{OUT} ({P.n} pages)")


if __name__ == "__main__":
    main()
