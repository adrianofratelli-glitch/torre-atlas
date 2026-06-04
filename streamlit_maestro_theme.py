"""
streamlit_maestro_theme.py — MongoDB Atlas styled cluster table component.
Used by app.py for the Clusters tab. Theme CSS lives inline in app.py.
"""

import streamlit as st


def maestro_cluster_table(clusters: list[dict]):
    """
    clusters = [
        {
            "projeto": "POC Inter - Cartões",
            "cluster": "inter",
            "tier": "M20",
            "regiao": "US_EAST_1",
            "status": "IDLE",   # IDLE | RUNNING | PAUSED | ERROR
            "mongodb": "8.0.24",
            "tipo": "REPLICASET",
            "usd": "$144",
            "brl": "R$821",
        },
        ...
    ]
    """
    status_colors = {
        "IDLE":    ("#00ED64", "rgba(0,237,100,0.1)"),
        "RUNNING": ("#22D3EE", "rgba(34,211,238,0.1)"),
        "PAUSED":  ("#FACC15", "rgba(250,204,21,0.1)"),
        "ERROR":   ("#F87171", "rgba(248,113,113,0.1)"),
    }

    rows_html = ""
    for c in clusters:
        sc, sbg = status_colors.get(c.get("status", "IDLE"), ("#7D8FA3", "rgba(125,143,163,0.1)"))
        rows_html += f"""
        <tr style="border-bottom:1px solid rgba(255,255,255,0.04);transition:background 0.12s;"
            onmouseover="this.style.background='rgba(255,255,255,0.02)'"
            onmouseout="this.style.background='transparent'">
            <td style="padding:11px 14px;font-size:13px;color:#E2E8F0;">{c.get('projeto','')}</td>
            <td style="padding:11px 14px;font-size:12px;font-family:'IBM Plex Mono',monospace;color:#00ED64;">{c.get('cluster','')}</td>
            <td style="padding:11px 14px;">
                <span style="font-size:11px;font-weight:600;
                    background:rgba(96,165,250,0.1);color:#60A5FA;
                    border:1px solid rgba(96,165,250,0.2);
                    padding:2px 8px;border-radius:4px;
                    font-family:'IBM Plex Mono',monospace;">{c.get('tier','')}</span>
            </td>
            <td style="padding:11px 14px;font-size:12px;font-family:'IBM Plex Mono',monospace;color:#7D8FA3;">{c.get('regiao','')}</td>
            <td style="padding:11px 14px;">
                <span style="display:inline-flex;align-items:center;gap:5px;
                    font-size:11px;font-weight:600;
                    background:{sbg};color:{sc};
                    border:1px solid {sc}33;
                    padding:3px 8px;border-radius:4px;">
                    <span style="width:5px;height:5px;border-radius:50%;background:{sc};
                        box-shadow:0 0 5px {sc};display:inline-block;
                        animation:pulse 2s ease-in-out infinite;"></span>
                    {c.get('status','')}
                </span>
            </td>
            <td style="padding:11px 14px;font-size:12px;font-family:'IBM Plex Mono',monospace;color:#7D8FA3;">{c.get('mongodb','')}</td>
            <td style="padding:11px 14px;font-size:12px;font-family:'IBM Plex Mono',monospace;color:#7D8FA3;">{c.get('tipo','')}</td>
            <td style="padding:11px 14px;font-size:12px;font-family:'IBM Plex Mono',monospace;color:#E2E8F0;text-align:right;">
                {c.get('usd','')} <span style="color:#3A4556;">/</span>
                <span style="color:#00ED64;">{c.get('brl','')}</span>
            </td>
        </tr>"""

    st.markdown(f"""
    <style>@keyframes pulse{{0%,100%{{opacity:1}}50%{{opacity:0.4}}}}</style>
    <div style="
        background:#131920;border:1px solid rgba(255,255,255,0.05);
        border-radius:8px;overflow:hidden;margin-bottom:16px;">
        <table style="width:100%;border-collapse:collapse;">
            <thead>
                <tr style="background:#0D1117;border-bottom:1px solid rgba(255,255,255,0.07);">
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;
                        font-family:'IBM Plex Sans',sans-serif;">Projeto</th>
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">Cluster</th>
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">Tier</th>
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">Região</th>
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">Status</th>
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">MongoDB</th>
                    <th style="padding:10px 14px;text-align:left;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">Tipo</th>
                    <th style="padding:10px 14px;text-align:right;font-size:10px;font-weight:600;
                        color:#3A4556;text-transform:uppercase;letter-spacing:0.09em;">💰 Est. Mensal</th>
                </tr>
            </thead>
            <tbody>{rows_html}</tbody>
        </table>
    </div>
    """, unsafe_allow_html=True)
