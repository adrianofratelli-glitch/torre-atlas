import requests
from requests.auth import HTTPDigestAuth
from typing import Optional

ATLAS_BASE = "https://cloud.mongodb.com/api/atlas/v2"
ATLAS_HEADERS = {
    "Accept": "application/vnd.atlas.2024-08-05+json",
    "Content-Type": "application/vnd.atlas.2024-08-05+json",
}

DEDICATED_TIERS = ["M10","M20","M30","M40","M50","M60","M80","M140","M200","M300","M400","M700"]
NVME_TIERS      = ["M40_NVME","M50_NVME","M60_NVME","M80_NVME","M200_NVME","M400_NVME"]

# ── Estimativa de custo mensal (USD) ────────────────────────────────────────
# 3-node replica set · AWS us-east-1 · valores aproximados (atlas.mongodb.com/pricing)
# Variam por cloud provider e região — use como referência comparativa
TIER_PRICING_USD = {
    "M10":         57,
    "M20":        144,
    "M30":        389,
    "M40":        749,
    "M50":      1_440,
    "M60":      2_844,
    "M80":      5_256,
    "M140":     7_913,
    "M200":    10_505,
    "M300":    15_732,
    "M400":    21_024,
    "M700":    31_500,
    "M40_NVME":    843,
    "M50_NVME":  1_642,
    "M60_NVME":  3_276,
    "M80_NVME":  5_926,
    "M200_NVME": 11_836,
    "M400_NVME": 23_672,
    "Free/Shared":   0,
}


