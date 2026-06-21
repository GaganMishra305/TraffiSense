#!/usr/bin/env bash
# Start TraffiSense.ai locally and open it in the browser.
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
  echo "Creating virtual environment..."
  uv venv --python 3.11
fi
source .venv/bin/activate

echo "Installing dependencies (Walmart index)..."
uv pip install -q --index-url https://pypi.ci.artifacts.walmart.com/artifactory/api/pypi/external-pypi/simple \
  --allow-insecure-host pypi.ci.artifacts.walmart.com -r requirements.txt

PORT="${PORT:-8077}"
echo "Starting TraffiSense.ai on http://127.0.0.1:${PORT}"
( sleep 3; (open "http://127.0.0.1:${PORT}" 2>/dev/null || xdg-open "http://127.0.0.1:${PORT}" 2>/dev/null || true) ) &
uvicorn app.main:app --host 127.0.0.1 --port "${PORT}"
