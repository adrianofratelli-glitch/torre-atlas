"""
api.py — Maestro Atlas Control Plane · Backend FastAPI
Expõe a lógica Python (atlas_client / ai_agent / chat_memory) como REST API
para o frontend React + LeafyGreen consumir via axios.

Credenciais vêm SEMPRE do ambiente (.env) — nunca do frontend.
Rode com:  uvicorn api:app --reload --port 8000
"""

import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from atlas_client import (
    AtlasClient, create_index_direct,
    DEDICATED_TIERS, NVME_TIERS, TIER_PRICING_USD,
)
from ai_agent import (
    analyze_cluster_stream, stream_chat,
    build_chat_system_prompt, generate_pdf_report, friendly_api_error,
)

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
USD_BRL = float(os.getenv("USD_BRL", "5.70"))

REGION_NAMES = {
    "US_EAST_1": "AWS · N. Virginia", "US_EAST_2": "AWS · Ohio",
    "US_WEST_1": "AWS · N. California", "US_WEST_2": "AWS · Oregon",
    "SA_EAST_1": "AWS · São Paulo", "EU_WEST_1": "AWS · Ireland",
    "EU_WEST_2": "AWS · London", "EU_CENTRAL_1": "AWS · Frankfurt",
    "AP_SOUTHEAST_1": "AWS · Singapore", "AP_SOUTHEAST_2": "AWS · Sydney",
    "AP_SOUTH_1": "AWS · Mumbai", "AP_NORTHEAST_1": "AWS · Tokyo",
    "CA_CENTRAL_1": "AWS · Canadá",
}

def pretty_region(code: str) -> str:
    if not code or code == "—":
        return "—"
    return REGION_NAMES.get(code, code.replace("_", " ").title())


def calculate_health_score(status: str, n_pa: int, n_sq: int, mongo_version: str) -> dict:
    score, issues = 100, []
    if status == "IDLE":
        pass
    elif status == "PAUSED":
        score -= 10; issues.append("Cluster PAUSADO (-10 pts)")
    else:
        score -= 20; issues.append(f"Status {status} não-IDLE (-20 pts)")
    pen = min(n_pa * 5, 30)
    if pen:
        score -= pen; issues.append(f"{n_pa} índice(s) sugerido(s) pelo PA (-{pen} pts)")
    pen = min(n_sq * 2, 30)
    if pen:
        score -= pen; issues.append(f"{n_sq} slow quer{'y' if n_sq == 1 else 'ies'} (-{pen} pts)")
    try:
        if int(mongo_version.split(".")[0]) < 7:
            score -= 10; issues.append(f"MongoDB {mongo_version} desatualizado (-10 pts)")
    except Exception:
        pass
    score = max(0, score)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
    color = "#00ED64" if score >= 75 else "#FFA500" if score >= 50 else "#FF4444"
    return {"score": score, "grade": grade, "color": color, "issues": issues}


# ── Atlas client (singleton a partir do ambiente) ─────────────────────────────
def get_client() -> AtlasClient:
    pub  = os.getenv("ATLAS_PUBLIC_KEY", "")
    priv = os.getenv("ATLAS_PRIVATE_KEY", "")
    org  = os.getenv("ATLAS_ORG_ID", "")
    proj = os.getenv("ATLAS_PROJECT_ID", "")
    if not (pub and priv and (org or proj)):
        raise HTTPException(status_code=503, detail="Credenciais Atlas ausentes no servidor (.env).")
    return AtlasClient(pub, priv, org, proj)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Maestro Atlas Control Plane API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Health / config ───────────────────────────────────────────────────────────
