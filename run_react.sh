#!/bin/bash
# run_react.sh — start Torre (FastAPI + React/LeafyGreen).
# Cleans up leftovers from previous runs and auto-detects free ports.
cd "$(dirname "$0")"

# Load .env
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); echo "Loaded .env"; fi

# Kill old Torre instances only (leaves other local services untouched)
pkill -f "uvicorn api:app" 2>/dev/null
pkill -f "torre/frontend.*vite" 2>/dev/null
# Generic vite process only if it belongs to this folder
for pid in $(pgrep -f "vite" 2>/dev/null); do
  if ps -o command= -p "$pid" 2>/dev/null | grep -q "torre"; then kill "$pid" 2>/dev/null; fi
done
sleep 1

# Find the first free port starting from a given value
free_port() { local p=$1; while lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; do p=$((p+1)); done; echo "$p"; }
export API_PORT="${API_PORT:-$(free_port 8765)}"
export WEB_PORT="${WEB_PORT:-$(free_port 5290)}"

# Backend dependencies
if ! python -c "import fastapi" 2>/dev/null; then
  echo "Installing backend dependencies..."; pip install -q -r requirements.txt
fi

echo "──────────────────────────────────────────────"
echo "Backend  (API) -> http://localhost:$API_PORT"
echo "Frontend (UI)  -> http://localhost:$WEB_PORT"
echo "──────────────────────────────────────────────"

uvicorn api:app --port "$API_PORT" --reload &
BACK=$!
trap "kill $BACK 2>/dev/null; pkill -f 'uvicorn api:app' 2>/dev/null" EXIT

cd frontend
[ -d node_modules ] || npm install --silent
npm run dev
