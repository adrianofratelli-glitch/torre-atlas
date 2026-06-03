"""
Maestro — Atlas Control Plane V2.0
Streamlit Theme Injector
Cole inject_maestro_theme() logo após st.set_page_config() no seu app.py
"""

import streamlit as st


def inject_maestro_theme():
    st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap" rel="stylesheet">
    <style>

    :root {
        --bg-void:    #080B10;
        --bg-surface: #0D1117;
        --bg-card:    #131920;
        --bg-card2:   #161E28;
        --bg-input:   #0A0E14;
        --border-subtle: rgba(255,255,255,0.05);
        --border-mid:    rgba(255,255,255,0.09);
        --border-strong: rgba(255,255,255,0.14);
        --green:      #00ED64;
        --green-dim:  rgba(0,237,100,0.08);
        --green-glow: rgba(0,237,100,0.15);
        --green-border: rgba(0,237,100,0.25);
        --cyan:       #22D3EE;
        --cyan-dim:   rgba(34,211,238,0.08);
        --yellow:     #FACC15;
        --yellow-dim: rgba(250,204,21,0.08);
        --red:        #F87171;
        --red-dim:    rgba(248,113,113,0.08);
        --blue:       #60A5FA;
        --blue-dim:   rgba(96,165,250,0.08);
        --text-primary:   #E2E8F0;
        --text-secondary: #7D8FA3;
        --text-muted:     #3A4556;
        --font: 'IBM Plex Sans', sans-serif;
        --mono: 'IBM Plex Mono', monospace;
    }

    .stApp {
        background: var(--bg-void) !important;
        font-family: var(--font) !important;
        color: var(--text-primary) !important;
    }

    #MainMenu, footer, header { visibility: hidden !important; }
    .block-container {
        padding-top: 0 !important;
        padding-bottom: 2rem !important;
        max-width: 1400px !important;
    }

    /* ── SIDEBAR ── */
    section[data-testid="stSidebar"] {
        background: var(--bg-surface) !important;
        border-right: 1px solid var(--border-subtle) !important;
    }
    section[data-testid="stSidebar"] * {
        font-family: var(--font) !important;
        color: var(--text-secondary) !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: var(--text-primary) !important;
        font-size: 12px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.09em !important;
    }

    /* ── TYPOGRAPHY ── */
    h1, h2, h3, h4 {
        font-family: var(--font) !important;
        color: var(--text-primary) !important;
    }
    p, label, span { font-family: var(--font) !important; }

    /* ── TEXT INPUT ── */
    .stTextInput > div > div > input {
        background: var(--bg-input) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        font-family: var(--mono) !important;
        font-size: 12px !important;
        padding: 8px 12px !important;
        transition: border-color 0.15s !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: var(--green) !important;
        box-shadow: 0 0 0 2px var(--green-glow) !important;
    }
    .stTextInput > div > div > input[type="password"] {
        letter-spacing: 0.2em !important;
    }

    /* ── SELECTBOX ── */
    .stSelectbox > div > div {
        background: var(--bg-input) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 6px !important;
        color: var(--text-primary) !important;
        font-family: var(--font) !important;
        font-size: 13px !important;
    }
    [data-baseweb="popover"] ul li {
        background: var(--bg-card) !important;
        color: var(--text-primary) !important;
        font-family: var(--font) !important;
        font-size: 13px !important;
    }
    [data-baseweb="popover"] ul li:hover {
        background: var(--bg-card2) !important;
    }

    /* ── BUTTONS ── */
    .stButton > button {
        background: transparent !important;
        color: var(--text-secondary) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 6px !important;
        font-family: var(--font) !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 7px 16px !important;
        transition: all 0.12s !important;
    }
    .stButton > button:hover {
        border-color: var(--green-border) !important;
        color: var(--green) !important;
        background: var(--green-dim) !important;
    }
    /* Primary */
    .stButton.primary > button {
        background: var(--green) !important;
        color: #080B10 !important;
        border-color: var(--green) !important;
        font-weight: 600 !important;
    }
    .stButton.primary > button:hover {
        background: #00C74E !important;
        box-shadow: 0 2px 12px var(--green-glow) !important;
    }

    /* ── TABS ── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--bg-surface) !important;
        border-bottom: 1px solid var(--border-subtle) !important;
        gap: 0 !important;
        padding: 0 4px !important;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent !important;
        color: var(--text-muted) !important;
        font-family: var(--font) !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        border-bottom: 2px solid transparent !important;
        padding: 10px 14px !important;
        transition: all 0.12s !important;
        letter-spacing: 0.01em !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-secondary) !important;
    }
    .stTabs [aria-selected="true"] {
        color: var(--green) !important;
        border-bottom-color: var(--green) !important;
        background: transparent !important;
    }
    .stTabs [data-baseweb="tab-panel"] {
        padding-top: 20px !important;
    }

    /* ── METRICS ── */
    [data-testid="metric-container"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        padding: 14px 16px !important;
    }
    [data-testid="metric-container"] label {
        font-size: 10px !important;
        font-weight: 600 !important;
        color: var(--text-muted) !important;
        text-transform: uppercase !important;
        letter-spacing: 0.09em !important;
        font-family: var(--font) !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-family: var(--mono) !important;
        font-size: 26px !important;
        font-weight: 500 !important;
        color: var(--text-primary) !important;
    }

    /* ── DATAFRAME / TABLE ── */
    .stDataFrame {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        overflow: hidden !important;
    }
    .stDataFrame thead th {
        background: var(--bg-surface) !important;
        color: var(--text-muted) !important;
        font-size: 10px !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.09em !important;
        border-bottom: 1px solid var(--border-mid) !important;
        padding: 10px 12px !important;
        font-family: var(--font) !important;
    }
    .stDataFrame tbody td {
        color: var(--text-secondary) !important;
        font-family: var(--mono) !important;
        font-size: 12px !important;
        border-color: var(--border-subtle) !important;
        padding: 9px 12px !important;
    }
    .stDataFrame tbody tr:hover td {
        background: rgba(255,255,255,0.02) !important;
    }

    /* ── EXPANDER ── */
    .streamlit-expanderHeader {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        color: var(--text-secondary) !important;
        font-family: var(--mono) !important;
        font-size: 11px !important;
    }
    .streamlit-expanderContent {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-top: none !important;
        border-radius: 0 0 6px 6px !important;
    }

    /* ── CHART AREA ── */
    [data-testid="stVegaLiteChart"],
    [data-testid="stArrowVegaLiteChart"],
    [data-testid="stPlotlyChart"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        padding: 12px !important;
    }

    /* ── DIVIDER ── */
    hr {
        border: none !important;
        border-top: 1px solid var(--border-subtle) !important;
    }

    /* ── SCROLLBAR ── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: var(--border-mid); border-radius: 2px; }

    /* ── SPINNER ── */
    .stSpinner > div { border-top-color: var(--green) !important; }

    /* ── ALERTS ── */
    .stSuccess {
        background: var(--green-dim) !important;
        border: 1px solid var(--green-border) !important;
        border-radius: 6px !important;
        color: var(--green) !important;
    }
    .stWarning {
        background: var(--yellow-dim) !important;
        border: 1px solid rgba(250,204,21,0.25) !important;
        border-radius: 6px !important;
        color: var(--yellow) !important;
    }
    .stError {
        background: var(--red-dim) !important;
        border: 1px solid rgba(248,113,113,0.25) !important;
        border-radius: 6px !important;
        color: var(--red) !important;
    }
    .stInfo {
        background: var(--blue-dim) !important;
        border: 1px solid rgba(96,165,250,0.25) !important;
        border-radius: 6px !important;
        color: var(--blue) !important;
    }

    /* ── CHAT (aba AI Chat) ── */
    [data-testid="stChatMessage"] {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 8px !important;
        padding: 14px !important;
        margin-bottom: 8px !important;
    }
    [data-testid="stChatInput"] textarea {
        background: var(--bg-input) !important;
        border: 1px solid var(--border-mid) !important;
        border-radius: 8px !important;
        color: var(--text-primary) !important;
        font-family: var(--font) !important;
        font-size: 13px !important;
    }
    [data-testid="stChatInput"] button {
        background: var(--green) !important;
        border-radius: 6px !important;
    }

    /* ── CODE / JSON ── */
    pre, code, .stJson {
        background: var(--bg-card) !important;
        border: 1px solid var(--border-subtle) !important;
        border-radius: 6px !important;
        font-family: var(--mono) !important;
        font-size: 11px !important;
        color: var(--green) !important;
    }

    </style>
    """, unsafe_allow_html=True)


# ── COMPONENTES HELPER ──────────────────────────────────────────────────────

def maestro_topbar(org_name: str = "", cluster_count: int = 0, last_update: str = ""):
    st.markdown(f"""
    <div style="
        background:#0D1117;
        border-bottom:1px solid rgba(255,255,255,0.05);
        padding:14px 0 12px;
        margin-bottom:0;
        display:flex; align-items:center; justify-content:space-between;
    ">
        <div style="display:flex; align-items:center; gap:12px;">
            <div style="display:flex; align-items:center; gap:8px;">
                <span style="font-size:18px;">🎼</span>
                <div>
                    <div style="
                        font-family:'IBM Plex Sans',sans-serif;
                        font-size:18px; font-weight:600;
                        color:#E2E8F0; line-height:1.2;">
                        Maestro
                        <span style="color:#00ED64;"> — Atlas Control Plane</span>
                    </div>
                    <div style="
                        font-size:10px; color:#3A4556;
                        font-family:'IBM Plex Mono',monospace;
                        letter-spacing:0.05em; margin-top:1px;">
                        Org: {org_name} · {cluster_count} cluster(s) · atualizado {last_update}
                    </div>
                </div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


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


