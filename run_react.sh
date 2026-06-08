#!/bin/bash
# run_react.sh — sobe o Maestro v3 (FastAPI + React/LeafyGreen)
# Mata leftovers de execuções anteriores e auto-detecta portas livres.
cd "$(dirname "$0")"

# Carrega .env
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); echo "✅ .env carregado"; fi

# Mata instâncias antigas DO MAESTRO (não toca em outras POCs)
pkill -f "uvicorn api:app" 2>/dev/null
pkill -f "maestro/frontend.*vite" 2>/dev/null
# vite genérico só se for desta pasta
for pid in $(pgrep -f "vite" 2>/dev/null); do
  if ps -o command= -p "$pid" 2>/dev/null | grep -q "maestro"; then kill "$pid" 2>/dev/null; fi
done
sleep 1

# Acha 1ª porta livre a partir de um valor inicial
free_port() { local p=$1; while lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; do p=$((p+1)); done; echo "$p"; }
export API_PORT="${API_PORT:-$(free_port 8765)}"
export WEB_PORT="${WEB_PORT:-$(free_port 5290)}"

# Deps backend
if ! python -c "import fastapi" 2>/dev/null; then
  echo "📦 Instalando deps do backend…"; pip install -q fastapi "uvicorn[standard]" sse-starlette
fi

echo "──────────────────────────────────────────────"
echo "🍃 Backend  (API) → http://localhost:$API_PORT"
echo "⚛️  Frontend (UI)  → http://localhost:$WEB_PORT"
echo "──────────────────────────────────────────────"

uvicorn api:app --port "$API_PORT" --reload &
BACK=$!
trap "kill $BACK 2>/dev/null; pkill -f 'uvicorn api:app' 2>/dev/null" EXIT

cd frontend
[ -d node_modules ] || npm install --silent
npm run dev
