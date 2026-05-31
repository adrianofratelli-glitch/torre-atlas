"""
ai_agent.py — Claude-powered MongoDB analysis + conversational chat
"""

import json
import anthropic
from typing import Iterator

MODEL = "claude-haiku-4-5-20251001"


# ══════════════════════════════════════════════════════════════════════════════
# ONE-SHOT ANALYSIS (original, mantido)
# ══════════════════════════════════════════════════════════════════════════════

def _build_analysis_prompt(cluster: dict, pa_data: dict, slow_queries: dict) -> str:
    tier = region = "N/A"
    try:
        rc     = cluster["replicationSpecs"][0]["regionConfigs"][0]
        tier   = rc["electableSpecs"]["instanceSize"]
        region = rc["regionName"]
    except (KeyError, IndexError, TypeError):
        pass

    suggestions = pa_data.get("suggestedIndexes", [])
    slow_qs     = slow_queries.get("slowQueries", [])

    return f"""Você é um DBA especialista em MongoDB com foco em performance para aplicações financeiras de alto volume no Brasil.

## Cluster analisado
- **Nome:** {cluster.get('name', 'N/A')}
- **Tier:** {tier}
- **Região:** {region}
- **Status:** {cluster.get('stateName', 'N/A')}
- **Versão:** {cluster.get('mongoDBVersion', 'N/A')}

## Performance Advisor — {len(suggestions)} índice(s) sugerido(s)
```json
{json.dumps(suggestions[:5], indent=2)[:4000]}
```

## Slow Queries — {len(slow_qs)} registros
```json
{json.dumps(slow_qs[:10], indent=2)[:3000]}
```

---
Análise **técnica e direta**. Estruture assim:

### 🔴 Problemas Críticos
Os 3 de maior impacto, com latência estimada e operações afetadas.

### 🟡 Ações Recomendadas
Para cada problema: ação específica + comando MongoDB quando aplicável + impacto esperado.

### 🟢 Quick Wins
Ações executáveis em menos de 1 hora, sem risco de downtime.

### 📊 Veredicto de Scaling
O tier **{tier}** é adequado? Se não, qual tier recomendar e por quê (critério técnico).

Máximo 600 palavras. Foque em impacto de negócio."""


def analyze_cluster_stream(cluster: dict, pa_data: dict, slow_queries: dict) -> Iterator[str]:
    """Streams a one-shot performance analysis."""
    client = anthropic.Anthropic()
    with client.messages.stream(
        model=MODEL,
        max_tokens=1500,
        messages=[{"role": "user", "content": _build_analysis_prompt(cluster, pa_data, slow_queries)}],
    ) as stream:
        for text in stream.text_stream:
            yield text


# ══════════════════════════════════════════════════════════════════════════════
# CONVERSATIONAL CHAT
# ══════════════════════════════════════════════════════════════════════════════

