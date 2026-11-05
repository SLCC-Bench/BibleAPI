#!/usr/bin/env bash
# Build BibleAPI as a PyInstaller onedir binary for desktop embedding.
# Prefer Praisehub's scripts/build-bibleapi.sh which copies into resources/.
set -euo pipefail

cd "$(dirname "$0")"
OUT_DIR="$(pwd)/dist/desktop"
mkdir -p "$OUT_DIR"

if [[ -x venv/bin/python ]]; then
  PYTHON=venv/bin/python
else
  PYTHON=python3
fi

"$PYTHON" -m pip install -q -r requirements.txt
"$PYTHON" -m pip install -q pyinstaller

"$PYTHON" -m PyInstaller \
  --noconfirm \
  --clean \
  --name bibleapi \
  --onedir \
  --console \
  --paths . \
  --hidden-import=certifi \
  --hidden-import=pymysql \
  --hidden-import=flask_cors \
  --hidden-import=routes.users \
  --hidden-import=routes.bible \
  --hidden-import=routes.uploadBible \
  --hidden-import=routes.updateBible \
  --hidden-import=routes.webhook \
  --hidden-import=routes.languages \
  --hidden-import=routes.songs \
  --hidden-import=routes.admin \
  --hidden-import=config_loader \
  --collect-all certifi \
  --add-data "static:static" \
  app.py

rm -rf "$OUT_DIR/bibleapi"
mkdir -p "$OUT_DIR"
mv dist/bibleapi "$OUT_DIR/bibleapi"
cp -f bibleapi.env.json.example "$OUT_DIR/bibleapi/bibleapi.env.json.example"
echo "Built $OUT_DIR/bibleapi"