@app.get("/api/config")
def config():
    """Quais integrações estão configuradas no servidor (sem expor segredos)."""
    return {
        "atlas":     bool(os.getenv("ATLAS_PUBLIC_KEY") and os.getenv("ATLAS_PRIVATE_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "mongodb":   bool(os.getenv("MONGODB_URI")),
        "usd_brl":   USD_BRL,
        "tiers":     {"dedicated": DEDICATED_TIERS, "nvme": NVME_TIERS},
        "pricing":   TIER_PRICING_USD,
    }


# ── Clusters ──────────────────────────────────────────────────────────────────
@app.get("/api/clusters")
def list_clusters():
    client = get_client()
    rows = []
    try:
        projects = client.get_projects()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    for proj in projects:
        try:
            clusters = client.get_clusters(proj["id"])
        except Exception:
            continue
        for c in clusters:
            tier = region = "—"
            try:
                rc = c["replicationSpecs"][0]["regionConfigs"][0]
                tier = rc["electableSpecs"]["instanceSize"]
                region = rc["regionName"]
            except (KeyError, IndexError, TypeError):
                tier = "Free/Shared"
            status = "PAUSED" if c.get("paused") else c.get("stateName", "—")
            cost = AtlasClient.estimate_cost(tier, USD_BRL)
            rows.append({
                "project_id": proj["id"], "project_name": proj["name"],
                "cluster_name": c["name"], "tier": tier,
                "region": region, "region_pretty": pretty_region(region),
                "status": status, "mongo_version": c.get("mongoDBVersion", "—"),
                "cluster_type": c.get("clusterType", "—"),
                "cost_usd": cost["usd"], "cost_brl": cost["brl"],
            })
    return {"clusters": rows}


@app.get("/api/alerts")
def alerts(project_ids: str = Query("", description="IDs separados por vírgula")):
    client = get_client()
    total = 0
    for pid in [p for p in project_ids.split(",") if p]:
        try:
            total += len(client.get_open_alerts(pid))
        except Exception:
            pass
    return {"open_alerts": total}


@app.get("/api/invoice")
def invoice():
    client = get_client()
    inv = client.get_pending_invoice()
    return {"amount_usd": inv.get("amountBilledCents", 0) / 100 if inv else 0}


# ── Performance Advisor / Profiler / Métricas ─────────────────────────────────
def _primary_or_404(client, project_id, cluster_name):
    pid = client.get_primary(project_id, cluster_name)
    if not pid:
        raise HTTPException(status_code=404, detail="Processo primário não encontrado (cluster pausado?).")
    return pid


@app.get("/api/cluster/{project_id}/{cluster_name}/pa")
def perf_advisor(project_id: str, cluster_name: str):
    client = get_client()
    pid = _primary_or_404(client, project_id, cluster_name)
    return client.get_suggested_indexes(project_id, pid)


@app.get("/api/cluster/{project_id}/{cluster_name}/slow")
def slow_queries(project_id: str, cluster_name: str):
    client = get_client()
    pid = _primary_or_404(client, project_id, cluster_name)
    return client.get_slow_queries(project_id, pid)


@app.get("/api/cluster/{project_id}/{cluster_name}/measurements")
def measurements(project_id: str, cluster_name: str):
    client = get_client()
    pid = _primary_or_404(client, project_id, cluster_name)
    return client.get_measurements(project_id, pid)


@app.get("/api/cluster/{project_id}/{cluster_name}/series")
def series(project_id: str, cluster_name: str):
    client = get_client()
    pid = _primary_or_404(client, project_id, cluster_name)
    return client.get_measurements_series(project_id, pid)


@app.get("/api/cluster/{project_id}/{cluster_name}/health")
def health(project_id: str, cluster_name: str, status: str = "", mongo_version: str = "0"):
    client = get_client()
    n_pa = n_sq = 0
    pid = client.get_primary(project_id, cluster_name)
    if pid:
        try:
            n_pa = len(client.get_suggested_indexes(project_id, pid).get("suggestedIndexes", []))
            n_sq = len(client.get_slow_queries(project_id, pid).get("slowQueries", []))
        except Exception:
            pass
    hs = calculate_health_score(status, n_pa, n_sq, mongo_version)

    # Breakdown por componente (quanto cada um contribui / desconta)
    try:
        major = int(str(mongo_version).split(".")[0])
    except Exception:
        major = 0
    status_pts = 20 if status == "IDLE" else (10 if status == "PAUSED" else 0)
    components = [
        {"label": "Status do Cluster", "earned": status_pts, "max": 20,
         "detail": "IDLE = saudável" if status == "IDLE" else f"Status {status}",
         "ok": status == "IDLE"},
        {"label": "Saúde de Índices", "earned": max(0, 30 - min(n_pa * 5, 30)), "max": 30,
         "detail": "Nenhum índice sugerido pelo PA" if n_pa == 0 else f"{n_pa} índice(s) sugerido(s) — faltam índices",
         "ok": n_pa == 0},
        {"label": "Saúde de Queries", "earned": max(0, 30 - min(n_sq * 2, 30)), "max": 30,
         "detail": "Sem slow queries" if n_sq == 0 else f"{n_sq} slow quer{'y' if n_sq == 1 else 'ies'} registradas",
         "ok": n_sq == 0},
        {"label": "Versão do MongoDB", "earned": 10 if major >= 7 else 0, "max": 10,
         "detail": f"MongoDB {mongo_version}" + ("" if major >= 7 else " — desatualizada (<7)"),
         "ok": major >= 7},
        {"label": "Base", "earned": 10, "max": 10, "detail": "pontuação base", "ok": True},
    ]
    # Recomendações acionáveis para melhorar a nota
    tips = []
    if n_pa > 0:
        tips.append({"gain": min(n_pa * 5, 30), "text": f"Crie os {n_pa} índice(s) sugeridos no **Performance Advisor** — recupera até +{min(n_pa*5,30)} pts."})
    if n_sq > 0:
        tips.append({"gain": min(n_sq * 2, 30), "text": f"Otimize as {n_sq} slow queries (veja o **Query Profiler**) — elimine COLLSCANs para recuperar até +{min(n_sq*2,30)} pts."})
    if major and major < 7:
        tips.append({"gain": 10, "text": f"Atualize o MongoDB {mongo_version} → 7.0+ — recupera +10 pts e melhora performance."})
    if status == "PAUSED":
        tips.append({"gain": 10, "text": "Retome (resume) o cluster pausado — recupera +10 pts."})
    if not tips:
        tips.append({"gain": 0, "text": "Cluster já está no topo — nenhuma ação necessária. 🎉"})

    return {**hs, "n_pa": n_pa, "n_sq": n_sq, "components": components, "tips": tips}


@app.get("/api/finops")
def finops():
    """Avalia eficiência de custo (custo vs utilização real de CPU) por cluster."""
    client = get_client()
    out = []
    try:
        projects = client.get_projects()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))
    for proj in projects:
        try:
            clusters = client.get_clusters(proj["id"])
        except Exception:
            continue
        for c in clusters:
            try:
                rc = c["replicationSpecs"][0]["regionConfigs"][0]
                tier = rc["electableSpecs"]["instanceSize"]
            except (KeyError, IndexError, TypeError):
                tier = "Free/Shared"
            if c.get("paused") or tier == "Free/Shared":
                cpu = None
            else:
                pid = client.get_primary(proj["id"], c["name"])
                m = client.get_measurements(proj["id"], pid) if pid else {}
                cpu = m.get("cpu_pct") if m and "error" not in m else None
            cost = AtlasClient.estimate_cost(tier, USD_BRL)
            # Veredito de eficiência: custo alto + CPU baixa = desperdício
            verdict, color = "sem dados", "muted"
            if cpu is not None:
                if cpu < 15 and cost["usd"] >= 389:      # M30+
                    verdict, color = "subutilizado — possível economia", "yellow"
                elif cpu > 75:
                    verdict, color = "saturado — avaliar scale up", "red"
                else:
                    verdict, color = "saudável — bom uso do tier", "green"
            out.append({
                "project": proj["name"], "cluster": c["name"], "tier": tier,
                "cpu": cpu, "cost_usd": cost["usd"], "cost_brl": cost["brl"],
                "verdict": verdict, "color": color,
            })
    total_usd = sum(c["cost_usd"] for c in out)
    waste = [c for c in out if c["color"] == "yellow"]
    return {"clusters": out, "total_usd": total_usd,
            "potential_savings_usd": sum(c["cost_usd"] for c in waste)}


