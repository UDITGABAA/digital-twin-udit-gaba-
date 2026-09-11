#!/usr/bin/env bash
# One command to a demo-ready machine (macOS/Linux). Run from the repo root: bash scripts/demo.sh
set -euo pipefail
cd "$(dirname "$0")/.."
pip install -r requirements.txt
npm install --prefix dashboard
python -m pytest -q || { echo "TESTS RED - do not demo"; exit 1; }
npm run build --prefix dashboard
python -m uvicorn server.app:app --port 8000 &
npm run dev --prefix dashboard &
sleep 3
echo "Primary: http://localhost:5173   Fallback (API only, serves the built dashboard): http://localhost:8000"
wait
