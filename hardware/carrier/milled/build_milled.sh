#!/bin/sh
# Makerspace version of the carrier board: generate, check, fab files -> fab/bumpem-carrier-milled-fab.zip
# Needs KiCad 8 (macOS paths). Run from anywhere: hardware/carrier/milled/build_milled.sh
set -eu
cd "$(dirname "$0")"
KAPP=/Applications/KiCad/KiCad.app/Contents
K=$KAPP/MacOS/kicad-cli
KPY=$KAPP/Frameworks/Python.framework/Versions/3.9/bin/python3
PCB=bumpem-carrier-milled.kicad_pcb

"$KPY" gen_milled.py 2>&1 | grep -v "Debug\|assert"
echo "== checks"
"$K" pcb drc --severity-error --exit-code-violations -o /tmp/bumpem-milled-drc.rpt "$PCB" >/dev/null || true
grep -E "^\*\* Found" /tmp/bumpem-milled-drc.rpt || true
echo "   (the 7 'unconnected' items are the wire links W1-W7; check_milled.py counts them as connections)"
"$KPY" check_milled.py "$PCB" 2>&1 | grep -v "Debug\|assert"

echo "== fab files -> fab/"
rm -rf fab && mkdir -p fab/gerbers
"$K" pcb export gerbers --layers "B.Cu,Edge.Cuts" -o fab/gerbers/ "$PCB" >/dev/null
"$K" pcb export drill --format excellon -o fab/gerbers/ "$PCB" >/dev/null      # one drill file: every hole, nothing plated
cp MAKERSPACE.txt fab/gerbers/
"$K" pcb export pdf --layers "B.Cu,Edge.Cuts" --mirror -o fab/bumpem-carrier-milled-bottom.pdf "$PCB" >/dev/null
"$K" pcb export pdf --layers "F.Fab,Edge.Cuts" -o fab/bumpem-carrier-milled-parts.pdf "$PCB" >/dev/null
"$KPY" ../dump_board.py "$PCB" fab/board.json 2>&1 | grep -v "Debug\|assert" >/dev/null
python3 soldering_guide_milled.py || echo "   soldering guide: run soldering_guide_milled.py with a Python that has matplotlib"
# one zip: the milling files (gerbers/, for the makerspace) + the PDFs (preview, parts placement, soldering guide)
(cd fab && rm -f bumpem-carrier-milled.zip && zip -q -r bumpem-carrier-milled.zip gerbers bumpem-carrier-milled-bottom.pdf \
   bumpem-carrier-milled-parts.pdf bumpem-carrier-milled-soldering.pdf)
unzip -l fab/bumpem-carrier-milled.zip
