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

    # ── Hardware Measurements ─────────────────────────────────────────────
    def get_measurements(self, project_id: str, process_id: str) -> dict:
        """
        Busca métricas de hardware do primário nos últimos 5 minutos.
        Retorna o último valor de cada métrica em formato legível.
        Métricas: CPU, Memória, Disk IOPS, Conexões, Opcounters.
        """
        METRICS = [
            "SYSTEM_CPU_USER",
            "SYSTEM_CPU_KERNEL",
            "SYSTEM_MEMORY_USED",
            "SYSTEM_MEMORY_AVAILABLE",
            "DISK_PARTITION_IOPS_READ",
            "DISK_PARTITION_IOPS_WRITE",
            "CONNECTIONS",
            "OPCOUNTER_INSERT",
            "OPCOUNTER_QUERY",
            "OPCOUNTER_UPDATE",
            "OPCOUNTER_DELETE",
            "NETWORK_BYTES_IN",
            "NETWORK_BYTES_OUT",
        ]
        try:
            data = self._get(
                f"/groups/{project_id}/processes/{process_id}/measurements",
                params={
                    "granularity": "PT1M",
                    "period":      "PT10M",
                    "m":           METRICS,
                },
            )
        except Exception as e:
            return {"error": str(e)}

        result = {}
        for m in data.get("measurements", []):
            name   = m.get("name", "")
            points = [p["value"] for p in m.get("dataPoints", []) if p.get("value") is not None]
            if points:
                result[name] = round(points[-1], 2)

        # Formata em algo legível para o sistema prompt do Claude
        formatted = {}
        cpu_user   = result.get("SYSTEM_CPU_USER", 0)
        cpu_kernel = result.get("SYSTEM_CPU_KERNEL", 0)
        mem_used   = result.get("SYSTEM_MEMORY_USED", 0)
        mem_avail  = result.get("SYSTEM_MEMORY_AVAILABLE", 0)

        formatted["cpu_pct"]          = round(cpu_user + cpu_kernel, 1)
        formatted["memory_used_gb"]   = round(mem_used   / 1024, 2) if mem_used   else 0
        formatted["memory_avail_gb"]  = round(mem_avail  / 1024, 2) if mem_avail  else 0
        formatted["disk_iops_read"]   = result.get("DISK_PARTITION_IOPS_READ",  0)
        formatted["disk_iops_write"]  = result.get("DISK_PARTITION_IOPS_WRITE", 0)
        formatted["connections"]      = int(result.get("CONNECTIONS", 0))
        formatted["ops_insert"]       = result.get("OPCOUNTER_INSERT", 0)
        formatted["ops_query"]        = result.get("OPCOUNTER_QUERY",  0)
        formatted["ops_update"]       = result.get("OPCOUNTER_UPDATE", 0)
        formatted["ops_delete"]       = result.get("OPCOUNTER_DELETE", 0)
        formatted["net_in_mb"]        = round(result.get("NETWORK_BYTES_IN",  0) / 1_048_576, 2)
        formatted["net_out_mb"]       = round(result.get("NETWORK_BYTES_OUT", 0) / 1_048_576, 2)
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

        cpu   = measurements.get("cpu_pct", 0)
        conns = measurements.get("connections", 0)
        iops  = measurements.get("disk_iops_read", 0) + measurements.get("disk_iops_write", 0)
        conn_limit = AtlasClient.TIER_CONN_LIMIT.get(tier, 1500)
        conn_pct   = (conns / conn_limit * 100) if conn_limit else 0

        reasons, action, severity = [], "ok", "low"

        if cpu >= 80:
            action, severity = "up", "high"
            reasons.append(f"CPU em **{cpu}%** — acima de 80%, gargalo de processamento")
        elif cpu >= 65:
            action, severity = "up", "med"
            reasons.append(f"CPU em **{cpu}%** — aproximando do limite (65%+)")

        if conn_pct >= 80:
            action, severity = "up", "high"
            reasons.append(f"Conexões em **{conns}** ({conn_pct:.0f}% do limite do {tier})")
        elif conn_pct >= 60:
            if action != "up":
                action, severity = "up", "med"
            reasons.append(f"Conexões em **{conns}** ({conn_pct:.0f}% do limite do {tier})")

        if iops >= 3000 and "_NVME" not in tier:
            if action != "up":
                action, severity = "up", "med"
            reasons.append(f"Disco em **{iops:.0f} IOPS** — avalie tier NVMe para I/O intensivo")

        # Scale DOWN: subutilização clara
        if action == "ok" and cpu < 15 and conn_pct < 20 and tier != "M10":
            action, severity = "down", "low"
            reasons.append(f"CPU em **{cpu}%** e conexões baixas — possível economia de custo")

        headlines = {
            "up":   "⬆️ Recomendação: Scale UP",
            "down": "⬇️ Oportunidade: Scale DOWN (economia)",
            "ok":   "✅ Tier adequado para a carga atual",
        }
        if action == "ok" and not reasons:
            reasons.append(f"CPU em **{cpu}%**, conexões saudáveis — nenhuma ação necessária")

        return {"action": action, "severity": severity,
                "reasons": reasons, "headline": headlines[action]}

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
