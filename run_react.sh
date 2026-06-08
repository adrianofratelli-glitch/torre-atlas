#!/bin/bash
# run_react.sh — sobe o Maestro v3 (backend FastAPI + frontend React/LeafyGreen)
cd "$(dirname "$0")"

# .env
if [ -f .env ]; then export $(grep -v '^#' .env | xargs); echo "✅ .env carregado"; fi

# deps backend
if ! python -c "import fastapi" 2>/dev/null; then pip install -q fastapi "uvicorn[standard]" sse-starlette; fi

echo "🍃 Backend  → http://localhost:8010  (API)"
echo "⚛️  Frontend → http://localhost:5173  (UI)"

# Backend em background
uvicorn api:app --port 8010 --reload &
BACK=$!
# Frontend
( cd frontend && npm install --silent && npm run dev )
kill $BACK 2>/dev/null