class AtlasClient:
    def __init__(self, public_key: str, private_key: str, org_id: str, project_id: str = ""):
        self.auth       = HTTPDigestAuth(public_key, private_key)
        self.org_id     = org_id
        self.project_id = project_id

    # ── HTTP helpers ──────────────────────────────────────────────────────
    def _get(self, path, params=None):
        r = requests.get(
            f"{ATLAS_BASE}{path}", auth=self.auth,
            headers=ATLAS_HEADERS, params=params or {}, timeout=30
        )
        r.raise_for_status()
        return r.json()

    def _patch(self, path, body):
        r = requests.patch(
            f"{ATLAS_BASE}{path}", auth=self.auth,
            headers=ATLAS_HEADERS, json=body, timeout=30
        )
        r.raise_for_status()
        return r.json()

    # ── Org / Projects ────────────────────────────────────────────────────
    def get_org(self):
        return self._get(f"/orgs/{self.org_id}")

    def get_projects(self):
        if self.project_id:
            return [self._get(f"/groups/{self.project_id}")]
        return self._get("/groups", params={"itemsPerPage": 500}).get("results", [])

    # ── Clusters ──────────────────────────────────────────────────────────
    def get_clusters(self, project_id):
        return self._get(f"/groups/{project_id}/clusters").get("results", [])

    def get_cluster(self, project_id, cluster_name):
        return self._get(f"/groups/{project_id}/clusters/{cluster_name}")

    def scale_cluster(self, project_id, cluster_name, new_tier):
        cluster   = self.get_cluster(project_id, cluster_name)
        rep_specs = cluster.get("replicationSpecs", [])
        for spec in rep_specs:
            for rc in spec.get("regionConfigs", []):
                for key in ("electableSpecs", "readOnlySpecs", "analyticsSpecs"):
                    if rc.get(key):
                        rc[key]["instanceSize"] = new_tier
        return self._patch(
            f"/groups/{project_id}/clusters/{cluster_name}",
            {"replicationSpecs": rep_specs}
        )

    # ── Processes / Primary ───────────────────────────────────────────────
    def get_processes(self, project_id):
        return self._get(f"/groups/{project_id}/processes").get("results", [])

    def get_primary(self, project_id: str, cluster_name: str) -> Optional[str]:
        """
        Encontra o processo primário usando a connectionString real do cluster.
        Necessário porque matching por nome falha para clusters com nomes genéricos
        como 'MongoDB' (aparece em todos os hostnames .mongodb.net).

        Estratégia:
        1. Busca o cluster para checar se está PAUSED (sem processos)
        2. Extrai o hash único do cluster via connectionStrings
        3. Usa esse hash para encontrar o primário exato na lista de processos
        """
        import re as _re
        try:
            cluster = self.get_cluster(project_id, cluster_name)
        except Exception:
            cluster = {}

        # Cluster pausado não tem processos ativos
        if cluster.get("paused") or cluster.get("stateName") in ("PAUSED", "DELETING", "CREATING"):
            return None

        try:
            procs = self.get_processes(project_id)
        except Exception:
            return None
        if not procs:
            return None

        primaries = [p for p in procs if p.get("typeName") == "REPLICA_PRIMARY"]
        if not primaries:
            return f"{procs[0]['hostname']}:{procs[0]['port']}"

        # Tenta extrair hash único do cluster via srvAddress ou connectionStrings
        conn = cluster.get("connectionStrings", {})
        srv  = conn.get("standardSrv", "") or cluster.get("srvAddress", "")
        # srvAddress ex: "mongodb+srv://inter.xxxxx.mongodb.net"
        # O hash "xxxxx" é único por cluster
        hash_match = _re.search(r'\.([a-z0-9]+)\.mongodb\.net', srv.lower())
        if hash_match:
            cluster_hash = hash_match.group(1)
            for p in primaries:
                if cluster_hash in p.get("hostname", "").lower():
                    return f"{p['hostname']}:{p['port']}"

        # Fallback: startswith pelo nome do cluster (funciona para nomes não-genéricos)
        cluster_lower = cluster_name.lower()
        _GENERIC = {"mongodb", "atlas", "cluster", "replica", "shard"}
        if cluster_lower not in _GENERIC:
            for p in primaries:
                if p.get("hostname", "").lower().startswith(cluster_lower):
                    return f"{p['hostname']}:{p['port']}"
            for p in primaries:
                if cluster_lower in p.get("hostname", "").lower():
                    return f"{p['hostname']}:{p['port']}"

        # Último fallback: primeiro primário disponível
        return f"{primaries[0]['hostname']}:{primaries[0]['port']}"

    # ── Disk / Storage measurements (endpoint /disks/{partition}) ─────────
    def _disk_metrics(self, project_id: str, process_id: str) -> dict:
        """Busca IOPS, latência e % de uso de storage da 1ª partição.
        Endpoint separado do de processo. Best-effort — retorna {} em falha."""
        try:
            disks = self._get(f"/groups/{project_id}/processes/{process_id}/disks").get("results", [])
            if not disks:
                return {}
            part = disks[0]["partitionName"]
            data = self._get(
                f"/groups/{project_id}/processes/{process_id}/disks/{part}/measurements",
                params={"granularity": "PT1M", "period": "PT5M", "m": [
                    "DISK_PARTITION_IOPS_READ", "DISK_PARTITION_IOPS_WRITE",
                    "DISK_PARTITION_LATENCY_READ", "DISK_PARTITION_LATENCY_WRITE",
                    "DISK_PARTITION_SPACE_PERCENT_USED",
                ]},
            )
        except Exception:
            return {}

        def _last(points):
            for p in reversed(points):
                if p.get("value") is not None:
                    return round(p["value"], 2)
            return 0

        out = {}
        for m in data.get("measurements", []):
            n = m.get("name", "")
            v = _last(m.get("dataPoints", []))
            if "IOPS_READ" in n:        out["iops_read"]  = v
            elif "IOPS_WRITE" in n:     out["iops_write"] = v
            elif "LATENCY_READ" in n:   out["lat_read"]   = v
            elif "LATENCY_WRITE" in n:  out["lat_write"]  = v
            elif "SPACE_PERCENT" in n:  out["space_pct"]  = v
        return out

    # ── Hardware Measurements ─────────────────────────────────────────────
    def get_measurements(self, project_id: str, process_id: str) -> dict:
        """
        Busca métricas de hardware do primário (janela recente de 5 min).
        Usa CPU NORMALIZADA (0–100% por core, igual ao painel Real Time do Atlas)
        e pega o último valor não-nulo de cada métrica (Atlas atrasa ~1-2 min).

        Métricas: CPU, Memória, Conexões, Disk IOPS + Latência, Rede,
        Opcounters (query/insert/update/delete/getmore/command) e Query Targeting.
        """
        # IMPORTANTE: o endpoint de PROCESSO só aceita métricas de sistema/processo.
        # Métricas DISK_PARTITION_* pertencem ao endpoint /disks/{partition} —
        # incluí-las aqui retorna 404 e derruba a chamada inteira (zera tudo).
        METRICS = [
            # CPU normalizada (preferida) + fallback não-normalizado
            "SYSTEM_NORMALIZED_CPU_USER", "SYSTEM_NORMALIZED_CPU_KERNEL",
            "SYSTEM_CPU_USER", "SYSTEM_CPU_KERNEL",
            # Memória
            "SYSTEM_MEMORY_USED", "SYSTEM_MEMORY_AVAILABLE",
            # Conexões
            "CONNECTIONS",
            # Operações
            "OPCOUNTER_INSERT", "OPCOUNTER_QUERY", "OPCOUNTER_UPDATE",
            "OPCOUNTER_DELETE", "OPCOUNTER_GETMORE", "OPCOUNTER_CMD",
            # Rede
            "NETWORK_BYTES_IN", "NETWORK_BYTES_OUT",
            # Eficiência de query (scanned/returned — quanto menor, melhor)
            "QUERY_TARGETING_SCANNED_OBJECTS_PER_RETURNED",
        ]
        try:
            data = self._get(
                f"/groups/{project_id}/processes/{process_id}/measurements",
                params={
                    "granularity": "PT1M",
                    "period":      "PT5M",
                    "m":           METRICS,
                },
            )
        except Exception as e:
            return {"error": str(e)}

        def _last_nonnull(points):
            for p in reversed(points):
                if p.get("value") is not None:
                    return p["value"]
            return None

        result = {}
        for m in data.get("measurements", []):
            name = m.get("name", "")
            val  = _last_nonnull(m.get("dataPoints", []))
            if val is not None:
                result[name] = round(val, 2)

        # CPU: prefere normalizada (0–100%), cai para não-normalizada se ausente
        cpu_user = result.get("SYSTEM_NORMALIZED_CPU_USER")
        cpu_kern = result.get("SYSTEM_NORMALIZED_CPU_KERNEL")
        if cpu_user is None and cpu_kern is None:
            cpu_user = result.get("SYSTEM_CPU_USER", 0)
            cpu_kern = result.get("SYSTEM_CPU_KERNEL", 0)

        mem_used  = result.get("SYSTEM_MEMORY_USED", 0)
        mem_avail = result.get("SYSTEM_MEMORY_AVAILABLE", 0)

        formatted = {}
        # SYSTEM_MEMORY_* vem em KB → GB = valor / 1024² (1_048_576)
        formatted["cpu_pct"]          = round((cpu_user or 0) + (cpu_kern or 0), 1)
        formatted["memory_used_gb"]   = round(mem_used  / 1_048_576, 2) if mem_used  else 0
        formatted["memory_avail_gb"]  = round(mem_avail / 1_048_576, 2) if mem_avail else 0
        formatted["mem_total_gb"]     = round((mem_used + mem_avail) / 1_048_576, 1) if (mem_used or mem_avail) else 0
        formatted["mem_pct"]          = round(mem_used / (mem_used + mem_avail) * 100, 1) if (mem_used + mem_avail) else 0
        formatted["connections"]      = int(result.get("CONNECTIONS", 0))
        # Disco/storage vêm do endpoint /disks (best-effort, não derruba se falhar)
        disk = self._disk_metrics(project_id, process_id)
        formatted["disk_iops_read"]   = disk.get("iops_read", 0)
        formatted["disk_iops_write"]  = disk.get("iops_write", 0)
        formatted["disk_lat_read"]    = disk.get("lat_read", 0)
        formatted["disk_lat_write"]   = disk.get("lat_write", 0)
        formatted["disk_pct"]         = disk.get("space_pct", 0)
        formatted["ops_insert"]       = result.get("OPCOUNTER_INSERT", 0)
        formatted["ops_query"]        = result.get("OPCOUNTER_QUERY",  0)
        formatted["ops_update"]       = result.get("OPCOUNTER_UPDATE", 0)
        formatted["ops_delete"]       = result.get("OPCOUNTER_DELETE", 0)
        formatted["ops_getmore"]      = result.get("OPCOUNTER_GETMORE", 0)
        formatted["ops_command"]      = result.get("OPCOUNTER_CMD", 0)
        formatted["net_in_mb"]        = round(result.get("NETWORK_BYTES_IN",  0) / 1_048_576, 2)
        formatted["net_out_mb"]       = round(result.get("NETWORK_BYTES_OUT", 0) / 1_048_576, 2)
        formatted["query_targeting"]  = result.get("QUERY_TARGETING_SCANNED_OBJECTS_PER_RETURNED", 0)
        formatted["_raw"]             = result
        return formatted

    # ── Hardware Measurements (time series) ───────────────────────────────
    def get_measurements_series(self, project_id: str, process_id: str,
                                period: str = "P1D", granularity: str = "PT1H") -> dict:
        """
        Busca série temporal de métricas para gráficos (default: últimas 24h, 1 ponto/h).
        Retorna estrutura pronta para plotar: timestamps + séries alinhadas.
        """
        METRICS = [
            "SYSTEM_CPU_USER", "SYSTEM_CPU_KERNEL",
            "OPCOUNTER_QUERY", "OPCOUNTER_INSERT", "OPCOUNTER_UPDATE",
            "CONNECTIONS",
        ]
        try:
            data = self._get(
                f"/groups/{project_id}/processes/{process_id}/measurements",
                params={"granularity": granularity, "period": period, "m": METRICS},
            )
        except Exception as e:
            return {"error": str(e)}

        raw = {}
        timestamps = []
        for m in data.get("measurements", []):
            name = m.get("name", "")
            pts  = m.get("dataPoints", [])
            raw[name] = [p.get("value") for p in pts]
            if not timestamps and pts:
                timestamps = [p.get("timestamp") for p in pts]

        def _combine(a, b):
            la, lb = raw.get(a, []), raw.get(b, [])
            n = max(len(la), len(lb))
            out = []
            for i in range(n):
                va = la[i] if i < len(la) and la[i] is not None else 0
                vb = lb[i] if i < len(lb) and lb[i] is not None else 0
                out.append(round(va + vb, 1))
            return out

        def _clean(name):
            return [round(v, 1) if v is not None else 0 for v in raw.get(name, [])]

        return {
            "timestamps":  timestamps,
            "cpu":         _combine("SYSTEM_CPU_USER", "SYSTEM_CPU_KERNEL"),
            "ops_query":   _clean("OPCOUNTER_QUERY"),
            "ops_insert":  _clean("OPCOUNTER_INSERT"),
            "ops_update":  _clean("OPCOUNTER_UPDATE"),
            "connections": _clean("CONNECTIONS"),
        }

    # ── Scaling recommendation (heuristic, based on real metrics) ─────────
    # Limite aproximado de conexões por tier (Atlas docs)
    TIER_CONN_LIMIT = {
        "M10": 1500, "M20": 3000, "M30": 3000, "M40": 6000, "M50": 16000,
        "M60": 32000, "M80": 64000, "M140": 96000, "M200": 128000,
        "M300": 128000, "M400": 128000, "M700": 128000,
        "M40_NVME": 6000, "M50_NVME": 16000, "M60_NVME": 32000,
        "M80_NVME": 64000, "M200_NVME": 128000, "M400_NVME": 128000,
    }

    @staticmethod
    def recommend_scaling(measurements: dict, tier: str) -> dict:
        """
        Recomenda scaling com base nas métricas reais de hardware.
        Retorna {"action": "up"|"down"|"ok", "severity": "high"|"med"|"low",
                 "reasons": [str], "headline": str}.
        """
        if not measurements or "error" in measurements:
            return {"action": "ok", "severity": "low", "reasons": [], "headline": ""}

        cpu      = measurements.get("cpu_pct", 0)
        conns    = measurements.get("connections", 0)
        iops     = measurements.get("disk_iops_read", 0) + measurements.get("disk_iops_write", 0)
        mem_pct  = measurements.get("mem_pct", 0)
        disk_pct = measurements.get("disk_pct", 0)
        conn_limit = AtlasClient.TIER_CONN_LIMIT.get(tier, 1500)
        conn_pct   = (conns / conn_limit * 100) if conn_limit else 0

        reasons, action, severity = [], "ok", "low"

        # ── CPU ──
        if cpu >= 80:
            action, severity = "up", "high"
            reasons.append(f"CPU em **{cpu}%** — acima de 80%, gargalo de processamento")
        elif cpu >= 65:
            action, severity = "up", "med"
            reasons.append(f"CPU em **{cpu}%** — aproximando do limite (65%+)")

        # ── Memória (pressão de cache WiredTiger) ──
        if mem_pct >= 90:
            action, severity = "up", "high"
            reasons.append(f"Memória em **{mem_pct}%** — working set não cabe na RAM, pressão de cache WiredTiger")
        elif mem_pct >= 75:
            if action != "up":
                action, severity = "up", "med"
            reasons.append(f"Memória em **{mem_pct}%** — aproximando do limite, risco de page faults em disco")

        # ── Storage (uso de disco) ──
        if disk_pct >= 85:
            action, severity = "up", "high"
            reasons.append(f"Storage em **{disk_pct}%** — risco de esgotar disco; expanda o tier")
        elif disk_pct >= 70:
            if action != "up":
                action, severity = "up", "med"
            reasons.append(f"Storage em **{disk_pct}%** — planeje expansão de disco")

        # ── Conexões ──
        if conn_pct >= 80:
            action, severity = "up", "high"
            reasons.append(f"Conexões em **{conns}** ({conn_pct:.0f}% do limite do {tier})")
        elif conn_pct >= 60:
            if action != "up":
                action, severity = "up", "med"
            reasons.append(f"Conexões em **{conns}** ({conn_pct:.0f}% do limite do {tier})")

        # ── Disco I/O ──
        if iops >= 3000 and "_NVME" not in tier:
            if action != "up":
                action, severity = "up", "med"
            reasons.append(f"Disco em **{iops:.0f} IOPS** — avalie tier NVMe para I/O intensivo")

        # ── Scale DOWN: subutilização clara nas 3 métricas-chave ──
        if (action == "ok" and cpu < 15 and conn_pct < 20
                and mem_pct < 50 and disk_pct < 50 and tier != "M10"):
            action, severity = "down", "low"
            reasons.append(f"CPU **{cpu}%**, memória **{mem_pct}%**, disco **{disk_pct}%** — "
                           "tudo baixo, possível economia de custo")

        headlines = {
            "up":   "⬆️ Recomendação: Scale UP",
            "down": "⬇️ Oportunidade: Scale DOWN (economia)",
            "ok":   "✅ Tier adequado para a carga atual",
        }
        if action == "ok" and not reasons:
            reasons.append(f"CPU **{cpu}%**, memória **{mem_pct}%**, storage **{disk_pct}%** — "
                           "tudo saudável, nenhuma ação necessária")

        return {"action": action, "severity": severity,
                "reasons": reasons, "headline": headlines[action],
                # métricas-chave p/ a UI exibir (CPU · Memória · Storage · Conexões)
                "metrics": {
                    "cpu_pct": cpu, "mem_pct": mem_pct, "disk_pct": disk_pct,
                    "connections": conns, "conn_pct": round(conn_pct, 1),
                    "memory_used_gb": measurements.get("memory_used_gb", 0),
                    "mem_total_gb": measurements.get("mem_total_gb", 0),
                    "iops": round(iops),
                }}

    # ── Performance Advisor ───────────────────────────────────────────────
    def get_suggested_indexes(self, project_id, process_id):
        return self._get(
            f"/groups/{project_id}/processes/{process_id}/performanceAdvisor/suggestedIndexes"
        )

    def get_slow_queries(self, project_id, process_id):
        return self._get(
            f"/groups/{project_id}/processes/{process_id}/performanceAdvisor/slowQueryLogs"
        )

    # ── Alerts ────────────────────────────────────────────────────────────
    def get_open_alerts(self, project_id):
        try:
            return self._get(
                f"/groups/{project_id}/alerts", params={"status": "OPEN"}
            ).get("results", [])
        except Exception:
            return []

    # ── Invoice ───────────────────────────────────────────────────────────
    def get_pending_invoice(self):
        try:
            return self._get(f"/orgs/{self.org_id}/invoices/pending")
        except Exception:
            return {}

    # ── Cost estimation (static, no API call) ─────────────────────────────
    @staticmethod
    def estimate_cost(tier: str, usd_brl: float = 5.70) -> dict:
        usd = TIER_PRICING_USD.get(tier, 0)
        return {
            "tier": tier,
            "usd": usd,
            "brl": round(usd * usd_brl),
        }