@app.get("/api/cluster/{project_id}/{cluster_name}/scaling")
def scaling(project_id: str, cluster_name: str, tier: str):
    client = get_client()
    pid = client.get_primary(project_id, cluster_name)
    meas = client.get_measurements(project_id, pid) if pid else {}
    return AtlasClient.recommend_scaling(meas, tier)


# ── Scale / Index (ações) ─────────────────────────────────────────────────────
class ScaleBody(BaseModel):
    new_tier: str

@app.post("/api/cluster/{project_id}/{cluster_name}/scale")
def scale(project_id: str, cluster_name: str, body: ScaleBody):
    client = get_client()
    try:
        result = client.scale_cluster(project_id, cluster_name, body.new_tier)
        return {"ok": True, "state": result.get("stateName", "UPDATING")}
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


class IndexBody(BaseModel):
    namespace: str
    index_keys: list

class ExplainBody(BaseModel):
    namespace: str
    filter: dict = {}

@app.post("/api/explain")
def explain_query(body: ExplainBody):
    """Roda explain('executionStats') real via pymongo no filtro informado."""
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise HTTPException(status_code=400, detail="MONGODB_URI não configurado no servidor.")
    try:
        from pymongo import MongoClient
        parts = body.namespace.split(".", 1)
        db_name, coll = parts[0], (parts[1] if len(parts) > 1 else parts[0])
        mc = MongoClient(uri, serverSelectionTimeoutMS=6000)
        plan = mc[db_name].command("explain", {"find": coll, "filter": body.filter},
                                   verbosity="executionStats")
        mc.close()
        exe = plan.get("executionStats", {})
        win = plan.get("queryPlanner", {}).get("winningPlan", {})
        return {
            "stage": win.get("stage") or win.get("inputStage", {}).get("stage", "—"),
            "docs_examined": exe.get("totalDocsExamined", "—"),
            "keys_examined": exe.get("totalKeysExamined", "—"),
            "n_returned": exe.get("nReturned", "—"),
            "exec_ms": exe.get("executionTimeMillis", "—"),
            "index_used": win.get("inputStage", {}).get("indexName") or win.get("indexName") or "COLLSCAN (sem índice)",
        }
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))


