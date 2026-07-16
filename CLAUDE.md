# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Torre — Atlas Control Plane. Operational dashboard for MongoDB Atlas with a built-in Claude assistant. React 18 + Vite + LeafyGreen frontend, FastAPI backend that wraps the Atlas Admin API v2 and Claude.

UI is pt-BR by design (built for Brazilian audience). Source code, comments, docs: English.

## Architecture

```
React 18 + Vite (frontend/) --/api proxy--> FastAPI (api.py) --> atlas_client / ai_agent / chat_memory --> MongoDB Atlas Admin API v2
```

- `api.py` — FastAPI backend, all REST routes (`/api/...`), plus request-id/metrics middleware and optional bearer-token auth (`API_AUTH_TOKEN`).
- `atlas_client.py` — Atlas Admin API v2 client, scaling recommendation logic.
- `ai_agent.py` — Claude analysis, streaming chat, PDF report generation.
- `chat_memory.py` — chat history persisted in Atlas via pymongo.
- `observability.py` — structured logging (`LOG_JSON=1` for JSON logs) and in-process metrics (`GET /api/metrics`).
- `populate_workload.py`, `populate_profiler.py` — standalone scripts to seed sample workload/profiler data.
- `tests/` — unittest suite for the scaling heuristic, injection guards, and `chat_memory` id validation.
- `frontend/src/api.js` — axios client + streaming.
- `frontend/src/App.jsx` — shell/navigation.
- `frontend/src/styles.css` — MongoDB dark design tokens (shared palette with the other PoVs in this workspace: `--bg-primary`, `--accent`, `--text-pri/sec/muted`, etc.) plus Outfit/JetBrains Mono typography.
- `frontend/src/pages/` — one component per page (Overview, Clusters, PerformanceAdvisor, Profiler, Health, Scale, FinOps, Compare, Chat).

Credentials live only in backend `.env`; frontend never sees them.

## Commands

```bash
./run_react.sh          # activates venv, installs deps if needed, finds free ports, starts backend+frontend
```

Ports default to 8765 (API) / 5290 (UI); override with `API_PORT` / `WEB_PORT` env vars.

Frontend only (from `frontend/`):
```bash
npm run dev
npm run build
npm run preview
```

Backend only: `uvicorn api:app --reload` (needs venv activated, `.env` populated).

Tests: `python -m unittest discover -s tests -v` (no Atlas/Mongo credentials required — pure-logic + guard tests only).

Docker (single container, nginx serves the frontend build and proxies `/api` to FastAPI):
```bash
docker build -t torre .
docker run --env-file .env -p 8080:8080 torre
```

No linter is configured in this repo.

## Environment

Copy `.env.example` to `.env` and fill in: `ATLAS_PUBLIC_KEY`, `ATLAS_PRIVATE_KEY`, `ATLAS_ORG_ID`, `ANTHROPIC_API_KEY`, optionally `MONGODB_URI` (index creation + chat history) and `CLAUDE_MODEL` (defaults to Sonnet 5).
