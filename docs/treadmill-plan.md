# Treadmill control from Bump'em (plan, not started)

Handoff for when we decide to do it (discussed 2026-11-24). Goal: set the speed of each belt and start / stop the
treadmill from the Bump'em pages, without using the D-Flow app's own controls during a study. No Motek support any
more: the user builds the D-Flow side, Claude the Bump'em side.

## Idea

D-Flow stays (it drives the treadmill), like Vicon Nexus stays for the plates. A small D-Flow application, made once,
stays open and takes the belt speeds from the Bump'em server over the network.

```
Bump'em page ──► Bump'em server ──UDP──► D-Flow app (open all session)
 [L m/s][R m/s]                            Script module (Lua): newest message each frame
 [Start] [Stop]                              → Treadmill module LeftBelt.Speed / RightBelt.Speed
           ◄──────── measured belt speeds (UDP) ◄── Treadmill module outputs
```

## What is known (sources at the end)

- D-Flow's **Script module** runs a Lua script every frame; `outputs.set(n, value)` / `inputs.get(n)` are its outputs
  and inputs, wired to other modules in the connection editor (Motek scripting tutorial).
- Belt speed is an **input of the Treadmill module** (`LeftBelt.Speed`, `RightBelt.Speed`); Motek's gait tutorial
  wires a Runtime Console slider into it. A script output can be wired there the same way.
- **LuaSocket** (sockets for Lua) was loaded in the Script module by a student project to exchange live data with
  another program. Their TCP link dropped because the script reruns every frame → use **UDP, non-blocking**
  (`settimeout(0)`, read every waiting message, keep the newest).

## Not known yet (step 1 answers it)

- Does this D-Flow have a network / UDP input module of its own (then no LuaSocket needed)?
- Is LuaSocket already in the D-Flow install (`socket\` folder, `core.dll`), and can `require("socket")` load it?
- D-Flow version; how the script gets the frame time (for the ramp); the Treadmill module's acceleration input/limit.

## Steps

### 1 · Look on the D-Flow PC (user, changes nothing)
Photos of: D-Flow version (Help → About); the module list (every category); the Treadmill module's inputs and
outputs; the D-Flow install folder (search for `socket`, `lua`, `core.dll`). Send them to Claude → choose the route
(own network module, or Script + LuaSocket). If neither exists: stop here (adding a library to the lab PC needs the
OK of whoever is responsible for that PC).

### 2 · Bump'em side (Claude, Mac, no lab)
Order as always: `docs/API.md` → server → UI.
- API (draft): `GET /api/v1/treadmill` (connected, set and measured speeds, running), `POST /api/v1/treadmill/connect`
  `{host}`, `POST /api/v1/treadmill/speed` `{left_ms, right_ms}`, `POST /api/v1/treadmill/start`,
  `POST /api/v1/treadmill/stop`; stream items `{"type":"treadmill",...}` for the measured speeds.
- UDP message (draft), server → D-Flow, 10 Hz while connected: `BUMPEM1 <seq> <left_ms> <right_ms> <run 0|1>`;
  D-Flow → server: `BUMPEM1 <seq> <left_measured> <right_measured>`. Plain text: easy to read in Lua and in a log.
- Limits in the server: max speed (setting, e.g. 3.5 m/s), speed steps only within it; Start needs the study's speed.
- Interlocks: **Release refused while the belts move** (measured > 0.05 m/s), the rule "treadmill stopped before
  rope tension is released" enforced instead of asked; the study's `speed_ms` sent at Start (confirm on the page);
  treadmill link lost → warning on every page.
- A fake D-Flow (`--treadmill sim`, same UDP messages, belts ramp at the set acceleration) for tests and the UI.

### 3 · D-Flow application (user, with Claude's script)
New application file (do not change the lab's existing ones): Script module → Treadmill module
(output 1 → `LeftBelt.Speed`, output 2 → `RightBelt.Speed`; Treadmill measured speeds → script inputs 1, 2).
Script, to finish once step 1 is known (draft, untested):

```lua
-- Bump'em → treadmill. Runs every frame. Stops the belts when Bump'em goes quiet.
local MAX_MS, ACC, TIMEOUT_S = 3.5, 0.5, 1.0          -- m/s, m/s², s (set to the lab's values)
if not bumpem then
  local socket = require("socket")
  local u = socket.udp(); u:setsockname("*", 50555); u:settimeout(0)
  bumpem = {u = u, socket = socket, last = 0, l = 0, r = 0, run = 0, outl = 0, outr = 0, t = socket.gettime(), peer = nil}
end
local b, now = bumpem, bumpem.socket.gettime()
while true do                                          -- every waiting message, keep the newest
  local msg, ip, port = b.u:receivefrom()
  if not msg then break end
  local seq, l, r, run = msg:match("^BUMPEM1 (%d+) ([%d.]+) ([%d.]+) ([01])$")
  if seq then b.l, b.r, b.run, b.last, b.peer = tonumber(l), tonumber(r), tonumber(run), now, {ip, port} end
end
local want_l, want_r = 0, 0
if b.run == 1 and now - b.last < TIMEOUT_S then want_l, want_r = math.min(b.l, MAX_MS), math.min(b.r, MAX_MS) end
local step = ACC * (now - b.t); b.t = now              -- ramp, whatever the Treadmill module does itself
local function toward(x, w) if x < w then return math.min(x + step, w) end return math.max(x - step, w) end
b.outl, b.outr = toward(b.outl, want_l), toward(b.outr, want_r)
outputs.set(1, b.outl); outputs.set(2, b.outr)
if b.peer then b.u:sendto(string.format("BUMPEM1 0 %.3f %.3f", inputs.get(1), inputs.get(2)), b.peer[1], b.peer[2]) end
```

### 4 · First tests (lab, nobody on the treadmill, someone at the GRAIL e-stop)
0.5 m/s both belts → Start → Stop; different speeds left / right; unplug the network cable while running → belts must
ramp to a stop within ~TIMEOUT_S + ramp; Bump'em server closed → same; GRAIL e-stop still stops everything. Then
1.2 m/s, then a walking participant, then running speeds. Record each test (date, speeds, what happened) in STATUS.

## Safety (does not change)
- The GRAIL e-stop and D-Flow's own limits stay as they are; this only replaces the hand on the speed slider.
- Bump'em STOP stays what it is (drops rope tension); it does not stop the belts. The treadmill Stop button does.
- No Motek support: the user checks it alone → first tests empty, slow, with someone at the e-stop.

## Sources
- Lua scripting in D-Flow (Motek): https://knowledge.motekmedical.com/wp-content/uploads/2019/08/D-Flow-Scripting-Tutorials.pdf
- D-Flow Gait tutorials (Motek): https://knowledge.motekmedical.com/wp-content/uploads/2019/05/D-Flow-Gait-tutorials-1-4-1.pdf
- Muscle activity: from D-Flow to RAGE (student project, LuaSocket in D-Flow): https://perso.liris.cnrs.fr/nicolas.pronost/Papers/StudentProject/Small/Muscle%20activity%20-%20From%20D-Flow%20to%20RAGE.pdf
