#!/bin/bash
# run_react.sh — sobe o Maestro v3 (FastAPI + React/LeafyGreen)
# Auto-detecta portas LIVRES para não colidir com outras POCs em execução.
cd "$(dirname "$0")"

# Carrega .env
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); echo "✅ .env carregado"; fi

# Acha a 1ª porta livre a partir de um valor inicial
free_port() {
  local p=$1
  while lsof -iTCP:"$p" -sTCP:LISTEN >/dev/null 2>&1; do
    p=$((p+1))
  done
  echo "$p"
}

# Portas: respeita env se setado, senão parte de defaults incomuns e pula ocupadas
export API_PORT="${API_PORT:-$(free_port 8765)}"
export WEB_PORT="${WEB_PORT:-$(free_port 5290)}"

# Garante deps do backend
if ! python -c "import fastapi" 2>/dev/null; then
  echo "📦 Instalando deps do backend…"
  pip install -q fastapi "uvicorn[standard]" sse-starlette
fi

echo "──────────────────────────────────────────────"
echo "🍃 Backend  (API) → http://localhost:$API_PORT"
echo "⚛️  Frontend (UI)  → http://localhost:$WEB_PORT"
echo "──────────────────────────────────────────────"

# Backend em background
uvicorn api:app --port "$API_PORT" --reload &
BACK=$!
trap "kill $BACK 2>/dev/null" EXIT

# Frontend (recebe API_PORT/WEB_PORT via env — vite.config.js usa)
cd frontend
[ -d node_modules ] || npm install --silent
npm run dev
