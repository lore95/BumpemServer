#!/bin/sh
# Rebuild the carrier board from netlist.py: schematic, board, checks, fab files.
# Needs KiCad 8 (macOS paths below). Run from anywhere: hardware/carrier/build.sh
set -eu
cd "$(dirname "$0")"
KAPP=/Applications/KiCad/KiCad.app/Contents
K=$KAPP/MacOS/kicad-cli
KPY=$KAPP/Frameworks/Python.framework/Versions/3.9/bin/python3

python3 gen_schematic.py
"$KPY" gen_carrier.py 2>&1 | grep -v Debug

echo "== checks (all must be 0)"
"$K" sch erc --severity-all --exit-code-violations -o /dev/null bumpem-carrier.kicad_sch >/dev/null && echo "ERC: 0 violations"
"$K" pcb drc --schematic-parity --severity-all --exit-code-violations -o /dev/null bumpem-carrier.kicad_pcb >/dev/null \
  && echo "DRC + schematic parity: 0 violations, 0 unconnected"

echo "== fab files -> fab/"
rm -rf fab && mkdir -p fab/gerbers
"$K" pcb export gerbers --layers "F.Cu,B.Cu,F.Mask,B.Mask,F.Silkscreen,B.Silkscreen,Edge.Cuts" --subtract-soldermask \
  -o fab/gerbers/ bumpem-carrier.kicad_pcb >/dev/null
"$K" pcb export drill --format excellon --excellon-separate-th -o fab/gerbers/ bumpem-carrier.kicad_pcb >/dev/null
(cd fab/gerbers && zip -q ../bumpem-carrier-gerbers.zip ./*)
"$K" sch export pdf -o fab/bumpem-carrier-schematic.pdf bumpem-carrier.kicad_sch >/dev/null
"$K" sch export bom --fields 'Reference,Value,Footprint,${QUANTITY}' --group-by "Value,Footprint" \
  -o fab/bumpem-carrier-bom.csv bumpem-carrier.kicad_sch >/dev/null
"$K" pcb export pdf --layers "F.Cu,B.Cu,F.Silkscreen,Edge.Cuts" -o fab/bumpem-carrier-layout.pdf bumpem-carrier.kicad_pcb >/dev/null
ls fab