# ── Direct pymongo index creation (requires connection string) ─────────────
def create_index_direct(mongo_uri: str, namespace: str, index_keys: list) -> str:
    """Creates an index directly via pymongo. Retries once on replica state change."""
    try:
        from pymongo import MongoClient
        from pymongo.errors import OperationFailure
        parts     = namespace.split(".", 1)
        db_name   = parts[0]
        coll_name = parts[1] if len(parts) > 1 else parts[0]
        keys      = [(list(k.keys())[0], int(list(k.values())[0])) for k in index_keys]
        mc        = MongoClient(mongo_uri, serverSelectionTimeoutMS=6000)

        for attempt in range(2):
            try:
                name = mc[db_name][coll_name].create_index(keys)
                mc.close()
                return f"✅ Índice criado: `{name}`"
            except OperationFailure as e:
                if e.code == 11602 and attempt == 0:
                    # Primary election in progress — wait and retry once
                    import time; time.sleep(3)
                    continue
                mc.close()
                return (
                    f"❌ Erro MongoDB ({e.code}): {e.details.get('errmsg', str(e))}\n\n"
                    f"**Dica:** O cluster pode estar em processo de eleição de primário. "
                    f"Aguarde ~30s e tente novamente."
                )
        mc.close()
        return "❌ Falha após retry. Tente novamente em alguns instantes."
    except ImportError:
        return "❌ pymongo não instalado. Execute: pip install pymongo"
    except Exception as e:
        return f"❌ Erro de conexão: {e}"
