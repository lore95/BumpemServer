#!/bin/sh
# Print job for the makerspace: handoff PDF (German), assembly guide (English) + the STLs to print, in one zip.
# Run after make_stl.py:  ./druckauftrag.sh  ->  out/bumpem-druckauftrag-2026-10-22.zip
set -e
cd "$(dirname "$0")"
JOB=druckauftrag-2026-10-22
pdflatex -interaction=nonstopmode -halt-on-error -output-directory out "$JOB.tex" >/dev/null
rm -f "out/$JOB.aux" "out/$JOB.log"
rm -f "out/bumpem-$JOB.zip"
cd out && zip -q "bumpem-$JOB.zip" "$JOB.pdf" assembly-guide.pdf rs15_plate.stl rsp2000_bracket_B.stl rsp2000_brackets.stl iaa100_din_mount.stl
unzip -l "bumpem-$JOB.zip"