def maestro_metric_card(label: str, value: str, color: str = "default",
                        badge: str = "", sub: str = ""):
    color_map = {
        "green":   "#00ED64",
        "yellow":  "#FACC15",
        "red":     "#F87171",
        "cyan":    "#22D3EE",
        "blue":    "#60A5FA",
        "default": "#E2E8F0",
    }
    hl = color == "green"
    border = "rgba(0,237,100,0.2)" if hl else "rgba(255,255,255,0.05)"
    bg     = "linear-gradient(135deg,rgba(0,237,100,0.04) 0%,#131920 60%)" if hl else "#131920"

    badge_html = f"""<span style="
        position:absolute;top:8px;right:8px;
        font-size:9px;font-weight:600;padding:2px 6px;border-radius:3px;
        background:rgba(250,204,21,0.1);color:#FACC15;
        border:1px solid rgba(250,204,21,0.2);
        text-transform:uppercase;letter-spacing:0.06em;">{badge}</span>""" if badge else ""

    st.markdown(f"""
    <div style="
        background:{bg};border:1px solid {border};
        border-radius:8px;padding:14px 16px;
        position:relative;transition:border-color 0.15s;">
        {badge_html}
        <div style="font-size:10px;color:#3A4556;text-transform:uppercase;
                    letter-spacing:0.09em;font-weight:600;margin-bottom:5px;
                    font-family:'IBM Plex Sans',sans-serif;">{label}</div>
        <div style="font-size:26px;font-weight:500;color:{color_map[color]};
                    font-family:'IBM Plex Mono',monospace;line-height:1;">{value}</div>
        {f'<div style="font-size:11px;color:#3A4556;margin-top:3px;font-family:IBM Plex Mono,monospace;">{sub}</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)


def maestro_api_field(label: str, key: str, is_password: bool = True,
                      placeholder: str = ""):
    """Campo de API key para a sidebar."""
    st.markdown(f'<div style="font-size:11px;color:#3A4556;margin-bottom:4px;font-family:IBM Plex Sans,sans-serif;font-weight:500;">{label}</div>', unsafe_allow_html=True)
    return st.text_input(
        label,
        key=key,
        type="password" if is_password else "default",
        placeholder=placeholder,
        label_visibility="collapsed",
    )


def maestro_section(title: str, sub: str = ""):
    st.markdown(f"""
    <div style="margin:24px 0 14px;">
        <div style="font-size:16px;font-weight:600;color:#E2E8F0;
                    font-family:'IBM Plex Sans',sans-serif;">{title}</div>
        {f'<div style="font-size:12px;color:#3A4556;margin-top:2px;">{sub}</div>' if sub else ''}
    </div>
    """, unsafe_allow_html=True)


def maestro_alert_badge(count: int = 0):
    if count == 0:
        color, bg, border = "#3A4556", "rgba(58,69,86,0.1)", "rgba(58,69,86,0.2)"
        icon = ""
    else:
        color, bg, border = "#FACC15", "rgba(250,204,21,0.1)", "rgba(250,204,21,0.25)"
        icon = "⚠️ "

    st.markdown(f"""
    <span style="font-size:12px;font-weight:600;font-family:IBM Plex Mono,monospace;
        padding:3px 10px;border-radius:4px;
        background:{bg};color:{color};border:1px solid {border};">
        {icon}{count} alertas
    </span>
    """, unsafe_allow_html=True)


# ── EXEMPLO DE USO ──────────────────────────────────────────────────────────
if __name__ == "__main__":

    st.set_page_config(
        page_title="Maestro — Atlas Control Plane",
        page_icon="🎼",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_maestro_theme()

    # ── SIDEBAR ──────────────────────────────────────────
    with st.sidebar:
        st.markdown("""
        <div style="padding:16px 0 14px;border-bottom:1px solid rgba(255,255,255,0.05);margin-bottom:16px;">
            <div style="display:flex;align-items:center;gap:8px;">
                <span style="font-size:20px;">🎼</span>
                <div>
                    <div style="font-size:14px;font-weight:600;color:#E2E8F0;font-family:'IBM Plex Sans',sans-serif;">Maestro</div>
                    <div style="font-size:9px;color:#3A4556;font-family:'IBM Plex Mono',monospace;text-transform:uppercase;letter-spacing:0.1em;">Atlas Control Plane V2.0</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 🔑 Atlas API")
        maestro_api_field("Public Key",  "pub_key",  True,  "••••••••")
        maestro_api_field("Private Key", "priv_key", True,  "••••••••••••••••")
        maestro_api_field("Org ID",      "org_id",   False, "5f9f1b2b3c4d5e6f7a8b9c0d")
        maestro_api_field("Project ID",  "proj_id",  False, "6a047df438c3d2e32bfbdfe1")

        st.divider()
        st.markdown("### 🤖 Anthropic API")
        maestro_api_field("API Key", "anthropic_key", True, "sk-ant-••••••••")

        st.divider()
        st.markdown("### 🔗 MongoDB Connection")
        maestro_api_field("Connection String", "conn_str", True, "mongodb+srv://...")

        st.divider()
        if st.button("🔄  Conectar & Atualizar"):
            st.success("Conectado com sucesso!")

    # ── TOPBAR ───────────────────────────────────────────
    maestro_topbar(
        org_name="POC Inter - Cartões",
        cluster_count=2,
        last_update="14:43:13",
    )

    # ── TABS ─────────────────────────────────────────────
    tabs = st.tabs([
        "🖥️  Clusters",
        "⚡  Performance Advisor",
        "🔍  Query Profiler",
        "📐  Scale",
        "💰  FinOps",
        "📊  Compare",
        "❤️  Health Score",
        "💬  AI Chat",
    ])

    with tabs[0]:
        maestro_section("Clusters da Organização")

        c1, c2, c3, c4, c5 = st.columns(5)
        with c1: maestro_metric_card("Total Clusters", "2")
        with c2: maestro_metric_card("Projetos", "1")
        with c3: maestro_metric_card("Ativos (IDLE)", "2", color="green")
        with c4: maestro_metric_card("Tier + comum", "M20", color="cyan")
        with c5: maestro_metric_card("Alertas Abertos", "0", badge="OK")

        st.markdown("<div style='margin-bottom:16px;'></div>", unsafe_allow_html=True)

        maestro_cluster_table([
            {
                "projeto": "POC Inter - Cartões",
                "cluster": "inter",
                "tier": "M20",
                "regiao": "US_EAST_1",
                "status": "IDLE",
                "mongodb": "8.0.24",
                "tipo": "REPLICASET",
                "usd": "$144",
                "brl": "R$821",
            },
            {
                "projeto": "POC Inter - Cartões",
                "cluster": "MongoDB",
                "tier": "M10",
                "regiao": "US_EAST_1",
                "status": "IDLE",
                "mongodb": "8.0.24",
                "tipo": "REPLICASET",
                "usd": "$57",
                "brl": "R$325",
            },
        ])

        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            maestro_section("Distribuição de Tiers")
            # ← seu st.bar_chart() ou plotly aqui
            import pandas as pd
            st.bar_chart(
                pd.DataFrame({"Clusters": [1, 1]}, index=["M10", "M20"]),
                color="#00ED64",
            )
        with col_chart2:
            maestro_section("Clusters por Projeto")
            # ← seu st.plotly_chart() (pie) aqui
            st.bar_chart(
                pd.DataFrame({"Clusters": [2]}, index=["POC Inter - Cartões"]),
                color="#00ED64",
            )

    with tabs[7]:  # AI Chat
        maestro_section("AI Chat", "Assistente MongoDB Atlas com contexto da sua organização")
        for msg in st.session_state.get("maestro_msgs", []):
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])
        if prompt := st.chat_input("Pergunte sobre seus clusters, performance, custos..."):
            if "maestro_msgs" not in st.session_state:
                st.session_state.maestro_msgs = []
            st.session_state.maestro_msgs.append({"role": "user", "content": prompt})
            st.rerun()
