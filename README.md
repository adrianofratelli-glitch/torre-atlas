# Torre — Atlas Control Plane

Operational dashboard for MongoDB Atlas with a built-in Claude assistant. A single control plane for a fleet of clusters: status, cost, performance, and AI-assisted analysis.

The frontend is React with [LeafyGreen](https://www.mongodb.design/), MongoDB's official design system. The backend is FastAPI, exposing the existing Python logic as a REST API.

![React](https://img.shields.io/badge/React-18-blue)
![LeafyGreen](https://img.shields.io/badge/LeafyGreen-MongoDB-00ED64)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-009688)
![Claude](https://img.shields.io/badge/Claude-Anthropic-orange)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

> Note: the user interface is in Brazilian Portuguese (pt-BR) by design, since this was built for a Brazilian audience. Source code, comments, and documentation are in English.

## Architecture

```
┌────────────────────────┐   /api proxy   ┌───────────────────────────┐
│  React 18 + Vite        │ ─────────────► │  FastAPI (api.py)          │
│  LeafyGreen (MongoDB)   │   WEB → API    │  atlas_client / ai_agent / │
│  dark mode              │ ◄───────────── │  chat_memory               │
└────────────────────────┘                └─────────────┬─────────────┘
                                                         ▼
                                              MongoDB Atlas (Admin API v2)
```

Credentials live only in the backend (`.env`); the frontend never sees them. The startup script auto-detects free ports so Torre does not collide with other local services.

## Features

| Page | Description |
|------|-------------|
| Overview | Fast static snapshot of the fleet: clusters, status, cost, and alerts. |
| Clusters | Table of every cluster in the org with tier, region, status, and cost. |
| Performance Advisor | Suggested indexes, execution via pymongo, Claude analysis, and a PDF report. |
| Query Profiler | Parsed slow queries (plan, COLLSCAN, documents examined, latency), with a real `explain('executionStats')`. |
| Health Score | A 0–100 score combining Performance Advisor, COLLSCAN shapes, status, and version. |
| Scale | Tier recommendation from 24h CPU (p95/avg), memory, storage, and connections, plus native auto-scaling status. |
| FinOps | Current invoice (Billing API) plus estimated cost vs 24h utilization per cluster. |
| Compare | Side-by-side comparison of two clusters. |
| AI Chat | Claude chat grounded in real cluster context (streaming), with history persisted in Atlas. |

## Getting started

### Prerequisites

Python 3.10+, Node 18+, a MongoDB Atlas account, and an Anthropic API key.

### 1. Configure the environment

```bash
cp .env.example .env   # then fill in your keys
```

```env
ATLAS_PUBLIC_KEY=...
ATLAS_PRIVATE_KEY=...
ATLAS_ORG_ID=...
ANTHROPIC_API_KEY=...
MONGODB_URI=mongodb+srv://...   # optional: index creation and chat history
CLAUDE_MODEL=claude-sonnet-5    # optional: defaults to Sonnet 5
```

### 2. Run

```bash
./run_react.sh
```

The script activates the virtualenv, installs dependencies if needed, finds free ports, and starts the backend and frontend together. The URLs are printed to the terminal.

Optional shell alias:

```bash
alias torre="cd ~/torre && source venv/bin/activate && ./run_react.sh"
```

### Ports

The defaults are 8765 (API) and 5290 (UI). Override them with environment variables:

```bash
API_PORT=8770 WEB_PORT=5295 ./run_react.sh
```

## Project layout

```
torre/
├── api.py                # FastAPI backend; exposes the Python logic as REST
├── atlas_client.py       # Atlas Admin API v2 client and scaling recommendations
├── ai_agent.py           # Claude analysis, chat, and PDF generation (streaming)
├── chat_memory.py        # Chat history persisted in Atlas (pymongo)
├── requirements.txt      # Backend dependencies
├── run_react.sh          # Starts backend + frontend on free ports
└── frontend/             # React 18 + Vite + LeafyGreen
    ├── src/api.js         # Axios client and streaming
    ├── src/App.jsx        # Shell and navigation
    └── src/pages/         # One component per page
```

## Credits

Torre is based on Maestro, originally created by [Carime](https://github.com/carimeb) ([maestro-atlas-landing-zone](https://github.com/carimeb/maestro-atlas-landing-zone)). Thanks to her for the foundation.

## License

MIT. See [LICENSE](LICENSE).
