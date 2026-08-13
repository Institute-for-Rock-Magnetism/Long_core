#!/bin/sh
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
cd "$ROOT"
PYINSTALLER_CONFIG_DIR="$ROOT/build/.pyinstaller"
export PYINSTALLER_CONFIG_DIR

.venv/bin/python tools/build_icon.py
.venv/bin/python -m PyInstaller --noconfirm --clean LongCoreControl.spec

printf '\nBuilt application: %s\n' "$ROOT/dist/Long Core Control.app"
