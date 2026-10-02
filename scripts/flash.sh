#!/bin/sh
# Build + upload firmware to Teensy 4.1 (requires: pip install platformio)
#   scripts/flash.sh            v1 firmware (firmware/src/main.ino)
#   scripts/flash.sh legacy     v0 reference (legacy/Arduino_Script.ino)
#   scripts/flash.sh loadcell   load-cell check (firmware/tools/loadcell_check)
set -eu
dir="$(dirname "$0")/../firmware"
case "${1:-}" in
  "")       ;;
  legacy)   dir="$dir/legacy" ;;
  loadcell) dir="$dir/tools/loadcell_check" ;;
  *)        echo "usage: $0 [legacy|loadcell]" >&2; exit 1 ;;
esac
cd "$dir"
pio run -t upload
