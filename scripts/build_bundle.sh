#!/bin/sh
# Builds the offline Windows bundle (docs/TODO.md "Offline install"): Python installer, wheels, both repos at HEAD,
# settings, the .bat files of scripts/bundle/. Output: ../dist/BumpemLab_<date>/ and .zip next to it.
# Needs internet (python.org, PyPI). Only committed files of the repos go in (git archive).
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)            # BumpemServer
UI="$HERE/../BumpemUI"
PYV=3.12.10
PY="${PY:-$HOME/miniconda3/bin/python}"
NAME="BumpemLab_$(date +%Y-%m-%d)"
DIST="$HERE/../dist"
OUT="$DIST/$NAME"

[ -e "$OUT" ] && { echo "$OUT exists: remove it first"; exit 1; }
mkdir -p "$OUT/installers" "$OUT/wheels" "$OUT/vicon" "$OUT/BumpemServer" "$OUT/BumpemUI"

git -C "$HERE" archive HEAD | tar -x -C "$OUT/BumpemServer"
git -C "$UI" archive HEAD | tar -x -C "$OUT/BumpemUI"
for f in settings.json force_logger_cal.json; do [ -f "$HERE/$f" ] && cp "$HERE/$f" "$OUT/BumpemServer/"; done

curl -fL --progress-bar -o "$OUT/installers/python-$PYV-amd64.exe" "https://www.python.org/ftp/python/$PYV/python-$PYV-amd64.exe"
"$PY" -m pip download -q --only-binary=:all: --platform win_amd64 --python-version 3.12 --implementation cp --abi cp312 \
  -d "$OUT/wheels" -r "$HERE/scripts/bundle/requirements.txt"

# check: the wheels alone satisfy requirements.txt for Windows / Python 3.12
"$PY" -m pip install -q --dry-run --no-index --find-links "$OUT/wheels" --only-binary=:all: --platform win_amd64 \
  --python-version 3.12 --implementation cp --abi cp312 --target "$OUT/.check" -r "$HERE/scripts/bundle/requirements.txt"
rm -rf "$OUT/.check"

for f in "$HERE"/scripts/bundle/*; do              # Windows line endings
  sed 's/$/\r/' "$f" > "$OUT/$(basename "$f")"
done
sed -i '' "s/@BUILT@/$(date '+%Y-%m-%d %H:%M')/; s/@SERVER@/$(git -C "$HERE" rev-parse --short HEAD)/; s/@UI@/$(git -C "$UI" rev-parse --short HEAD)/" "$OUT/README.txt"
echo "Put the Vicon DataStream SDK installer (vicon.com) here before copying the bundle." | sed 's/$/\r/' > "$OUT/vicon/PUT_SDK_INSTALLER_HERE.txt"

(cd "$DIST" && zip -qr "$NAME.zip" "$NAME")
du -sh "$OUT" "$DIST/$NAME.zip"