@app.post("/api/index")
def create_index(body: IndexBody):
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise HTTPException(status_code=400, detail="MONGODB_URI não configurado no servidor.")
    return {"result": create_index_direct(uri, body.namespace, body.index_keys)}


# ── Cost / estimate ───────────────────────────────────────────────────────────
@app.get("/api/cost")
def cost(tier: str):
    return AtlasClient.estimate_cost(tier, USD_BRL)


# ── AI: análise (stream) e chat (stream) ──────────────────────────────────────
class AnalyzeBody(BaseModel):
    project_id: str
    cluster_name: str

@app.post("/api/analyze")
def analyze(body: AnalyzeBody):
    client = get_client()
    full_c = client.get_cluster(body.project_id, body.cluster_name)
    pid = client.get_primary(body.project_id, body.cluster_name)
    pa = client.get_suggested_indexes(body.project_id, pid) if pid else {}
    sq = client.get_slow_queries(body.project_id, pid) if pid else {}

    def gen():
        try:
            for chunk in analyze_cluster_stream(full_c, pa, sq):
                yield chunk
        except Exception as e:
            yield friendly_api_error(e)
    return StreamingResponse(gen(), media_type="text/plain")


class ChatBody(BaseModel):
    messages: list           # [{"role","content"}]
    project_id: Optional[str] = None
    cluster_name: Optional[str] = None

@app.post("/api/chat")
def chat(body: ChatBody):
    # SEMPRE há system prompt (âncora MongoDB Atlas) — sem ele o modelo responde genérico.
    system = build_chat_system_prompt()
    if body.project_id and body.cluster_name:
        client = get_client()
        pid = client.get_primary(body.project_id, body.cluster_name)
        full_c = client.get_cluster(body.project_id, body.cluster_name)
        pa = client.get_suggested_indexes(body.project_id, pid) if pid else {}
        sq = client.get_slow_queries(body.project_id, pid) if pid else {}
        meas = client.get_measurements(body.project_id, pid) if pid else {}
        system = build_chat_system_prompt(full_c, pa, sq, meas)

    def gen():
        try:
            for chunk in stream_chat(body.messages, system):
                yield chunk
        except Exception as e:
            yield friendly_api_error(e)
    return StreamingResponse(gen(), media_type="text/plain")


# ── Chat history (persistência no Atlas, opcional) ────────────────────────────
def _mongo_or_400():
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise HTTPException(status_code=400, detail="MONGODB_URI não configurado.")
    return uri

@app.get("/api/chat/conversations")
def conversations(q: str = ""):
    uri = _mongo_or_400()
    from chat_memory import list_conversations, search_conversations
    rows = search_conversations(uri, q) if q else list_conversations(uri, limit=25)
    return {"conversations": [
        {"id": r["id"], "title": r["title"], "cluster": r.get("cluster", ""),
         "msg_count": r.get("msg_count", 0), "updated_at": str(r.get("updated_at", ""))}
        for r in rows
    ]}

@app.get("/api/chat/conversations/{conv_id}")
def conversation_messages(conv_id: str):
    uri = _mongo_or_400()
    from chat_memory import load_messages
    return {"messages": load_messages(uri, conv_id)}

@app.delete("/api/chat/conversations/{conv_id}")
def delete_conversation_ep(conv_id: str):
    uri = _mongo_or_400()
    from chat_memory import delete_conversation
    delete_conversation(uri, conv_id)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
