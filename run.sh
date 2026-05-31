#!/bin/bash
# run.sh — inicia o Maestro v2.0

cd "$(dirname "$0")"

# Carrega .env se existir
if [ -f .env ]; then
    export $(grep -v '^#' .env | xargs)
    echo "✅ .env carregado"
fi

# Instala dependências se necessário
if ! python -c "import fpdf" 2>/dev/null; then
    echo "📦 Instalando dependências novas…"
    pip install -q fpdf2 pymongo
fi

echo "🎯 Iniciando Maestro v2.0 na porta 8502…"
streamlit run app.py --server.port 8502 --server.headless false
