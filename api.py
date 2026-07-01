"""
api.py — Torre Atlas Control Plane · FastAPI backend
Exposes the Python logic (atlas_client / ai_agent / chat_memory) as a REST API
for the React + LeafyGreen frontend to consume via axios.

Credentials ALWAYS come from the environment (.env) — never from the frontend.
Run with:  uvicorn api:app --reload --port 8000
"""

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
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


def _uri_cluster_hash() -> str:
    """Unique hash of the cluster MONGODB_URI points to ('' if unset/unparseable)."""
    m = re.search(r'\.([a-z0-9]+)\.mongodb\.net', os.getenv("MONGODB_URI", "").lower())
    return m.group(1) if m else ""


def _cluster_srv_hash(cluster: dict) -> str:
    srv = (cluster.get("connectionStrings") or {}).get("standardSrv", "") or cluster.get("srvAddress", "")
    m = re.search(r'\.([a-z0-9]+)\.mongodb\.net', str(srv).lower())
    return m.group(1) if m else ""


def _cpu_24h_stats(client: AtlasClient, project_id: str, process_id: str) -> Optional[dict]:
    """avg/p95 of normalized CPU over the last 24h — scaling and efficiency
    verdicts must not rely on a 5-min snapshot."""
    series = client.get_measurements_series(project_id, process_id)
    if "error" in series:
        return None
    vals = [v for v in series.get("cpu", []) if v is not None]
    if not vals:
        return None
    ordered = sorted(vals)
    return {"avg": round(sum(vals) / len(vals), 1),
            "p95": round(ordered[int(0.95 * (len(ordered) - 1))], 1)}


# ── Atlas client (singleton built from the environment) ───────────────────────
def get_client() -> AtlasClient:
    pub  = os.getenv("ATLAS_PUBLIC_KEY", "")
    priv = os.getenv("ATLAS_PRIVATE_KEY", "")
    org  = os.getenv("ATLAS_ORG_ID", "")
    proj = os.getenv("ATLAS_PROJECT_ID", "")
    if not (pub and priv and (org or proj)):
        raise HTTPException(status_code=503, detail="Credenciais Atlas ausentes no servidor (.env).")
    return AtlasClient(pub, priv, org, proj)


# ── App ───────────────────────────────────────────────────────────────────────
app = FastAPI(title="Torre Atlas Control Plane API", version="3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "http://localhost:5173,http://localhost:3000").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Conversation-Id"],
)


# ── MongoDB (cached client — connection pool reused across requests) ──────────
_mongo_clients: dict = {}

def _mongo(uri: str):
    from pymongo import MongoClient
    if uri not in _mongo_clients:
        _mongo_clients[uri] = MongoClient(uri, serverSelectionTimeoutMS=6000)
    return _mongo_clients[uri]


