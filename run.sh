#!/bin/bash
# Local BibleAPI launcher. Credentials come from bibleapi.env.json (see bibleapi.env.json.example).
# Do NOT put TiDB passwords in this file.
set -euo pipefail
cd "$(dirname "$0")"

export BIBLEAPI_LOCAL="${BIBLEAPI_LOCAL:-1}"
export PORT="${PORT:-5000}"

if [[ ! -f bibleapi.env.json ]]; then
  echo "Missing bibleapi.env.json"
  echo "Copy bibleapi.env.json.example → bibleapi.env.json and fill in TiDB credentials."
  exit 1
fi

if [[ -x venv/bin/python ]]; then
  exec venv/bin/python app.py
fi

exec python3 app.py
