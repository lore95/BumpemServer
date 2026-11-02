#!/bin/sh
# Vicon DataStream SDK (Windows) -> vendor/vicon_dssdk-<version>-py3-none-any.whl, shipped in the bundle's wheels\ (D36).
#   scripts/vicon_wheel.sh ../bumpemInstallation/ViconDataStreamSDK_1.13.0+167154h_Win64.zip
# Takes Win64/Python/vicon_dssdk out of the SDK's .msi without running it (msiextract: brew install msitools).
# Drops setup.py's install_requires=['enum34']: a Python 2 backport that shadows the standard enum on Python 3.
# Vicon's licence (MIT, in the wheel) allows redistribution. vendor/ is not in git.
set -eu
HERE=$(cd "$(dirname "$0")/.." && pwd)
PY="${PY:-$HOME/miniconda3/bin/python}"
ZIP=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT

(cd "$TMP" && unzip -q "$ZIP")
MSI=$(find "$TMP" -name '*_x64.msi' | head -1)
[ -n "$MSI" ] || { echo "no *_x64.msi in $ZIP (the Win64 download is needed, not Mac/Linux)"; exit 1; }
mkdir "$TMP/msi"
msiextract -C "$TMP/msi" "$MSI" >/dev/null
SRC=$(find "$TMP/msi" -type d -path '*Win64/Python/vicon_dssdk' | head -1)
[ -f "$SRC/setup.py" ] || { echo "Win64/Python/vicon_dssdk not found in the msi"; exit 1; }
grep -q "install_requires=\['enum34'\]," "$SRC/setup.py" || { echo "setup.py changed: check its install_requires by hand"; exit 1; }
sed -i '' "s/install_requires=\['enum34'\],/install_requires=[],/" "$SRC/setup.py"
[ -f "$SRC/vicon_dssdk/_CoreClient3.pyd" ] && [ -f "$SRC/vicon_dssdk/ViconDataStreamSDK_CPP.dll" ] || { echo "binaries missing"; exit 1; }

mkdir -p "$HERE/vendor"
rm -f "$HERE"/vendor/vicon_dssdk-*.whl
"$PY" -m pip wheel -q --no-deps --no-build-isolation -w "$HERE/vendor" "$SRC"
WHL=$(ls "$HERE"/vendor/vicon_dssdk-*.whl)
unzip -l "$WHL" | grep -q "vicon_dssdk/_CoreClient3.pyd" || { echo "wheel lacks _CoreClient3.pyd"; exit 1; }
unzip -p "$WHL" '*/METADATA' | grep -q '^Requires-Dist' && { echo "wheel still requires something"; exit 1; }
echo "$WHL"