def build_chat_system_prompt(
    cluster_data: dict = None,
    pa_data: dict = None,
    slow_queries: dict = None,
    measurements: dict = None,
) -> str:
    base = (
        "Você é um DBA especialista em MongoDB e Solutions Architect, especializado em "
        "aplicações financeiras de alto volume no Brasil.\n"
        "Responda de forma técnica e objetiva. Use markdown para formatar.\n"
        "Quando relevante, forneça comandos MongoDB prontos para execução.\n"
        "Foque em impacto de negócio ao explicar problemas técnicos.\n\n"
        "REGRAS CRÍTICAS:\n"
        "- Use APENAS os dados reais fornecidos neste contexto. NUNCA invente métricas, índices ou queries.\n"
        "- O acesso à API é COMPLETO. NUNCA mencione 'permissões limitadas' ou 'API Key restrita' — "
        "se um campo estiver vazio (ex: 0 sugestões do PA), é porque realmente não há sugestões, não é falta de permissão.\n"
        "- Se suggestedIndexes tiver 0 itens: informe claramente que o PA não encontrou oportunidades de indexação "
        "e analise as slow queries para propor índices baseados nos padrões de acesso REAIS observados.\n"
        "- Se slowQueries tiver dados: analise os namespaces, planSummary e durationMillis reais.\n"
        "- Distingua sempre: '**dados reais da API**' vs '**recomendação baseada em padrões**'.\n"
    )

    if not cluster_data:
        return base

    tier = region = "N/A"
    try:
        rc     = cluster_data["replicationSpecs"][0]["regionConfigs"][0]
        tier   = rc["electableSpecs"]["instanceSize"]
        region = rc["regionName"]
    except (KeyError, IndexError, TypeError):
        pass

    ctx = (
        f"\n\n## Contexto: Cluster `{cluster_data.get('name', 'N/A')}`\n"
        f"- Tier: **{tier}** | Região: {region}\n"
        f"- Status: {cluster_data.get('stateName', 'N/A')} | MongoDB: {cluster_data.get('mongoDBVersion', 'N/A')}\n"
    )

    # ── Métricas de hardware (últimos 10min) ──
    if measurements and "error" not in measurements:
        cpu   = measurements.get("cpu_pct", 0)
        m_use = measurements.get("memory_used_gb", 0)
        m_av  = measurements.get("memory_avail_gb", 0)
        conns = measurements.get("connections", 0)
        iops_r = measurements.get("disk_iops_read", 0)
        iops_w = measurements.get("disk_iops_write", 0)
        ops_q  = measurements.get("ops_query", 0)
        ops_i  = measurements.get("ops_insert", 0)
        ops_u  = measurements.get("ops_update", 0)
        net_in  = measurements.get("net_in_mb", 0)
        net_out = measurements.get("net_out_mb", 0)

        ctx += (
            f"\n### Métricas de Hardware (últimos 10 min)\n"
            f"| Métrica | Valor |\n|---|---|\n"
            f"| CPU (user+kernel) | **{cpu}%** |\n"
            f"| Memória usada | **{m_use} GB** |\n"
            f"| Memória disponível | **{m_av} GB** |\n"
            f"| Conexões ativas | **{conns}** |\n"
            f"| Disk IOPS Read | **{iops_r}** |\n"
            f"| Disk IOPS Write | **{iops_w}** |\n"
            f"| Queries/s | **{ops_q}** |\n"
            f"| Inserts/s | **{ops_i}** |\n"
            f"| Updates/s | **{ops_u}** |\n"
            f"| Network In | **{net_in} MB/s** |\n"
            f"| Network Out | **{net_out} MB/s** |\n"
        )
    else:
        ctx += "- Métricas de hardware: não disponíveis (verifique permissões da API Key)\n"

    if pa_data:
        suggestions = pa_data.get("suggestedIndexes", [])
        ctx += f"\n### Performance Advisor\n- **{len(suggestions)}** índice(s) sugerido(s)\n"
        if suggestions:
            ctx += f"```json\n{json.dumps(suggestions[:3], indent=2)[:2000]}\n```\n"

    if slow_queries:
        slow_qs = slow_queries.get("slowQueries", [])
        ctx += f"\n### Slow Queries\n- **{len(slow_qs)}** registrada(s)\n"
        if slow_qs:
            ctx += f"```json\n{json.dumps(slow_qs[:5], indent=2)[:1500]}\n```\n"

    return base + ctx


def stream_chat(messages: list, system_prompt: str = "") -> Iterator[str]:
    """Streams a conversational Claude response with full history."""
    client = anthropic.Anthropic()
    kwargs = dict(model=MODEL, max_tokens=2000, messages=messages)
    if system_prompt:
        kwargs["system"] = system_prompt
    with client.messages.stream(**kwargs) as stream:
        for text in stream.text_stream:
            yield text


# ══════════════════════════════════════════════════════════════════════════════
# PDF EXPORT
# ══════════════════════════════════════════════════════════════════════════════

def generate_pdf_report(
    cluster_name: str,
    analysis_text: str,
    health_score: int = None,
    health_issues: list = None,
) -> bytes:
    """
    Gera um relatório Markdown (.md) pronto para download.
    Markdown é mais confiável que PDF para conteúdo técnico com
    nomes de campos longos, hashes e blocos de código MongoDB.
    """
    from datetime import datetime

    lines = [
        f"# Maestro — Atlas Report",
        f"**Cluster:** `{cluster_name}`  ",
        f"**Data:** {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        "",
    ]

    if health_score is not None:
        lines += [f"## Health Score: {health_score}/100", ""]
        if health_issues:
            for issue in health_issues:
                lines.append(f"- {issue}")
            lines.append("")

    lines += ["---", "", analysis_text]

    content = "\n".join(lines)
    return content.encode("utf-8")
