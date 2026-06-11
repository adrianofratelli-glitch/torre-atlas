# 🗼 Torre — Atlas Control Plane

> Dashboard operacional para MongoDB Atlas com IA integrada (Claude) — a torre de controle da sua frota de clusters.
> **Frontend** React + [LeafyGreen](https://www.mongodb.design/) (design system oficial MongoDB) · **Backend** FastAPI reusando a lógica Python.

![React](https://img.shields.io/badge/React-18-blue)
![LeafyGreen](https://img.shields.io/badge/LeafyGreen-MongoDB-00ED64)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![Claude](https://img.shields.io/badge/Claude-Sonnet_4.6-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## 🏗️ Arquitetura

```
┌────────────────────────┐   /api proxy   ┌───────────────────────────┐
│  React 18 + Vite        │ ─────────────► │  FastAPI (api.py)          │
│  LeafyGreen (MongoDB)   │   :WEB → :API  │  atlas_client / ai_agent / │
│  darkMode               │ ◄───────────── │  chat_memory               │
└────────────────────────┘                └─────────────┬─────────────┘
                                                         ▼
                                              MongoDB Atlas (Admin API v2)
```

- **Credenciais ficam só no backend** (`.env`) — o frontend nunca as vê.
- Portas **auto-detectadas** (livres) para não colidir com outras POCs.

## ✨ Funcionalidades

| Página | Descrição |
|--------|-----------|
| 📊 **Visão Geral** | Snapshot estático e rápido da frota (clusters, status, custo, alertas) |
| 🗄️ **Clusters** | Tabela de todos os clusters da org com tier, região, status e custo |
| ⚡ **Performance Advisor** | Índices sugeridos + execução via pymongo + análise com Claude + relatório PDF |
| 🔍 **Query Profiler** | Slow queries parseadas (plano, COLLSCAN, docs examinados, latência) |
| ❤️ **Health Score** | Nota 0–100 combinando PA, slow queries, status e versão |
| 📈 **Scale** | Recomendação inteligente (CPU/conexões/IOPS reais) + gráfico 24h + scaling |
| 💰 **FinOps** | Estimativa de custo por cluster e projeto |
| 📊 **Compare** | Comparativo side-by-side entre 2 clusters |
| 💬 **AI Chat** | Chat com Claude usando contexto real do cluster (streaming) + histórico persistido no Atlas |

---

## 🚀 Como rodar

### Pré-requisitos
- Python 3.10+ · Node 18+ · Conta MongoDB Atlas · API Key Anthropic

### 1. Configure o `.env`
```bash
cp env_template.txt .env   # edite com suas chaves
```
```env
ATLAS_PUBLIC_KEY=...
ATLAS_PRIVATE_KEY=...
ATLAS_ORG_ID=...
ANTHROPIC_API_KEY=...
MONGODB_URI=mongodb+srv://...   # opcional (criar índices + histórico do chat)
CLAUDE_MODEL=claude-sonnet-4-6  # opcional (default; ex: claude-opus-4-8)
```

### 2. Suba tudo com um comando
```bash
./run_react.sh
```
O script ativa o venv, instala dependências se necessário, **acha portas livres** e sobe backend + frontend juntos. URLs aparecem no terminal.

> Atalho opcional no `~/.zshrc`:
> ```bash
> alias torre="cd ~/torre && source venv/bin/activate && ./run_react.sh"
> ```
> Depois é só digitar `torre`.

### Portas
Defaults incomuns **8765** (API) / **5290** (UI), configuráveis:
```bash
API_PORT=8770 WEB_PORT=5295 ./run_react.sh
```

---

## 🗂️ Estrutura

```
torre/
├── api.py                # Backend FastAPI — expõe a lógica como REST
├── atlas_client.py       # Client da Atlas Admin API v2 + recomendação de scaling
├── ai_agent.py           # Claude (streaming) — análise + chat + PDF
├── chat_memory.py        # Persistência do chat no Atlas (pymongo)
├── requirements.txt      # Deps do backend
├── run_react.sh          # Sobe backend + frontend (portas livres)
└── frontend/             # React 18 + Vite + LeafyGreen
    ├── src/api.js         # Cliente axios + streaming
    ├── src/App.jsx        # Shell + navegação
    └── src/pages/         # 9 páginas
```

---

## 🙏 Créditos

O Torre foi baseado no **Maestro**, projeto original criado pela **Carime** — obrigado pela base e inspiração! 💚

## 📄 Licença

MIT — veja [LICENSE](LICENSE).

*Construído para demonstrar o poder do MongoDB Atlas em aplicações financeiras de alto volume.*