# ── Health / config ───────────────────────────────────────────────────────────
@app.get("/api/config")
def config():
    """Which integrations are configured on the server (without exposing secrets)."""
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
    uri_hash = _uri_cluster_hash()
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
            autoscale = {}
            try:
                rc = c["replicationSpecs"][0]["regionConfigs"][0]
                tier = rc["electableSpecs"]["instanceSize"]
                region = rc["regionName"]
                autoscale = rc.get("autoScaling") or {}
            except (KeyError, IndexError, TypeError):
                tier = "Free/Shared"
            status = "PAUSED" if c.get("paused") else c.get("stateName", "—")
            cost = AtlasClient.estimate_cost(tier, USD_BRL)
            compute = autoscale.get("compute") or {}
            rows.append({
                "project_id": proj["id"], "project_name": proj["name"],
                "cluster_name": c["name"], "tier": tier,
                "region": region, "region_pretty": pretty_region(region),
                "status": status, "mongo_version": c.get("mongoDBVersion", "—"),
                "cluster_type": c.get("clusterType", "—"),
                "cost_usd": cost["usd"], "cost_brl": cost["brl"],
                # whether MONGODB_URI points to THIS cluster (gates index/explain actions)
                "is_uri_target": bool(uri_hash) and _cluster_srv_hash(c) == uri_hash,
                "autoscale_compute": bool(compute.get("enabled")),
                "autoscale_min": compute.get("minInstanceSize", ""),
                "autoscale_max": compute.get("maxInstanceSize", ""),
                "autoscale_disk": bool((autoscale.get("diskGB") or {}).get("enabled")),
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


# ── Performance Advisor / Profiler / Metrics ──────────────────────────────────
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
    pid = client.get_primary(project_id, cluster_name)
    if not pid:
        # Paused/transitioning cluster: PA and profiler have no process to report
        # on — an honest "no grade" beats scoring 90 on absent data.
        return {"score": None, "grade": "—", "color": "#7fa8bc", "n_pa": 0, "n_sq": 0,
                "components": [],
                "issues": ["Cluster pausado ou em transição — sem dados de PA/profiler."],
                "tips": [{"gain": 0, "text": "Retome o cluster para calcular o Health Score — "
                          "pausado, não há processo primário para o Performance Advisor e o profiler avaliarem."}]}

    n_pa = n_sq = 0
    collscan_shapes = set()
    try:
        n_pa = len(client.get_suggested_indexes(project_id, pid).get("suggestedIndexes", []))
        slow = client.get_slow_queries(project_id, pid).get("slowQueries", [])
        n_sq = len(slow)
        for q in slow:
            try:
                attr = json.loads(q.get("line") or "{}").get("attr", {})
            except Exception:
                attr = {}
            if "COLLSCAN" in str(attr.get("planSummary", "")):
                collscan_shapes.add((q.get("namespace", ""), str(attr.get("type", ""))))
    except Exception:
        pass

    try:
        major = int(str(mongo_version).split(".")[0])
    except Exception:
        major = 0

    idx_pen = min(n_pa * 5, 30)
    # Penalize by COLLSCAN shape, not raw log volume — a busy, healthy cluster
    # always has slow-log entries; what hurts is repeated unindexed shapes.
    q_pen = min(len(collscan_shapes) * 10, 30)
    if q_pen == 0 and n_sq > 50:
        q_pen = 5
    ver_pts = 10 if major >= 8 else 5 if major == 7 else 0

    components = [
        {"label": "Status do Cluster", "earned": 20 if status == "IDLE" else 10, "max": 20,
         "detail": "IDLE = estável" if status == "IDLE" else f"Status {status} (em transição)",
         "ok": status == "IDLE"},
        {"label": "Saúde de Índices", "earned": 30 - idx_pen, "max": 30,
         "detail": "Nenhum índice sugerido pelo PA" if n_pa == 0 else f"{n_pa} índice(s) sugerido(s) pelo PA",
         "ok": n_pa == 0},
        {"label": "Saúde de Queries", "earned": 30 - q_pen, "max": 30,
         "detail": (f"{len(collscan_shapes)} shape(s) COLLSCAN em {n_sq} slow queries" if collscan_shapes
                    else f"Volume alto de slow queries ({n_sq}), sem COLLSCAN" if q_pen
                    else f"Sem COLLSCANs ({n_sq} slow queries no log)"),
         "ok": q_pen == 0},
        {"label": "Versão do MongoDB", "earned": ver_pts, "max": 10,
         "detail": f"MongoDB {mongo_version}" + ("" if major >= 8 else
                    " — 8.0 é a versão atual" if major == 7 else " — desatualizada (<7)"),
         "ok": major >= 8},
        {"label": "Base", "earned": 10, "max": 10, "detail": "pontuação base", "ok": True},
    ]
    score = sum(c["earned"] for c in components)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
    color = "#00ED64" if score >= 75 else "#FFA500" if score >= 50 else "#FF4444"
    issues = [f"{c['label']}: {c['detail']} (-{c['max'] - c['earned']} pts)"
              for c in components if not c["ok"]]

    tips = []
    if n_pa:
        tips.append({"gain": idx_pen, "text": f"Crie os {n_pa} índice(s) sugeridos no **Performance Advisor** — recupera até +{idx_pen} pts."})
    if collscan_shapes:
        tips.append({"gain": q_pen, "text": f"Elimine os {len(collscan_shapes)} shape(s) COLLSCAN (veja o **Query Profiler**) — recupera até +{q_pen} pts."})
    elif q_pen:
        tips.append({"gain": q_pen, "text": f"Volume alto de slow queries ({n_sq}) — revise no **Query Profiler** para recuperar +{q_pen} pts."})
    if major < 8:
        tips.append({"gain": 10 - ver_pts, "text": f"Atualize o MongoDB {mongo_version} → 8.0 — recupera +{10 - ver_pts} pts e melhora performance."})
    if status != "IDLE":
        tips.append({"gain": 10, "text": f"Cluster em {status} — a nota volta a +10 pts quando estabilizar em IDLE."})
    if not tips:
        tips.append({"gain": 0, "text": "Cluster já está no topo — nenhuma ação necessária. 🎉"})

    return {"score": score, "grade": grade, "color": color, "n_pa": n_pa, "n_sq": n_sq,
            "components": components, "issues": issues, "tips": tips}


@app.get("/api/finops")
def finops():
    """Evaluates cost efficiency (estimated cost vs. 24h average CPU) per cluster."""
    client = get_client()
    try:
        projects = client.get_projects()
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    work = []
    for proj in projects:
        try:
            work += [(proj, c) for c in client.get_clusters(proj["id"])]
        except Exception:
            continue

    def _tier_down(tier: str) -> Optional[str]:
        tiers = NVME_TIERS if tier.endswith("_NVME") else DEDICATED_TIERS
        i = tiers.index(tier) if tier in tiers else -1
        return tiers[i - 1] if i > 0 else None

    def evaluate(item):
        proj, c = item
        try:
            rc = c["replicationSpecs"][0]["regionConfigs"][0]
            tier = rc["electableSpecs"]["instanceSize"]
        except (KeyError, IndexError, TypeError):
            tier = "Free/Shared"
        cpu = None
        if not c.get("paused") and tier != "Free/Shared":
            pid = client.get_primary(proj["id"], c["name"])
            stats = _cpu_24h_stats(client, proj["id"], pid) if pid else None
            cpu = stats["avg"] if stats else None
        cost = AtlasClient.estimate_cost(tier, USD_BRL)
        verdict, color, savings = "sem dados", "muted", 0
        if cpu is not None:
            down = _tier_down(tier)
            if cpu < 15 and down:
                # Real saving is the delta to the next tier down — not the whole bill
                savings = cost["usd"] - AtlasClient.estimate_cost(down, USD_BRL)["usd"]
                verdict, color = f"subutilizado — avaliar {down}", "yellow"
            elif cpu > 75:
                verdict, color = "saturado — avaliar scale up", "red"
            else:
                verdict, color = "saudável — bom uso do tier", "green"
        return {"project": proj["name"], "cluster": c["name"], "tier": tier,
                "cpu": cpu, "cost_usd": cost["usd"], "cost_brl": cost["brl"],
                "verdict": verdict, "color": color, "savings_usd": savings}

    # Each cluster needs 3-4 Atlas API calls — sequential would take minutes on a real org
    with ThreadPoolExecutor(max_workers=8) as ex:
        out = list(ex.map(evaluate, work))

    return {"clusters": out, "total_usd": sum(c["cost_usd"] for c in out),
            "potential_savings_usd": sum(c["savings_usd"] for c in out)}


@app.get("/api/cluster/{project_id}/{cluster_name}/scaling")
def scaling(project_id: str, cluster_name: str, tier: str):
    client = get_client()
    pid = client.get_primary(project_id, cluster_name)
    meas = client.get_measurements(project_id, pid) if pid else {}
    cpu24 = _cpu_24h_stats(client, project_id, pid) if pid else None
    return AtlasClient.recommend_scaling(meas, tier, cpu24)


# ── Scale / Index (actions) ───────────────────────────────────────────────────
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
    project_id: Optional[str] = None
    cluster_name: Optional[str] = None

class ExplainBody(BaseModel):
    namespace: str
    filter: dict = {}
    project_id: Optional[str] = None
    cluster_name: Optional[str] = None


def _assert_uri_targets(project_id: Optional[str], cluster_name: Optional[str]):
    """409 if MONGODB_URI points to a different cluster than the one selected in
    the UI — otherwise the index/explain would silently run on the wrong cluster."""
    uri_hash = _uri_cluster_hash()
    if not (uri_hash and project_id and cluster_name):
        return
    try:
        cluster = get_client().get_cluster(project_id, cluster_name)
    except Exception:
        return
    srv_hash = _cluster_srv_hash(cluster)
    if srv_hash and srv_hash != uri_hash:
        raise HTTPException(status_code=409, detail=(
            f"MONGODB_URI aponta para outro cluster — a ação seria executada fora de "
            f"'{cluster_name}'. Ajuste o MONGODB_URI no .env do servidor."))


@app.post("/api/explain")
def explain_query(body: ExplainBody):
    """Runs a real explain('executionStats') via pymongo on the given filter."""
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise HTTPException(status_code=400, detail="MONGODB_URI não configurado no servidor.")
    _assert_uri_targets(body.project_id, body.cluster_name)
    try:
        parts = body.namespace.split(".", 1)
        db_name, coll = parts[0], (parts[1] if len(parts) > 1 else parts[0])
        mc = _mongo(uri)
        plan = mc[db_name].command("explain", {"find": coll, "filter": body.filter},
                                   verbosity="executionStats")
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
    _assert_uri_targets(body.project_id, body.cluster_name)
    return {"result": create_index_direct(uri, body.namespace, body.index_keys)}


# ── Cost / estimate ───────────────────────────────────────────────────────────
@app.get("/api/cost")
def cost(tier: str):
    return AtlasClient.estimate_cost(tier, USD_BRL)


# ── AI: analysis (stream) and chat (stream) ───────────────────────────────────
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
    conversation_id: Optional[str] = None

_chat_db_ready = False

def _ensure_chat_db(uri: str):
    """Ensures the history collection's indexes exist, once per process."""
    global _chat_db_ready
    if not _chat_db_ready:
        from chat_memory import init_db
        init_db(uri)
        _chat_db_ready = True


@app.post("/api/chat")
def chat(body: ChatBody):
    # There is ALWAYS a system prompt (MongoDB Atlas anchor) — without it the model answers generically.
    system = build_chat_system_prompt()
    if body.project_id and body.cluster_name:
        client = get_client()
        pid = client.get_primary(body.project_id, body.cluster_name)
        full_c = client.get_cluster(body.project_id, body.cluster_name)
        pa = client.get_suggested_indexes(body.project_id, pid) if pid else {}
        sq = client.get_slow_queries(body.project_id, pid) if pid else {}
        meas = client.get_measurements(body.project_id, pid) if pid else {}
        system = build_chat_system_prompt(full_c, pa, sq, meas)

    # Atlas persistence (best-effort — chat works even without MONGODB_URI)
    uri = os.getenv("MONGODB_URI", "")
    conv_id = body.conversation_id
    user_msg = body.messages[-1].get("content", "") if body.messages else ""
    if uri and user_msg:
        try:
            from chat_memory import new_conversation, add_message
            _ensure_chat_db(uri)
            if not conv_id:
                conv_id = new_conversation(uri, body.cluster_name or "")
            add_message(uri, conv_id, "user", user_msg)
        except Exception:
            conv_id = None

    def gen():
        acc = []
        try:
            for chunk in stream_chat(body.messages, system):
                acc.append(chunk)
                yield chunk
        except Exception as e:
            err = friendly_api_error(e)
            acc.append(err)
            yield err
        if uri and conv_id:
            try:
                from chat_memory import add_message
                add_message(uri, conv_id, "assistant", "".join(acc))
            except Exception:
                pass

    headers = {"X-Conversation-Id": conv_id} if conv_id else {}
    return StreamingResponse(gen(), media_type="text/plain", headers=headers)


# ── Analysis PDF report (MongoDB branding, Markdown fallback) ─────────────────
class ReportBody(BaseModel):
    cluster_name: str
    analysis: str
    health_score: Optional[int] = None
    health_issues: Optional[list] = None

@app.post("/api/report")
def report(body: ReportBody):
    data, mime, ext = generate_pdf_report(
        body.cluster_name, body.analysis, body.health_score, body.health_issues
    )
    return Response(
        content=data, media_type=mime,
        headers={"Content-Disposition": f'attachment; filename="torre-{body.cluster_name}.{ext}"'},
    )


# ── Chat history (Atlas persistence, optional) ────────────────────────────────
def _mongo_or_400():
    uri = os.getenv("MONGODB_URI", "")
    if not uri:
        raise HTTPException(status_code=400, detail="MONGODB_URI não configurado.")
    return uri

_MONGO_DOWN = "Cluster do MONGODB_URI inacessível (pausado ou IP fora da access list)."

@app.get("/api/chat/conversations")
def conversations(q: str = ""):
    uri = _mongo_or_400()
    from chat_memory import list_conversations, search_conversations
    try:
        rows = search_conversations(uri, q) if q else list_conversations(uri, limit=25)
    except Exception:
        raise HTTPException(status_code=503, detail=_MONGO_DOWN)
    return {"conversations": [
        {"id": r["id"], "title": r["title"], "cluster": r.get("cluster", ""),
         "msg_count": r.get("msg_count", 0), "updated_at": str(r.get("updated_at", ""))}
        for r in rows
    ]}

@app.get("/api/chat/conversations/{conv_id}")
def conversation_messages(conv_id: str):
    uri = _mongo_or_400()
    from chat_memory import load_messages
    try:
        msgs = load_messages(uri, conv_id)
    except Exception:
        raise HTTPException(status_code=503, detail=_MONGO_DOWN)
    return {"messages": [
        {"role": m.get("role"), "content": m.get("content"), "ts": str(m.get("ts", ""))}
        for m in msgs
    ]}

@app.delete("/api/chat/conversations/{conv_id}")
def delete_conversation_ep(conv_id: str):
    uri = _mongo_or_400()
    from chat_memory import delete_conversation
    try:
        delete_conversation(uri, conv_id)
    except Exception:
        raise HTTPException(status_code=503, detail=_MONGO_DOWN)
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
