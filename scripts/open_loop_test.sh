#!/bin/sh
# Preliminary open-loop test (docs/tests/open-loop-test-module-C.md).
#   scripts/open_loop_test.sh            module C (right)
#   scripts/open_loop_test.sh A          module A (left)
#   scripts/open_loop_test.sh AC         modules A + C together: same pulse on both, started in the same control cycle
#   PORT=/dev/cu.usbmodemXXXX scripts/open_loop_test.sh C
# Needs: conda activate BumpemHome; Teensy on USB; bumpem serve NOT running (it would hold the port).
# Ctrl+C at any point sends ESTOP (drives off, rope goes slack).
set -eu

MOD="${1:-C}"
P="${PORT:-/dev/cu.usbmodem169222501}"
case "$MOD" in
  A)  OFF="ch_B ch_C ch_D"; ON="ch_A";      NAME="module A" ;;
  C)  OFF="ch_A ch_B ch_D"; ON="ch_C";      NAME="module C" ;;
  AC) OFF="ch_B ch_D";      ON="ch_A ch_C"; NAME="modules A and C" ;;
  *)  echo "usage: $0 [A|C|AC]" >&2; exit 1 ;;
esac

DUR=400   # pulse duration in ms, start to end incl. ramps (was 600; shortened by one third 2026-10-02)

b() { bumpem "$@" --port "$P"; }
if [ -t 1 ]; then RED=$(printf '\033[1;37;41m'); GRN=$(printf '\033[1;30;42m'); RST=$(printf '\033[0m'); else RED=""; GRN=""; RST=""; fi
banner() {   # banner COLOUR "line" ["line" ...]
  col=$1; shift
  printf '\n\n%s%s%s\n' "$col" "                                                                  " "$RST"
  for l in "$@"; do printf '%s   %-63s%s\n' "$col" "$l" "$RST"; done
  printf '%s%s%s\n\n' "$col" "                                                                  " "$RST"
}
pause() { printf '\n>>> %s\n    Press Enter to continue (Ctrl+C = emergency stop) ' "$1"; read -r _; }
amps() { out=""; for c in $(echo "$MOD" | sed 's/./& /g'); do out="$out $c=$1"; done; echo "$out"; }   # "AC" 5 -> " A=5 C=5"
trap 'echo; echo "!!! Ctrl+C: sending ESTOP"; bumpem estop --port "$P" || true; echo "Switch the 48 V OFF."; exit 1' INT

echo "== 1. Board"
b info

echo "== 2. Settings: open-loop, $NAME only"
for k in kp_track kd_track kp_pulse kd_pulse; do b set "$k" 0; done
b set kff 2
b set baseline_n 2
b set fmax_n 30
for k in $OFF; do b set "$k" 0; done
for k in $ON; do b set "$k" 1; done
b get

pause "Check above: kp/kd 0, kff 2, baseline_n 2, fmax_n 30, $ON = 1, others 0."

banner "$RED" "!!!  KEEP THE 48 V POWER SUPPLY OFF  !!!" "" "Dry run next: the Teensy arms and pulses with the motors unpowered." "Check now: 48 V strip switch OFF for $NAME."
pause "48 V is OFF? Then start the dry run."

echo "== 3. Dry run (48 V off, nothing moves)"
b arm --watch 3
# shellcheck disable=SC2046
b pulse $(amps 20) --rise 50 --dur "$DUR" --fall 50 --watch 2
b release
sleep 1.5

banner "$GRN" ">>>  DRY RUN DONE: TURN THE 48 V POWER SUPPLY ON  <<<" "" "Ropes tied to fixed anchors, no person, treadmill off, everyone clear." "Hand on the strip switch."
if [ "$MOD" = "AC" ]; then
  pause "Dry run done. Ropes tied to fixed anchors, no person, treadmill off, everyone clear.
    Switch A's 48 V ON, wait 2 s, then C's 48 V ON (separate sockets, one at a time).
    Both ESCON LEDs must blink GREEN."
else
  pause "Dry run done. Rope tied to a fixed anchor, no person, treadmill off, everyone clear.
    Switch $NAME's 48 V ON (only that one). ESCON LED must blink GREEN."
fi

echo "== 4. Arm: rope(s) should tighten gently (2 N)"
b arm --watch 3

for f in 5 10 20; do
  pause "Next: pulse$(amps $f) N (bigger tug each time; with AC both at once). Stop if a rope pulls hard or slackens."
  # shellcheck disable=SC2046
  b pulse $(amps "$f") --rise 50 --dur "$DUR" --fall 50 --watch 2
done

echo "== 5. Release: rope(s) slacken, ESCON LED(s) blinking again"
b release
sleep 1.5
trap - INT
banner "$RED" "!!!  SWITCH THE 48 V POWER SUPPLY OFF NOW  !!!" "" "$NAME released."
pause "48 V is OFF?"
echo "Done. Tell Claude: LED and rope behaviour at arm and at each pulse."
