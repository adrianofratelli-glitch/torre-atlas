"""
app.py — Maestro Atlas Control Plane  v2.0
Tabs: Clusters · PA · Profiler · Scale · FinOps · Compare · Health · AI Chat
"""

import os
import time
import json
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from dotenv import load_dotenv

from atlas_client import AtlasClient, DEDICATED_TIERS, NVME_TIERS, TIER_PRICING_USD
from ai_agent import (
    analyze_cluster_stream,
    stream_chat,
    build_chat_system_prompt,
    generate_pdf_report,
)
from streamlit_maestro_theme import maestro_cluster_table

load_dotenv()

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Maestro — Atlas Control Plane",
    page_icon="🎯",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Theme — MongoDB Atlas Design System ──────────────────────────────────────
st.html("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

/* ══ MongoDB official palette ══════════════════════════════════════════════ */
:root {
    /* backgrounds */
    --bg:       #001E2B;   /* MongoDB Atlas void */
    --surface:  #023430;   /* elevated surface   */
    --card:     #00111A;   /* card / modal        */
    --card2:    #002235;   /* secondary card     */

    /* MongoDB greens */
    --green:    #00ED64;
    --green-2:  #00A35C;
    --green-3:  #023430;
    --green-lo: rgba(0,237,100,0.08);
    --green-md: rgba(0,237,100,0.18);
    --green-bd: rgba(0,237,100,0.22);

    /* text */
    --text:     #E3FCF7;   /* MongoDB warm white */
    --sub:      #89979B;
    --muted:    #3D5A6C;

    /* semantic */
    --yellow:   #FACC15;
    --red:      #F87171;
    --blue:     #0B66DC;   /* MongoDB accent blue */
    --teal:     #00D2FF;

    /* borders */
    --border:   rgba(0,237,100,0.12);
    --border-2: rgba(255,255,255,0.06);

    --font: 'Plus Jakarta Sans', 'Helvetica Neue', Arial, sans-serif;
    --mono: 'IBM Plex Mono', 'Courier New', monospace;
}

/* ══ GLOBAL ════════════════════════════════════════════════════════════════ */
.stApp {
    background: var(--bg) !important;
    font-family: var(--font) !important;
    color: var(--text) !important;
}
#MainMenu, footer, header { visibility: hidden !important; }
.block-container {
    padding-top: 0 !important;
    padding-bottom: 3rem !important;
    max-width: 1440px !important;
}
h1,h2,h3,h4,h5 {
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-weight: 700 !important;
}
p, li, span { color: var(--sub); font-family: var(--font); }
label { color: var(--sub) !important; font-family: var(--font) !important; }

/* ══ TOPBAR (pinned green bar) ══════════════════════════════════════════════ */
.mdb-topbar {
    background: var(--surface);
    border-bottom: 2px solid var(--green);
    padding: 14px 0 12px;
    margin-bottom: 28px;
    display: flex;
    align-items: center;
    gap: 16px;
}
.mdb-logo-leaf {
    width: 28px; height: 28px;
    background: var(--green);
    clip-path: polygon(50% 0%,85% 15%,100% 50%,85% 85%,50% 100%,15% 85%,0% 50%,15% 15%);
}
.mdb-topbar-title {
    font-size: 18px;
    font-weight: 800;
    color: var(--text);
    font-family: var(--font);
    letter-spacing: -0.3px;
}
.mdb-topbar-title em { color: var(--green); font-style: normal; }
.mdb-topbar-meta {
    font-size: 11px;
    color: var(--muted);
    font-family: var(--mono);
    margin-left: auto;
    padding-right: 8px;
}

/* ══ SIDEBAR ════════════════════════════════════════════════════════════════ */
[data-testid="stSidebar"] {
    background: var(--card2) !important;
    border-right: 1px solid var(--border) !important;
}
[data-testid="stSidebar"] * {
    color: var(--sub) !important;
    font-family: var(--font) !important;
}
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] b { color: var(--text) !important; }
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {
    color: var(--muted) !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.4px !important;
}
[data-testid="stSidebar"] .stMarkdown p { font-size: 11px !important; }
[data-testid="stSidebar"] input {
    background: var(--bg) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 5px !important;
    color: var(--text) !important;
    font-family: var(--mono) !important;
    font-size: 12px !important;
    padding: 7px 10px !important;
    transition: border-color .15s, box-shadow .15s !important;
}
[data-testid="stSidebar"] input:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 2px var(--green-lo) !important;
    outline: none !important;
}
[data-testid="stSidebar"] hr {
    border-color: var(--border-2) !important;
    margin: 12px 0 !important;
}

/* ══ METRICS (native st.metric) ═════════════════════════════════════════════ */
[data-testid="metric-container"] {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 8px !important;
    padding: 18px 20px 16px !important;
    position: relative !important;
    overflow: hidden !important;
    transition: border-color .2s, box-shadow .2s !important;
}
[data-testid="metric-container"]::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 2px;
    background: linear-gradient(90deg, var(--green) 0%, var(--green-2) 100%);
    opacity: 0;
    transition: opacity .2s;
}
[data-testid="metric-container"]:hover {
    border-color: var(--green-bd) !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.35), 0 0 0 1px var(--green-lo) !important;
}
[data-testid="metric-container"]:hover::before { opacity: 1; }
[data-testid="metric-container"] label {
    color: var(--muted) !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.4px !important;
    font-family: var(--font) !important;
}
[data-testid="metric-container"] [data-testid="stMetricValue"] {
    color: var(--text) !important;
    font-size: 26px !important;
    font-weight: 700 !important;
    font-family: var(--mono) !important;
    line-height: 1.2 !important;
    letter-spacing: -0.5px !important;
}
[data-testid="metric-container"] [data-testid="stMetricDelta"] {
    font-size: 11px !important;
    font-family: var(--mono) !important;
    margin-top: 2px !important;
}

/* ══ TABS (MongoDB docs underline style) ════════════════════════════════════ */
[data-testid="stTabs"] [role="tablist"] {
    background: transparent !important;
    border-bottom: 1px solid var(--border-2) !important;
    padding: 0 !important;
    gap: 0 !important;
}
[data-testid="stTabs"] [role="tab"] {
    background: transparent !important;
    color: var(--muted) !important;
    font-family: var(--font) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    padding: 12px 18px !important;
    border-radius: 0 !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    margin-bottom: -1px !important;
    transition: color .15s, border-color .15s !important;
    letter-spacing: 0.01em !important;
}
[data-testid="stTabs"] [role="tab"]:hover { color: var(--sub) !important; }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] {
    color: var(--green) !important;
    border-bottom-color: var(--green) !important;
    font-weight: 600 !important;
}
[data-testid="stTabs"] [data-baseweb="tab-panel"] {
    padding-top: 28px !important;
}

/* ══ BUTTONS (MongoDB CTA style) ════════════════════════════════════════════ */
[data-testid="baseButton-primary"] {
    background: var(--green) !important;
    color: #001E2B !important;
    border: none !important;
    border-radius: 5px !important;
    font-family: var(--font) !important;
    font-weight: 700 !important;
    font-size: 13px !important;
    letter-spacing: 0.01em !important;
    padding: 8px 20px !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.3), 0 0 20px rgba(0,237,100,0.2) !important;
    transition: background .15s, box-shadow .15s, transform .1s !important;
}
[data-testid="baseButton-primary"]:hover {
    background: #00FF6E !important;
    box-shadow: 0 2px 8px rgba(0,0,0,0.3), 0 0 28px rgba(0,237,100,0.35) !important;
    transform: translateY(-1px) !important;
}
[data-testid="baseButton-secondary"] {
    background: transparent !important;
    color: var(--sub) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 5px !important;
    font-family: var(--font) !important;
    font-size: 13px !important;
    font-weight: 500 !important;
    transition: border-color .15s, color .15s, background .15s !important;
}
[data-testid="baseButton-secondary"]:hover {
    border-color: var(--green-bd) !important;
    color: var(--green) !important;
    background: var(--green-lo) !important;
}

/* ══ DATAFRAME ══════════════════════════════════════════════════════════════ */
[data-testid="stDataFrame"] {
    border: 1px solid var(--border-2) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
[data-testid="stDataFrame"] thead th {
    background: var(--card2) !important;
    color: var(--muted) !important;
    font-size: 10px !important;
    font-weight: 700 !important;
    text-transform: uppercase !important;
    letter-spacing: 1.2px !important;
    border-bottom: 1px solid var(--border-2) !important;
    padding: 10px 14px !important;
    font-family: var(--font) !important;
}
[data-testid="stDataFrame"] tbody td {
    color: var(--sub) !important;
    font-family: var(--mono) !important;
    font-size: 12px !important;
    border-color: var(--border-2) !important;
    padding: 10px 14px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td {
    background: var(--green-lo) !important;
    color: var(--text) !important;
}

/* ══ INPUTS ═════════════════════════════════════════════════════════════════ */
.stTextInput > div > div > input,
.stNumberInput input {
    background: var(--card) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 5px !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-size: 13px !important;
    transition: border-color .15s, box-shadow .15s !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput input:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 2px var(--green-lo) !important;
    outline: none !important;
}

/* ══ SELECTBOX ══════════════════════════════════════════════════════════════ */
.stSelectbox > div > div,
[data-baseweb="select"] > div {
    background: var(--card) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 5px !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-size: 13px !important;
}
[data-baseweb="popover"] ul {
    background: var(--card2) !important;
    border: 1px solid var(--border) !important;
    border-radius: 6px !important;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5) !important;
}
[data-baseweb="popover"] ul li {
    color: var(--sub) !important;
    font-size: 13px !important;
    font-family: var(--font) !important;
    padding: 8px 14px !important;
}
[data-baseweb="popover"] ul li:hover {
    background: var(--green-lo) !important;
    color: var(--green) !important;
}

/* ══ SLIDER ═════════════════════════════════════════════════════════════════ */
[data-testid="stSlider"] [role="slider"] {
    background: var(--green) !important;
    box-shadow: 0 0 0 3px var(--green-lo), 0 0 10px rgba(0,237,100,0.4) !important;
}
[data-testid="stSlider"] [data-testid="stTickBar"] { color: var(--muted) !important; }

/* ══ EXPANDER ═══════════════════════════════════════════════════════════════ */
[data-testid="stExpander"] {
    background: var(--card2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}
[data-testid="stExpander"] summary {
    color: var(--sub) !important;
    font-family: var(--font) !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    padding: 12px 16px !important;
}
[data-testid="stExpander"] summary:hover { color: var(--green) !important; }

/* ══ ALERTS ═════════════════════════════════════════════════════════════════ */
[data-testid="stAlert"] {
    border-radius: 6px !important;
    border: none !important;
    border-left: 3px solid !important;
    font-family: var(--font) !important;
    font-size: 13px !important;
}
.stSuccess {
    background: rgba(0,237,100,0.07) !important;
    border-left-color: var(--green) !important;
    color: #7FFFC4 !important;
}
.stWarning {
    background: rgba(250,204,21,0.07) !important;
    border-left-color: var(--yellow) !important;
    color: var(--yellow) !important;
}
.stError {
    background: rgba(248,113,113,0.07) !important;
    border-left-color: var(--red) !important;
    color: var(--red) !important;
}
.stInfo {
    background: rgba(11,102,220,0.08) !important;
    border-left-color: var(--blue) !important;
    color: #93C5FD !important;
}

/* ══ CODE ═══════════════════════════════════════════════════════════════════ */
code, pre, .stJson {
    background: var(--card) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 6px !important;
    color: var(--green) !important;
    font-family: var(--mono) !important;
    font-size: 12px !important;
}

/* ══ DIVIDER ════════════════════════════════════════════════════════════════ */
hr { border-color: var(--border-2) !important; margin: 16px 0 !important; }

/* ══ CHAT ═══════════════════════════════════════════════════════════════════ */
[data-testid="stChatMessage"] {
    background: var(--card2) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 10px !important;
    padding: 16px !important;
    margin-bottom: 10px !important;
}
[data-testid="stChatInput"] textarea {
    background: var(--card) !important;
    border: 1px solid var(--border-2) !important;
    border-radius: 8px !important;
    color: var(--text) !important;
    font-family: var(--font) !important;
    font-size: 14px !important;
}
[data-testid="stChatInput"] textarea:focus {
    border-color: var(--green) !important;
    box-shadow: 0 0 0 2px var(--green-lo) !important;
}
[data-testid="stChatInput"] button {
    background: var(--green) !important;
    border-radius: 6px !important;
}

/* ══ MISC ═══════════════════════════════════════════════════════════════════ */
.stSpinner > div { border-top-color: var(--green) !important; }

::-webkit-scrollbar { width: 5px; height: 5px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,237,100,0.15); border-radius: 3px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,237,100,0.35); }

/* ══ SIDEBAR NAVIGATION ══════════════════════════════════════════════════════ */
.mdb-nav-section-lbl {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2.2px;
    color: #3D5A6C;
    padding: 14px 4px 5px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    display: block;
}
.mdb-nav-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 7px 10px 7px 10px;
    border-radius: 5px;
    border-left: 2px solid transparent;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 13px;
    font-weight: 400;
    color: #89979B;
    margin-bottom: 1px;
    transition: background 0.12s, color 0.12s;
    cursor: default;
}
.mdb-nav-item:hover { background: rgba(0,237,100,0.05); color: #E3FCF7; }
.mdb-nav-item.active {
    background: rgba(0,237,100,0.09);
    color: #00ED64;
    border-left-color: #00ED64;
    font-weight: 600;
}
.mdb-nav-check {
    width: 13px;
    height: 13px;
    border: 1.5px solid currentColor;
    border-radius: 2px;
    flex-shrink: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0.65;
    font-size: 9px;
}
.mdb-nav-item.active .mdb-nav-check {
    background: #00ED64;
    border-color: #00ED64;
    color: #001E2B;
    opacity: 1;
}

/* ══ BREADCRUMB TOPBAR ═══════════════════════════════════════════════════════ */
.mdb-breadcrumb {
    background: linear-gradient(90deg, #023430 0%, #001E2B 70%);
    border-bottom: 2px solid #00ED64;
    border-radius: 8px 8px 0 0;
    padding: 14px 22px;
    display: flex;
    align-items: center;
    gap: 0;
    margin-bottom: 6px;
}
.mdb-breadcrumb-title {
    font-size: 17px;
    font-weight: 800;
    color: #E3FCF7;
    font-family: 'Plus Jakarta Sans', sans-serif;
    letter-spacing: -0.3px;
}
.mdb-breadcrumb-sep {
    font-size: 14px;
    color: #3D5A6C;
    margin: 0 10px;
}
.mdb-breadcrumb-sub {
    font-size: 13px;
    color: #89979B;
    font-family: 'IBM Plex Mono', monospace;
    letter-spacing: 0.01em;
}
.mdb-breadcrumb-meta {
    font-size: 11px;
    color: #3D5A6C;
    font-family: 'IBM Plex Mono', monospace;
    margin-left: auto;
}
.mdb-btn {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 7px 16px;
    border-radius: 6px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 13px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.15s;
}
.mdb-btn-outline {
    background: transparent;
    color: #E3FCF7;
    border: 1.5px solid rgba(255,255,255,0.15);
}
.mdb-btn-outline:hover { border-color: rgba(0,237,100,0.4); color: #00ED64; }
.mdb-btn-primary {
    background: var(--green);
    color: #001E2B;
    border: none;
    box-shadow: 0 0 16px rgba(0,237,100,0.25);
}
.mdb-btn-primary:hover { background: #00FF6E; box-shadow: 0 0 24px rgba(0,237,100,0.4); }

/* ══ CUSTOM CLASSES ══════════════════════════════════════════════════════════ */
.health-grade {
    font-size: 3rem !important;
    font-weight: 800 !important;
    line-height: 1 !important;
    font-family: var(--mono) !important;
}
.chat-context-badge {
    background: var(--card);
    border: 1px solid var(--green-bd);
    border-radius: 5px;
    padding: 5px 12px;
    font-size: 12px;
    color: var(--green);
    display: inline-block;
    margin-bottom: 10px;
    font-family: var(--mono);
}

/* ══ KPI CARDS (mdb_kpi_row) ═════════════════════════════════════════════════
   Replicates the MongoDB dashboard card style:
   colored top border · large mono value · uppercase label
   ══════════════════════════════════════════════════════════════════════════ */
.mdb-kpi-row {
    display: flex;
    gap: 14px;
    margin: 20px 0 28px;
    width: 100%;
}
.mdb-kpi-card {
    flex: 1;
    background: var(--card2);
    border: 1px solid rgba(255,255,255,0.06);
    border-top: 3px solid var(--green);
    border-radius: 0 0 8px 8px;
    padding: 18px 20px 16px;
    position: relative;
    overflow: hidden;
    transition: box-shadow .2s, border-color .2s;
    cursor: default;
}
.mdb-kpi-card::after {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: radial-gradient(ellipse at top left, rgba(255,255,255,0.025) 0%, transparent 70%);
    pointer-events: none;
}
.mdb-kpi-card:hover {
    box-shadow: 0 8px 32px rgba(0,0,0,0.45);
    border-color: rgba(255,255,255,0.1);
}
.mdb-kpi-label {
    font-size: 10px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    color: var(--muted);
    font-family: var(--font);
    margin-bottom: 10px;
}
.mdb-kpi-value {
    font-size: 30px;
    font-weight: 700;
    font-family: var(--mono);
    line-height: 1.1;
    letter-spacing: -0.5px;
    color: var(--text);
}
.mdb-kpi-delta {
    font-size: 11px;
    color: var(--muted);
    font-family: var(--mono);
    margin-top: 6px;
}
.mdb-kpi-delta.up   { color: var(--green); }
.mdb-kpi-delta.down { color: #F87171; }
.mdb-kpi-delta.warn { color: #FACC15; }

/* ══ SECTION HEADERS (mdb_section_header) ════════════════════════════════════ */
.mdb-section-hdr {
    display: flex;
    align-items: center;
    gap: 12px;
    margin: 28px 0 18px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}
.mdb-section-hdr-title {
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1.8px;
    color: var(--sub);
    font-family: var(--font);
}
.mdb-section-hdr-badge {
    font-size: 10px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 3px;
    font-family: var(--mono);
    letter-spacing: 0.4px;
}
.mdb-section-hdr-badge.green {
    background: rgba(0,237,100,0.1);
    color: var(--green);
    border: 1px solid rgba(0,237,100,0.22);
}
.mdb-section-hdr-badge.yellow {
    background: rgba(250,204,21,0.1);
    color: #FACC15;
    border: 1px solid rgba(250,204,21,0.22);
}
.mdb-section-hdr-badge.blue {
    background: rgba(56,189,248,0.1);
    color: #38BDF8;
    border: 1px solid rgba(56,189,248,0.22);
}
.mdb-section-hdr-sub {
    font-size: 11px;
    color: var(--muted);
    font-family: var(--mono);
    margin-left: auto;
}

/* ══ SIDEBAR NAV SECTION LABELS ══════════════════════════════════════════════ */
.mdb-nav-section {
    font-size: 9px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 2px;
    color: #3D5A6C;
    font-family: 'Plus Jakarta Sans', sans-serif;
    padding: 14px 0 6px;
}
.mdb-cluster-pill {
    background: rgba(0,237,100,0.08);
    border: 1px solid rgba(0,237,100,0.2);
    border-radius: 6px;
    padding: 10px 14px;
    margin-top: 12px;
}
.mdb-cluster-pill-label {
    font-size: 9px;
    color: #3D5A6C;
    text-transform: uppercase;
    letter-spacing: 1.5px;
    font-family: 'Plus Jakarta Sans', sans-serif;
}
.mdb-cluster-pill-value {
    font-size: 13px;
    font-weight: 700;
    color: #00ED64;
    font-family: 'IBM Plex Mono', monospace;
    margin-top: 3px;
}

</style>
""")


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── MongoDB leaf logo + brand ──────────────────────────────────────────
    st.markdown("""
    <div style="padding:18px 4px 14px;border-bottom:1px solid rgba(0,237,100,0.12);margin-bottom:16px;">
      <div style="display:flex;align-items:center;gap:10px;">
        <svg width="28" height="28" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M14 2C8.48 2 4 6.7 4 12.5c0 4.1 2.1 7.7 5.3 9.7l.7 3.3c.1.3.3.5.6.5h6.8c.3 0 .5-.2.6-.5l.7-3.3C21.9 20.2 24 16.6 24 12.5 24 6.7 19.52 2 14 2zm.8 16.2v3.3c0 .1-.1.2-.2.2h-1.2c-.1 0-.2-.1-.2-.2v-3.3C11.1 17.4 9.5 15 9.5 12.5c0-2.5 2-4.5 4.5-4.5s4.5 2 4.5 4.5c0 2.5-1.6 4.9-3.7 5.7z" fill="#00ED64"/>
        </svg>
        <div>
          <div style="font-size:15px;font-weight:800;color:#E3FCF7;font-family:'Plus Jakarta Sans',sans-serif;letter-spacing:-0.2px;line-height:1.2;">Maestro</div>
          <div style="font-size:9px;color:#3D5A6C;text-transform:uppercase;letter-spacing:1.8px;font-family:'Plus Jakarta Sans',sans-serif;margin-top:1px;">Atlas Control Plane · v2.0</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    # ── Navegação ──────────────────────────────────────────────────────────────
    _nav_active = st.session_state.get("_nav_active", "clusters")
    _NAV = [
        ("PRINCIPAL", [
            ("clusters", "Dashboard"),
            ("finops",   "FinOps"),
        ]),
        ("ANALYTICS", [
            ("pa",       "Performance Advisor"),
            ("profiler", "Query Profiler"),
            ("scale",    "Scale"),
            ("compare",  "Compare"),
            ("health",   "Health Score"),
        ]),
        ("TOOLS", [
            ("chat",     "AI Agent"),
        ]),
        ("CONFIG", [
            ("settings", "Settings"),
        ]),
    ]
    _nav_html = ""
    for _grp, _items in _NAV:
        _nav_html += f'<span class="mdb-nav-section-lbl">{_grp}</span>'
        for _key, _lbl in _items:
            _cls = "active" if _nav_active == _key else ""
            _chk = "✓" if _nav_active == _key else ""
            _nav_html += (
                f'<div class="mdb-nav-item {_cls}">'
                f'<div class="mdb-nav-check">{_chk}</div>{_lbl}</div>'
            )
    st.markdown(_nav_html, unsafe_allow_html=True)

    # Nav buttons invisíveis para troca de estado (um por item)
    _nav_cols = st.columns(len([i for _, g in _NAV for i in g]))
    _nav_idx = 0
    for _, _items in _NAV:
        for _key, _lbl in _items:
            with _nav_cols[_nav_idx]:
                if st.button("·", key=f"_nav_{_key}", help=_lbl,
                             use_container_width=True,
                             label_visibility="hidden"):
                    st.session_state["_nav_active"] = _key
                    st.rerun()
            _nav_idx += 1

    st.divider()

    # ── Credenciais (collapsible) ──────────────────────────────────────────────
    _cred_icon = "🟢" if bool(os.getenv("ATLAS_PUBLIC_KEY")) else "⚪"
    with st.expander(f"{_cred_icon} Credenciais & Configurações", expanded=not bool(os.getenv("ATLAS_PUBLIC_KEY"))):
        st.markdown("**🔑 Atlas API**")
        pub_key     = st.text_input("Public Key",  value=os.getenv("ATLAS_PUBLIC_KEY",  ""), type="password")
        priv_key    = st.text_input("Private Key", value=os.getenv("ATLAS_PRIVATE_KEY", ""), type="password")
        org_id      = st.text_input("Org ID",      value=os.getenv("ATLAS_ORG_ID",      ""))
        proj_id_env = st.text_input("Project ID",  value=os.getenv("ATLAS_PROJECT_ID",  ""))

        st.markdown("**🤖 Anthropic API**")
        ant_key = st.text_input("API Key", value=os.getenv("ANTHROPIC_API_KEY", ""), type="password")

        st.markdown("**🔗 MongoDB Connection**")
        mongo_uri = st.text_input(
            "Connection String",
            value=os.getenv("MONGODB_URI", ""),
            type="password",
            help="Necessário para criar índices diretamente.",
        )

        st.markdown("**⚙️ Configurações**")
        usd_brl = st.number_input("USD/BRL", value=5.70, step=0.05, format="%.2f")
        refresh_opt = st.selectbox("Auto-refresh", ["Off", "30s", "60s", "120s"], index=0)

    st.divider()
    connected = bool(pub_key and priv_key and (org_id or proj_id_env))
    if connected:
        st.success("✅ Atlas conectado")
    else:
        st.warning("⚠️ Preencha as credenciais")

    if ant_key:
        os.environ["ANTHROPIC_API_KEY"] = ant_key
        st.success("✅ Claude pronto")
    else:
        st.info("ℹ️ Configure a Anthropic API Key para o AI Chat")

    if mongo_uri:
        st.success("✅ Connection String configurada")

    # ── Cluster status pill (bottom of sidebar) ────────────────────────────
    if connected and "all_clusters" in dir() and all_clusters:
        _tiers  = [c["tier"] for c in all_clusters if c["tier"] not in ["Free/Shared","—"]]
        _top    = _tiers[0] if _tiers else "Free"
        _region = all_clusters[0].get("region","—") if all_clusters else "—"
        st.markdown(f"""
        <div class="mdb-cluster-pill">
          <div class="mdb-cluster-pill-label">Cluster Ativo</div>
          <div class="mdb-cluster-pill-value">{_top} · {_region}</div>
        </div>
        """, unsafe_allow_html=True)


# ── Guard ─────────────────────────────────────────────────────────────────────
if not connected:
    st.markdown("""
    <div style="max-width:600px;margin:80px auto 0;text-align:center;">
      <svg width="52" height="52" viewBox="0 0 28 28" fill="none" xmlns="http://www.w3.org/2000/svg" style="margin-bottom:20px;">
        <path d="M14 2C8.48 2 4 6.7 4 12.5c0 4.1 2.1 7.7 5.3 9.7l.7 3.3c.1.3.3.5.6.5h6.8c.3 0 .5-.2.6-.5l.7-3.3C21.9 20.2 24 16.6 24 12.5 24 6.7 19.52 2 14 2zm.8 16.2v3.3c0 .1-.1.2-.2.2h-1.2c-.1 0-.2-.1-.2-.2v-3.3C11.1 17.4 9.5 15 9.5 12.5c0-2.5 2-4.5 4.5-4.5s4.5 2 4.5 4.5c0 2.5-1.6 4.9-3.7 5.7z" fill="#00ED64"/>
      </svg>
      <div style="font-size:28px;font-weight:800;color:#E3FCF7;font-family:'Plus Jakarta Sans',sans-serif;letter-spacing:-0.5px;margin-bottom:8px;">
        Maestro <span style="color:#00ED64;">Atlas Control Plane</span>
      </div>
      <div style="font-size:13px;color:#3D5A6C;font-family:'IBM Plex Mono',monospace;margin-bottom:32px;letter-spacing:0.5px;">
        PREENCHA AS CREDENCIAIS NO PAINEL LATERAL PARA COMEÇAR
      </div>
      <div style="display:flex;gap:12px;justify-content:center;flex-wrap:wrap;">
        <div style="background:#002235;border:1px solid rgba(0,237,100,0.15);border-top:2px solid #00ED64;border-radius:0 0 8px 8px;padding:16px 20px;min-width:160px;text-align:left;">
          <div style="font-size:9px;color:#3D5A6C;text-transform:uppercase;letter-spacing:1.5px;font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:6px;">1 — Atlas API Key</div>
          <div style="font-size:12px;color:#89979B;font-family:'IBM Plex Mono',monospace;">Org → Access Manager</div>
        </div>
        <div style="background:#002235;border:1px solid rgba(56,189,248,0.15);border-top:2px solid #38BDF8;border-radius:0 0 8px 8px;padding:16px 20px;min-width:160px;text-align:left;">
          <div style="font-size:9px;color:#3D5A6C;text-transform:uppercase;letter-spacing:1.5px;font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:6px;">2 — Anthropic Key</div>
          <div style="font-size:12px;color:#89979B;font-family:'IBM Plex Mono',monospace;">console.anthropic.com</div>
        </div>
        <div style="background:#002235;border:1px solid rgba(0,212,170,0.15);border-top:2px solid #00D4AA;border-radius:0 0 8px 8px;padding:16px 20px;min-width:160px;text-align:left;">
          <div style="font-size:9px;color:#3D5A6C;text-transform:uppercase;letter-spacing:1.5px;font-family:'Plus Jakarta Sans',sans-serif;margin-bottom:6px;">3 — Connection String</div>
          <div style="font-size:12px;color:#89979B;font-family:'IBM Plex Mono',monospace;">opcional · para índices</div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Client ────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client(pub, priv, org, proj=""):
    return AtlasClient(pub, priv, org, proj)

client = get_client(pub_key, priv_key, org_id, proj_id_env)


# ── Load all clusters ─────────────────────────────────────────────────────────
@st.cache_data(ttl=60, show_spinner=False)
def load_all_clusters(_client: AtlasClient):
    rows = []
    try:
        projects = _client.get_projects()
    except Exception as e:
        return [], str(e)
    for proj in projects:
        try:
            clusters = _client.get_clusters(proj["id"])
        except Exception:
            continue
        for c in clusters:
            tier = region = "Free/Shared"
            region = "—"
            try:
                rc     = c["replicationSpecs"][0]["regionConfigs"][0]
                tier   = rc["electableSpecs"]["instanceSize"]
                region = rc["regionName"]
            except (KeyError, IndexError, TypeError):
                pass

            # Atlas tem campo "paused" separado do stateName
            raw_status = c.get("stateName", "—")
            is_paused  = c.get("paused", False)
            status     = "PAUSED" if is_paused else raw_status

            rows.append({
                "project_id":    proj["id"],
                "project_name":  proj["name"],
                "cluster_name":  c["name"],
                "tier":          tier,
                "region":        region,
                "status":        status,
                "mongo_version": c.get("mongoDBVersion", "—"),
                "cluster_type":  c.get("clusterType", "—"),
            })
    return rows, None


with st.spinner("Carregando clusters…"):
    all_clusters, load_error = load_all_clusters(client)


# ── Auto-refresh ──────────────────────────────────────────────────────────────
REFRESH_INTERVALS = {"30s": 30, "60s": 60, "120s": 120}
if refresh_opt != "Off":
    interval = REFRESH_INTERVALS[refresh_opt]
    now = time.time()
    if "last_refresh" not in st.session_state:
        st.session_state["last_refresh"] = now
    elif now - st.session_state["last_refresh"] >= interval:
        st.session_state["last_refresh"] = now
        st.cache_data.clear()
        st.rerun()


# ── Page header ───────────────────────────────────────────────────────────────
STATUS_ICON = {
    "IDLE":      "🟢 IDLE",
    "CREATING":  "🟡 CREATING",
    "UPDATING":  "🟡 UPDATING",
    "PAUSED":    "⚪ PAUSED",
    "RESUMING":  "🟡 RESUMING",
    "DELETING":  "🔴 DELETING",
    "REPAIRING": "🔴 REPAIRING",
    "REPEATING": "🟡 REPEATING",
}

refresh_badge = f" · 🔄 {refresh_opt}" if refresh_opt != "Off" else ""
_active_nav   = st.session_state.get("_nav_active", "clusters")
_tab_labels   = {
    "clusters": "Dashboard", "finops": "FinOps", "pa": "Performance Advisor",
    "profiler": "Query Profiler", "scale": "Scale", "compare": "Compare",
    "health": "Health Score", "chat": "AI Agent", "settings": "Settings",
}
_page_title   = _tab_labels.get(_active_nav, "Dashboard")
_org_display  = (org_id[:16] + "…") if len(org_id) > 16 else (org_id or "—")
_proj_display = (proj_id_env[:16] + "…") if len(proj_id_env) > 16 else (proj_id_env or "—")

_hcol, _rcol = st.columns([7, 2])
with _hcol:
    st.markdown(
        f'<div class="mdb-breadcrumb">'
        f'<span class="mdb-breadcrumb-title">{_page_title}</span>'
        f'<span class="mdb-breadcrumb-sep">·</span>'
        f'<span class="mdb-breadcrumb-sub">org: {_org_display}</span>'
        f'<span class="mdb-breadcrumb-sep">·</span>'
        f'<span class="mdb-breadcrumb-sub">{len(all_clusters)} cluster(s)</span>'
        f'<span class="mdb-breadcrumb-meta">'
        f'{datetime.now().strftime("%H:%M:%S")}{refresh_badge}</span>'
        f'</div>',
        unsafe_allow_html=True,
    )
with _rcol:
    st.markdown("<div style='margin-top:6px;display:flex;gap:8px;'>", unsafe_allow_html=True)
    _bc1, _bc2 = st.columns(2)
    with _bc1:
        if st.button("↺  Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    with _bc2:
        if st.button("＋  Nova POC", use_container_width=True, type="primary"):
            st.info("Configure as credenciais de uma nova POC na sidebar.")

if load_error:
    st.error(f"Erro ao carregar clusters: {load_error}")
    st.stop()

st.divider()


# ── Helper functions ──────────────────────────────────────────────────────────
def project_selector(key_prefix: str):
    project_map = {c["project_name"]: c["project_id"] for c in all_clusters}
    proj_name = st.selectbox("Projeto", list(project_map.keys()), key=f"{key_prefix}_proj")
    proj_id   = project_map[proj_name]
    in_proj   = [c for c in all_clusters if c["project_id"] == proj_id]
    return proj_name, proj_id, in_proj

def cluster_selector(clusters_in_proj: list, key_prefix: str):
    names        = [c["cluster_name"] for c in clusters_in_proj]
    cluster_name = st.selectbox("Cluster", names, key=f"{key_prefix}_cluster")
    row          = next((c for c in clusters_in_proj if c["cluster_name"] == cluster_name), {})
    return cluster_name, row

def calculate_health_score(status: str, n_suggestions: int, n_slow: int, mongo_version: str) -> dict:
    score  = 100
    issues = []
    if status == "IDLE":
        pass  # perfeito, sem penalidade
    elif status == "PAUSED":
        score -= 10
        issues.append("Cluster PAUSADO  (-10 pts) — métricas podem estar desatualizadas")
    else:
        score -= 20
        issues.append(f"Status {status} não-IDLE  (-20 pts)")
    penalty = min(n_suggestions * 5, 30)
    if penalty:
        score -= penalty
        issues.append(f"{n_suggestions} índice(s) sugerido(s) pelo PA  (-{penalty} pts)")
    penalty = min(n_slow * 2, 30)
    if penalty:
        score -= penalty
        issues.append(f"{n_slow} slow quer{'y' if n_slow == 1 else 'ies'}  (-{penalty} pts)")
    try:
        major = int(mongo_version.split(".")[0])
        if major < 7:
            score -= 10
            issues.append(f"MongoDB {mongo_version} (versão desatualizada)  (-10 pts)")
    except Exception:
        pass
    score = max(0, score)
    grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"
    color = "#00ED64" if score >= 75 else "#FFA500" if score >= 50 else "#FF4444"
    return {"score": score, "grade": grade, "color": color, "issues": issues}

def health_gauge_fig(score: int, color: str):
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={"font": {"color": color, "size": 52}, "suffix": ""},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#B8C4C2", "tickfont": {"color": "#B8C4C2"}},
            "bar": {"color": color, "thickness": 0.3},
            "bgcolor": "#001a24",
            "bordercolor": "rgba(0,237,100,0.19)",
            "borderwidth": 1,
            "steps": [
                {"range": [0,  40], "color": "rgba(255,68,68,0.08)"},
                {"range": [40, 75], "color": "rgba(255,165,0,0.08)"},
                {"range": [75,100], "color": "rgba(0,237,100,0.08)"},
            ],
        },
    ))
    fig.update_layout(
        height=280, paper_bgcolor="rgba(0,0,0,0)",
        font={"color": "#B8C4C2"}, margin=dict(t=30, b=10, l=20, r=20),
    )
    return fig

def plotly_dark(fig, height=280):
    fig.update_layout(
        height=height,
        plot_bgcolor="#001E2B",
        paper_bgcolor="#002235",
        font_color="#89979B",
        font_family="IBM Plex Mono",
        margin=dict(t=40, b=20, l=10, r=10),
    )
    fig.update_xaxes(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)")
    fig.update_yaxes(gridcolor="rgba(255,255,255,0.05)", zerolinecolor="rgba(255,255,255,0.05)")
    return fig


# ── UI helper: KPI card row ───────────────────────────────────────────────────
_KPI_COLORS = {
    "green":  ("#00ED64",  "rgba(0,237,100,0.10)"),
    "teal":   ("#00D4AA",  "rgba(0,212,170,0.10)"),
    "blue":   ("#38BDF8",  "rgba(56,189,248,0.10)"),
    "yellow": ("#FACC15",  "rgba(250,204,21,0.10)"),
    "orange": ("#F97316",  "rgba(249,115,22,0.10)"),
    "red":    ("#F87171",  "rgba(248,113,113,0.10)"),
    "muted":  ("#89979B",  "rgba(137,151,155,0.06)"),
}

def mdb_kpi_row(cards: list):
    """
    Renders a row of MongoDB-style KPI cards as a single st.markdown() block.
    cards = [{"label": str, "value": str, "delta": str|None,
              "color": "green"|"teal"|"blue"|"yellow"|"orange"|"red"|"muted",
              "delta_type": "up"|"down"|"warn"|"" }]
    """
    html = '<div class="mdb-kpi-row">'
    for card in cards:
        accent, bg = _KPI_COLORS.get(card.get("color", "green"), _KPI_COLORS["green"])
        delta_cls  = card.get("delta_type", "")
        delta_html = (f'<div class="mdb-kpi-delta {delta_cls}">{card["delta"]}</div>'
                      if card.get("delta") else "")
        html += (
            f'<div class="mdb-kpi-card" '
            f'style="border-top-color:{accent};background:linear-gradient(160deg,{bg} 0%,#002235 100%);">'
            f'<div class="mdb-kpi-label">{card["label"]}</div>'
            f'<div class="mdb-kpi-value" style="color:{accent};">{card["value"]}</div>'
            f'{delta_html}'
            f'</div>'
        )
    html += '</div>'
    st.markdown(html, unsafe_allow_html=True)


def mdb_section_header(title: str, badge: str = "", badge_color: str = "green", sub: str = ""):
    """Renders a styled section header matching the MongoDB dashboard style."""
    badge_html = (f'<span class="mdb-section-hdr-badge {badge_color}">{badge}</span>'
                  if badge else "")
    sub_html   = f'<span class="mdb-section-hdr-sub">{sub}</span>' if sub else ""
    st.markdown(
        f'<div class="mdb-section-hdr">'
        f'<span class="mdb-section-hdr-title">{title}</span>'
        f'{badge_html}{sub_html}'
        f'</div>',
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════════════════════════════════════
# TABS
# ══════════════════════════════════════════════════════════════════════════════
(
    tab_clusters, tab_pa, tab_profiler,
    tab_scale, tab_finops, tab_compare,
    tab_health, tab_chat,
) = st.tabs([
    "🏗️ Clusters",
    "⚡ Performance Advisor",
    "🔍 Query Profiler",
    "📈 Scale",
    "💰 FinOps",
    "📊 Compare",
    "🏥 Health Score",
    "💬 AI Chat",
])


# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — CLUSTERS
# ══════════════════════════════════════════════════════════════════════════════
with tab_clusters:
    mdb_section_header("Clusters da Organização", badge="Live", badge_color="green",
                       sub=f"atualizado {datetime.now().strftime('%H:%M:%S')}")
    if not all_clusters:
        st.warning("Nenhum cluster encontrado. Verifique as permissões da API Key.")
    else:
        df = pd.DataFrame(all_clusters)
        dedicated    = df[~df["tier"].isin(["Free/Shared"])]
        top_tier     = dedicated["tier"].value_counts().index[0] if len(dedicated) else "—"
        idle_count   = len(df[df["status"] == "IDLE"])
        total_alerts = 0
        for proj_id_a in df["project_id"].unique():
            total_alerts += len(client.get_open_alerts(proj_id_a))

        mdb_kpi_row([
            {"label": "Total Clusters",  "value": str(len(df)),
             "delta": f"{df['project_name'].nunique()} projeto(s)", "color": "green"},
            {"label": "Projetos",        "value": str(df["project_name"].nunique()),
             "delta": "na organização", "color": "blue"},
            {"label": "Ativos (IDLE)",   "value": str(idle_count),
             "delta": "↑ online" if idle_count == len(df) else f"{len(df)-idle_count} offline",
             "delta_type": "up" if idle_count == len(df) else "warn",
             "color": "green" if idle_count == len(df) else "yellow"},
            {"label": "Tier + comum",    "value": top_tier,
             "delta": "dedicated", "color": "teal"},
            {"label": "Alertas Abertos", "value": str(total_alerts),
             "delta": f"↑ {total_alerts} ativos" if total_alerts > 0 else "✓ nenhum",
             "delta_type": "down" if total_alerts > 0 else "up",
             "color": "yellow" if total_alerts > 0 else "green"},
        ])
        st.divider()

        _table_rows = []
        for _c in all_clusters:
            _cost = AtlasClient.estimate_cost(_c["tier"], usd_brl)
            _table_rows.append({
                "projeto": _c["project_name"],
                "cluster": _c["cluster_name"],
                "tier":    _c["tier"],
                "regiao":  _c["region"],
                "status":  _c["status"],
                "mongodb": _c["mongo_version"],
                "tipo":    _c["cluster_type"],
                "usd":     f"${_cost['usd']:,.0f}",
                "brl":     f"R${_cost['brl']:,.0f}",
            })
        maestro_cluster_table(_table_rows)

        if len(dedicated) > 0:
            st.divider()
            col_c1, col_c2 = st.columns(2)
            with col_c1:
                st.markdown("**Distribuição de Tiers**")
                tier_counts = dedicated["tier"].value_counts()
                fig = px.bar(x=tier_counts.index, y=tier_counts.values,
                             labels={"x":"Tier","y":"Clusters"}, color_discrete_sequence=["#00ED64"])
                st.plotly_chart(plotly_dark(fig), use_container_width=True)
            with col_c2:
                st.markdown("**Clusters por Projeto**")
                proj_counts = df["project_name"].value_counts()
                fig2 = px.pie(names=proj_counts.index, values=proj_counts.values,
                              hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r)
                st.plotly_chart(plotly_dark(fig2), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PERFORMANCE ADVISOR
# ══════════════════════════════════════════════════════════════════════════════
with tab_pa:
    mdb_section_header("Performance Advisor", badge="Índices", badge_color="yellow")
    if not all_clusters:
        st.warning("Nenhum cluster disponível.")
    else:
        _, proj_id_pa, in_proj_pa = project_selector("pa")
        cluster_name_pa, _        = cluster_selector(in_proj_pa, "pa")

        if st.button("🔍 Buscar Recomendações", key="btn_pa"):
            with st.spinner("Consultando Performance Advisor…"):
                try:
                    pid = client.get_primary(proj_id_pa, cluster_name_pa)
                    if not pid:
                        st.error("Processo primário não encontrado.")
                    else:
                        pa_data = client.get_suggested_indexes(proj_id_pa, pid)
                        st.session_state["pa_data"]         = pa_data
                        st.session_state["pa_cluster_name"] = cluster_name_pa
                except Exception as e:
                    st.error(f"Erro: {e}")

        if "pa_data" in st.session_state and st.session_state.get("pa_cluster_name") == cluster_name_pa:
            suggestions = st.session_state["pa_data"].get("suggestedIndexes", [])
            if not suggestions:
                st.success(f"✅ Nenhuma recomendação para **{cluster_name_pa}** — cluster saudável!")
            else:
                st.warning(f"⚠️ {len(suggestions)} índice(s) sugerido(s) para **{cluster_name_pa}**")

                for i, idx in enumerate(suggestions):
                    ns         = idx.get("namespace", "N/A")
                    weight     = round(idx.get("weight", 0), 2)
                    index_keys = idx.get("index", [])
                    impact     = idx.get("impact", [])

                    fields = ", ".join(
                        f'"{list(k.keys())[0]}": {list(k.values())[0]}' for k in index_keys
                    )
                    cmd = f'db.{ns.split(".")[-1]}.createIndex({{ {fields} }})'

                    with st.expander(f"#{i+1} — `{ns}`  ·  peso {weight}", expanded=(i == 0)):
                        col_left, col_right = st.columns([3, 2])
                        with col_left:
                            st.markdown("**Comando:**")
                            st.code(cmd, language="javascript")  # ← built-in copy button

                        with col_right:
                            st.markdown("**Operações impactadas:**")
                            for op in impact[:4]:
                                if isinstance(op, dict):
                                    avg_ms = round(op.get("avgMs", 0), 1)
                                    count  = op.get("count", 0)
                                    ns_op  = op.get("namespace", ns)
                                else:
                                    avg_ms, count, ns_op = 0, 0, str(op)
                                st.markdown(f"- `{ns_op}`  ·  avg **{avg_ms}ms**  ·  **{count}x**")

                        # ── Execute via pymongo ──
                        if mongo_uri:
                            if st.button(f"▶ Executar Índice #{i+1}", key=f"exec_idx_{i}"):
                                from atlas_client import create_index_direct
                                with st.spinner("Criando índice…"):
                                    result = create_index_direct(mongo_uri, ns, index_keys)
                                if "✅" in result:
                                    st.success(result)
                                else:
                                    st.error(result)
                        else:
                            st.caption("💡 Configure a **Connection String** na sidebar para criar o índice com 1 clique")

                # ── AI Analysis button (shown once after all suggestions) ──
                st.divider()
                if st.button("🤖 Analisar com AI (Claude)", key="btn_pa_ai", type="primary"):
                    with st.spinner("Claude analisando o cluster…"):
                        try:
                            full_c = client.get_cluster(proj_id_pa, cluster_name_pa)
                            sq_r   = client.get_slow_queries(proj_id_pa,
                                         client.get_primary(proj_id_pa, cluster_name_pa) or "")
                            with st.chat_message("assistant"):
                                holder = st.empty()
                                text   = ""
                                for chunk in analyze_cluster_stream(full_c, st.session_state["pa_data"], sq_r):
                                    text += chunk
                                    holder.markdown(text + "▌")
                                holder.markdown(text)
                        except Exception as e:
                            st.error(f"Erro na análise AI: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — QUERY PROFILER
# ══════════════════════════════════════════════════════════════════════════════
with tab_profiler:
    mdb_section_header("Query Profiler", badge="Slow Queries", badge_color="yellow")
    if not all_clusters:
        st.warning("Nenhum cluster disponível.")
    else:
        _, proj_id_qp, in_proj_qp = project_selector("qp")
        cluster_name_qp, _        = cluster_selector(in_proj_qp, "qp")

        if st.button("🔍 Carregar Slow Queries", key="btn_qp"):
            with st.spinner("Buscando slow queries…"):
                try:
                    pid_qp = client.get_primary(proj_id_qp, cluster_name_qp)
                    if not pid_qp:
                        st.error("Processo primário não encontrado.")
                    else:
                        sq_data = client.get_slow_queries(proj_id_qp, pid_qp)
                        st.session_state["sq_data"]         = sq_data
                        st.session_state["sq_cluster_name"] = cluster_name_qp
                except Exception as e:
                    st.error(f"Erro: {e}")

        if "sq_data" in st.session_state and st.session_state.get("sq_cluster_name") == cluster_name_qp:
            sq_list = st.session_state["sq_data"].get("slowQueries", [])
            if not sq_list:
                st.success(f"✅ Nenhuma slow query em **{cluster_name_qp}**.")
            else:
                st.warning(f"⚠️ **{len(sq_list)}** slow quer{'y' if len(sq_list) == 1 else 'ies'} registradas")
                rows = []
                for q in sq_list:
                    line = q.get("line", "")
                    try:
                        dur = json.loads(line or "{}").get("attr", {}).get("durationMillis", q.get("duration", 0))
                    except Exception:
                        dur = q.get("duration", 0)
                    rows.append({
                        "Namespace":     q.get("namespace", "N/A"),
                        "Duration (ms)": dur,
                        "Log":           (line[:130] + "…") if len(line) > 130 else line,
                    })
                df_sq = pd.DataFrame(rows).sort_values("Duration (ms)", ascending=False).reset_index(drop=True)
                st.dataframe(df_sq, use_container_width=True, hide_index=True)
                if len(df_sq) >= 3:
                    fig = px.histogram(df_sq, x="Duration (ms)", nbins=20,
                                       title="Distribuição de Latência", color_discrete_sequence=["#00ED64"])
                    st.plotly_chart(plotly_dark(fig), use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 4 — SCALE
# ══════════════════════════════════════════════════════════════════════════════
with tab_scale:
    mdb_section_header("Scale", badge="Up / Down", badge_color="teal")
    st.info("O scaling causa um **rolling restart sem downtime**. O Atlas atualiza os nós um a um.")

    if not all_clusters:
        st.warning("Nenhum cluster disponível.")
    else:
        _, proj_id_sc, in_proj_sc = project_selector("sc")
        cluster_name_sc, row_sc   = cluster_selector(in_proj_sc, "sc")
        current_tier              = row_sc.get("tier", "N/A")

        curr_cost = AtlasClient.estimate_cost(current_tier, usd_brl)
        mdb_kpi_row([
            {"label": "Cluster",       "value": cluster_name_sc,
             "delta": row_sc.get("status","—"), "color": "blue"},
            {"label": "Tier Atual",    "value": current_tier,
             "delta": "dedicated" if current_tier not in ["Free/Shared"] else "shared",
             "color": "teal"},
            {"label": "Região",        "value": row_sc.get("region","—"),
             "delta": "AWS", "color": "muted"},
            {"label": "Custo Est./Mês","value": f"R$ {curr_cost['brl']:,.0f}",
             "delta": f"≈ USD {curr_cost['usd']:,}", "color": "green"},
        ])
        st.divider()

        is_nvme  = "_NVME" in current_tier
        is_free  = current_tier not in DEDICATED_TIERS and not is_nvme
        tier_list = NVME_TIERS if is_nvme else DEDICATED_TIERS

        if is_free:
            st.warning("⚠️ Clusters **M0/M2/M5** não podem ser escalados via API. Use o Atlas UI.")
        else:
            new_tier = st.select_slider(
                "Selecione o novo tier",
                options=tier_list,
                value=current_tier if current_tier in tier_list else tier_list[0],
                key="sc_slider",
            )

            if new_tier != current_tier:
                new_cost   = AtlasClient.estimate_cost(new_tier, usd_brl)
                curr_idx   = tier_list.index(current_tier) if current_tier in tier_list else 0
                new_idx    = tier_list.index(new_tier)
                direction  = "⬆️ Scale UP" if new_idx > curr_idx else "⬇️ Scale DOWN"
                delta_usd  = new_cost["usd"] - curr_cost["usd"]
                delta_brl  = new_cost["brl"] - curr_cost["brl"]
                delta_sign = "+" if delta_usd >= 0 else ""

                col_info, col_cost = st.columns(2)
                with col_info:
                    st.markdown(
                        f"**{current_tier}** → **{new_tier}**  {direction}  "
                        f"_(salto de {abs(new_idx - curr_idx)} tier{'s' if abs(new_idx-curr_idx)>1 else ''})_"
                    )
                with col_cost:
                    st.markdown(
                        f"💰 **Custo novo:** R$ {new_cost['brl']:,.0f}/mês (USD {new_cost['usd']:,})  \n"
                        f"**Delta:** {delta_sign}R$ {delta_brl:,.0f}/mês  ·  {delta_sign}USD {delta_usd:,}/mês"
                    )

                with st.form("scale_confirm_form"):
                    confirmed = st.checkbox(
                        f"Confirmo o scaling de **{cluster_name_sc}**: **{current_tier}** → **{new_tier}**"
                    )
                    if st.form_submit_button("🚀 Executar Scaling", type="primary"):
                        if not confirmed:
                            st.warning("Marque a caixa de confirmação.")
                        else:
                            with st.spinner(f"Escalando {cluster_name_sc} para {new_tier}…"):
                                try:
                                    result    = client.scale_cluster(proj_id_sc, cluster_name_sc, new_tier)
                                    new_state = result.get("stateName", "UPDATING")
                                    st.success(
                                        f"✅ Scaling iniciado! Status: **{new_state}**  \n"
                                        "O cluster entrará em UPDATING por alguns minutos."
                                    )
                                    st.cache_data.clear()
                                except Exception as e:
                                    st.error(f"Erro ao escalar: {e}")
            else:
                st.info("Mova o slider para um tier diferente do atual.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 5 — FINOPS
# ══════════════════════════════════════════════════════════════════════════════
with tab_finops:
    mdb_section_header("FinOps", badge="Estimativas", badge_color="green", sub="AWS us-east-1 · 3-node replica set")
    st.caption("Valores estimados com base em AWS us-east-1 · 3-node replica set · referência: atlas.mongodb.com/pricing")

    if not all_clusters:
        st.warning("Nenhum cluster disponível.")
    else:
        df_all = pd.DataFrame(all_clusters)

        # Cost per cluster
        df_cost = df_all.copy()
        df_cost["USD/mês"]  = df_cost["tier"].apply(lambda t: AtlasClient.estimate_cost(t, usd_brl)["usd"])
        df_cost["BRL/mês"]  = df_cost["tier"].apply(lambda t: AtlasClient.estimate_cost(t, usd_brl)["brl"])
        total_usd = df_cost["USD/mês"].sum()
        total_brl = df_cost["BRL/mês"].sum()

        # KPIs
        top_cost = df_cost.loc[df_cost["USD/mês"].idxmax(), "cluster_name"] if len(df_cost) > 0 else "—"
        invoice  = client.get_pending_invoice()
        inv_usd  = invoice.get("amountBilledCents", 0) / 100 if invoice else 0
        avg_brl  = total_brl / len(df_cost) if len(df_cost) > 0 else 0

        mdb_kpi_row([
            {"label": "Total Est. USD/Mês", "value": f"${total_usd:,.0f}",
             "delta": "estimativa AWS us-east-1", "color": "green"},
            {"label": "Total Est. BRL/Mês", "value": f"R$ {total_brl:,.0f}",
             "delta": f"cotação R$ {usd_brl:.2f}/USD", "color": "teal"},
            {"label": "Média por Cluster",  "value": f"R$ {avg_brl:,.0f}",
             "delta": f"{len(df_cost)} cluster(s)", "color": "blue"},
            {"label": "Maior Custo",        "value": top_cost,
             "delta": "cluster mais caro", "color": "yellow"},
            {"label": "Fatura Atlas (USD)", "value": f"${inv_usd:,.2f}",
             "delta": "acumulado no período", "color": "orange"},
        ])
        st.divider()

        # Cost table
        df_display_fin = df_cost[["project_name","cluster_name","tier","region","USD/mês","BRL/mês"]].copy()
        df_display_fin = df_display_fin.rename(columns={
            "project_name": "Projeto", "cluster_name": "Cluster",
            "tier": "Tier", "region": "Região",
        })
        df_display_fin["USD/mês"] = df_display_fin["USD/mês"].apply(lambda x: f"${x:,.0f}")
        df_display_fin["BRL/mês"] = df_display_fin["BRL/mês"].apply(lambda x: f"R$ {x:,.0f}")
        st.dataframe(df_display_fin, use_container_width=True, hide_index=True)

        # Charts
        st.divider()
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            st.markdown("**Custo por Cluster (USD)**")
            df_chart = df_cost.sort_values("USD/mês", ascending=True).tail(15)
            fig_cost = px.bar(
                df_chart, x="USD/mês", y="cluster_name", orientation="h",
                color="USD/mês", color_continuous_scale=["#003020","#00ED64"],
                labels={"cluster_name": "", "USD/mês": "USD/mês"},
            )
            fig_cost.update_coloraxes(showscale=False)
            st.plotly_chart(plotly_dark(fig_cost, 350), use_container_width=True)

        with col_f2:
            st.markdown("**Custo por Projeto (USD)**")
            proj_cost = df_cost.groupby("project_name")["USD/mês"].sum().reset_index()
            fig_proj  = px.pie(
                proj_cost, names="project_name", values="USD/mês",
                hole=0.4, color_discrete_sequence=px.colors.sequential.Greens_r,
            )
            st.plotly_chart(plotly_dark(fig_proj, 350), use_container_width=True)

        # Scale simulator
        st.divider()
        st.markdown("### 🔮 Simulador de Custo")
        col_s1, col_s2, col_s3 = st.columns(3)
        with col_s1:
            all_names  = [c["cluster_name"] for c in all_clusters]
            sim_name   = st.selectbox("Cluster", all_names, key="fin_sim_cluster")
            sim_row    = next((c for c in all_clusters if c["cluster_name"] == sim_name), {})
            sim_current = sim_row.get("tier","M10")
        with col_s2:
            all_tiers  = DEDICATED_TIERS + NVME_TIERS
            sim_new    = st.selectbox("Novo Tier", all_tiers,
                                      index=all_tiers.index(sim_current) if sim_current in all_tiers else 0,
                                      key="fin_sim_tier")
        with col_s3:
            curr_c = AtlasClient.estimate_cost(sim_current, usd_brl)
            new_c  = AtlasClient.estimate_cost(sim_new, usd_brl)
            delta  = new_c["brl"] - curr_c["brl"]
            sign   = "+" if delta >= 0 else ""
            st.metric(
                f"Delta Mensal",
                f"{sign}R$ {delta:,.0f}",
                f"{sign}USD {new_c['usd'] - curr_c['usd']:,}",
                delta_color="inverse" if delta < 0 else "normal",
            )

        # Tier reference table
        with st.expander("📋 Tabela de Preços de Referência (AWS us-east-1)"):
            ref_rows = [
                {"Tier": t, "USD/mês": f"${v:,}", "BRL/mês": f"R$ {round(v*usd_brl):,}", "USD/hora": f"${v/730:.2f}"}
                for t, v in TIER_PRICING_USD.items() if v > 0
            ]
            st.dataframe(pd.DataFrame(ref_rows), use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 6 — COMPARE
# ══════════════════════════════════════════════════════════════════════════════
with tab_compare:
    mdb_section_header("Comparar Clusters", badge="Side-by-side", badge_color="blue")

    if len(all_clusters) < 2:
        st.warning("São necessários pelo menos 2 clusters para comparar.")
    else:
        col_a, col_b = st.columns(2)
        all_names = [f"{c['project_name']} / {c['cluster_name']}" for c in all_clusters]

        with col_a:
            st.markdown("### 🔵 Cluster A")
            sel_a = st.selectbox("", all_names, index=0, key="cmp_a")
        with col_b:
            st.markdown("### 🟠 Cluster B")
            sel_b = st.selectbox("", all_names, index=min(1, len(all_names)-1), key="cmp_b")

        if st.button("🔍 Comparar", type="primary", key="btn_compare"):
            with st.spinner("Coletando dados de ambos os clusters…"):
                def fetch_cluster_metrics(display_name: str):
                    proj_name, cname = display_name.split(" / ", 1)
                    row     = next((c for c in all_clusters if c["project_name"] == proj_name and c["cluster_name"] == cname), {})
                    proj_id = row.get("project_id", "")
                    status  = row.get("status", "")
                    n_pa = n_sq = 0
                    # Não tenta buscar processos de clusters pausados
                    if status not in ("PAUSED", "DELETING"):
                        try:
                            pid = client.get_primary(proj_id, cname)
                            if pid:
                                pa_r = client.get_suggested_indexes(proj_id, pid)
                                sq_r = client.get_slow_queries(proj_id, pid)
                                n_pa = len(pa_r.get("suggestedIndexes", []))
                                n_sq = len(sq_r.get("slowQueries", []))
                        except Exception:
                            pass
                    cost   = AtlasClient.estimate_cost(row.get("tier", "Free/Shared"), usd_brl)
                    health = calculate_health_score(status, n_pa, n_sq, row.get("mongo_version", "0"))
                    return {
                        "Label":        display_name,
                        "Tier":         row.get("tier", "—"),
                        "Região":       row.get("region", "—"),
                        "Status":       STATUS_ICON.get(status, f"⚪ {status}"),
                        "MongoDB":      row.get("mongo_version", "—"),
                        "PA Sugestões": n_pa,
                        "Slow Queries": n_sq,
                        "Health Score": health["score"],
                        "Grade":        health["grade"],
                        "USD/mês":      cost["usd"],
                        "BRL/mês":      cost["brl"],
                    }

                data_a = fetch_cluster_metrics(sel_a)
                data_b = fetch_cluster_metrics(sel_b)
                st.session_state["cmp_a_data"] = data_a
                st.session_state["cmp_b_data"] = data_b

        if "cmp_a_data" in st.session_state and "cmp_b_data" in st.session_state:
            da = st.session_state["cmp_a_data"]
            db_ = st.session_state["cmp_b_data"]

            # Side-by-side table
            st.divider()

            # ── Tabela com destaque visual (🏆 melhor, ⚠️ pior) ──
            HIGHER_BETTER = {"Health Score"}
            LOWER_BETTER  = {"PA Sugestões", "Slow Queries", "USD/mês", "BRL/mês"}

            metrics_order = ["Tier","Região","Status","MongoDB","PA Sugestões","Slow Queries",
                             "Health Score","Grade","USD/mês","BRL/mês"]
            rows_table = []
            for m in metrics_order:
                va = da.get(m, "—")
                vb = db_.get(m, "—")

                # Formata valores numéricos
                if m == "USD/mês":
                    va_str, vb_str = f"${va:,}", f"${vb:,}"
                elif m == "BRL/mês":
                    va_str, vb_str = f"R$ {va:,}", f"R$ {vb:,}"
                else:
                    va_str, vb_str = str(va), str(vb)

                # Adiciona badge de comparação em métricas numéricas
                if isinstance(va, (int, float)) and isinstance(vb, (int, float)) and va != vb:
                    if m in HIGHER_BETTER:
                        winner = "A" if va > vb else "B"
                    elif m in LOWER_BETTER:
                        winner = "A" if va < vb else "B"
                    else:
                        winner = None
                    if winner == "A":
                        va_str = f"🏆 {va_str}"
                        vb_str = f"⚠️  {vb_str}"
                    elif winner == "B":
                        va_str = f"⚠️  {va_str}"
                        vb_str = f"🏆 {vb_str}"

                rows_table.append({"Métrica": m, "🔵 Cluster A": va_str, "🟠 Cluster B": vb_str})
            st.dataframe(pd.DataFrame(rows_table), use_container_width=True, hide_index=True)

            # ── Radar chart (só se os clusters tiverem dados diferentes) ──
            st.divider()
            dims = ["Health Score", "PA Sugestões", "Slow Queries", "USD/mês"]
            max_vals = {
                "Health Score": 100,
                "PA Sugestões": max(da["PA Sugestões"], db_["PA Sugestões"], 1),
                "Slow Queries": max(da["Slow Queries"],  db_["Slow Queries"],  1),
                "USD/mês":      max(da["USD/mês"],       db_["USD/mês"],       1),
            }

            def norm(key, val):
                if key == "Health Score":
                    return val / max_vals[key]
                return 1 - (val / max_vals[key])

            vals_a = [norm(d, da[d]) for d in dims]
            vals_b = [norm(d, db_[d]) for d in dims]
            labels = ["Health Score", "Index Health", "Query Health", "Cost Efficiency"]

            fig_radar = go.Figure()
            for vals, name, color, fill in [
                (vals_a, f"🔵 {sel_a.split('/')[-1].strip()}", "#1E90FF", "rgba(30,144,255,0.15)"),
                (vals_b, f"🟠 {sel_b.split('/')[-1].strip()}", "#FF8C00", "rgba(255,140,0,0.15)"),
            ]:
                fig_radar.add_trace(go.Scatterpolar(
                    r=vals + [vals[0]], theta=labels + [labels[0]],
                    fill="toself", name=name,
                    line_color=color, fillcolor=fill,
                ))
            fig_radar.update_layout(
                polar=dict(
                    radialaxis=dict(visible=True, range=[0, 1], tickfont=dict(color="#B8C4C2"),
                                   gridcolor="rgba(0,237,100,0.13)", linecolor="rgba(0,237,100,0.13)"),
                    angularaxis=dict(tickfont=dict(color="#B8C4C2")),
                    bgcolor="#001a24",
                ),
                showlegend=True, height=420,
                paper_bgcolor="rgba(0,0,0,0)", font_color="#B8C4C2",
                legend=dict(bgcolor="#002235", bordercolor="rgba(0,237,100,0.19)", borderwidth=1),
                margin=dict(t=40, b=20, l=40, r=40),
            )

            if vals_a == vals_b:
                st.info("ℹ️ Os dois clusters têm métricas idênticas — o gráfico radar seria sobreposto.")
            else:
                st.plotly_chart(fig_radar, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 7 — HEALTH SCORE
# ══════════════════════════════════════════════════════════════════════════════
with tab_health:
    mdb_section_header("Health Score", badge="0–100", badge_color="green")
    st.markdown("Análise de saúde baseada em Performance Advisor, Slow Queries, Status e versão do MongoDB.")

    if not all_clusters:
        st.warning("Nenhum cluster disponível.")
    else:
        _, proj_id_hs, in_proj_hs = project_selector("hs")
        cluster_name_hs, row_hs   = cluster_selector(in_proj_hs, "hs")

        if st.button("🏥 Calcular Health Score", type="primary", key="btn_hs"):
            with st.spinner("Coletando métricas de saúde…"):
                try:
                    pid_hs = client.get_primary(proj_id_hs, cluster_name_hs)
                    n_pa = n_sq = 0
                    if pid_hs:
                        pa_hs = client.get_suggested_indexes(proj_id_hs, pid_hs)
                        sq_hs = client.get_slow_queries(proj_id_hs, pid_hs)
                        n_pa  = len(pa_hs.get("suggestedIndexes", []))
                        n_sq  = len(sq_hs.get("slowQueries", []))

                    hs_result = calculate_health_score(
                        row_hs.get("status",""),
                        n_pa, n_sq,
                        row_hs.get("mongo_version","0"),
                    )
                    st.session_state["hs_result"]         = hs_result
                    st.session_state["hs_result_cluster"] = cluster_name_hs
                    st.session_state["hs_n_pa"]     = n_pa
                    st.session_state["hs_n_sq"]     = n_sq
                except Exception as e:
                    st.error(f"Erro: {e}")

        if "hs_result" in st.session_state and st.session_state.get("hs_result_cluster") == cluster_name_hs:
            hs  = st.session_state["hs_result"]
            n_pa = st.session_state.get("hs_n_pa", 0)
            n_sq = st.session_state.get("hs_n_sq", 0)

            col_gauge, col_info = st.columns([2, 3])
            with col_gauge:
                st.plotly_chart(health_gauge_fig(hs["score"], hs["color"]), use_container_width=True)
                grade_color = hs["color"]
                grade_val   = hs["grade"]
                grade_score = hs["score"]
                st.markdown(
                    f"<div style='text-align:center'>"
                    f"<span class='health-grade' style='color:{grade_color}'>{grade_val}</span>"
                    f"<br><span style='color:#B8C4C2;font-size:0.8rem'>Grade &middot; {grade_score}/100</span>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

            with col_info:
                st.markdown(f"### `{cluster_name_hs}`")
                mdb_kpi_row([
                    {"label": "Tier",         "value": row_hs.get("tier","—"),
                     "delta": "dedicated", "color": "teal"},
                    {"label": "PA Sugestões", "value": str(n_pa),
                     "delta": f"↑ {n_pa} pendentes" if n_pa > 0 else "✓ nenhuma",
                     "delta_type": "down" if n_pa > 0 else "up",
                     "color": "yellow" if n_pa > 0 else "green"},
                    {"label": "Slow Queries", "value": str(n_sq),
                     "delta": f"↑ {n_sq} registradas" if n_sq > 0 else "✓ nenhuma",
                     "delta_type": "down" if n_sq > 0 else "up",
                     "color": "orange" if n_sq > 0 else "green"},
                ])
                st.divider()

                if hs["issues"]:
                    st.markdown("**📋 Penalizações:**")
                    for issue in hs["issues"]:
                        st.markdown(f"- 🔴 {issue}")
                else:
                    st.success("✅ Nenhuma penalização encontrada — cluster saudável!")

                st.divider()
                interpretation = {
                    "A": "Cluster excelente. Nenhuma ação imediata necessária.",
                    "B": "Cluster saudável com pequenas oportunidades de melhoria.",
                    "C": "Atenção requerida. Existem otimizações importantes a aplicar.",
                    "D": "Cluster com problemas significativos. Ação recomendada em breve.",
                    "F": "Cluster crítico. Intervenção urgente necessária.",
                }
                st.info(f"**Grade {hs['grade']}:** {interpretation.get(hs['grade'],'—')}")

            # Breakdown bar
            st.divider()
            status_val = row_hs.get("status", "")
            # PAUSED conta como não-IDLE mas merece nota diferente
            status_pts = 20 if status_val == "IDLE" else (10 if status_val == "PAUSED" else 0)
            score_breakdown = {
                "Status":         status_pts,
                "Index Health":   max(0, 30 - min(n_pa * 5, 30)),
                "Query Health":   max(0, 30 - min(n_sq * 2, 30)),
                "MongoDB Version": 10 if int(row_hs.get("mongo_version","0").split(".")[0] or 0) >= 7 else 0,
                "Base Score":     10,
            }
            bar_colors = []
            for v in score_breakdown.values():
                if v >= 20:   bar_colors.append("#00ED64")
                elif v >= 10: bar_colors.append("#FFA500")
                else:         bar_colors.append("#FF4444")

            fig_breakdown = px.bar(
                x=list(score_breakdown.values()),
                y=list(score_breakdown.keys()),
                orientation="h",
                labels={"x": "Pontos", "y": ""},
                title="Composição do Score",
            )
            fig_breakdown.update_traces(marker_color=bar_colors)
            fig_breakdown.update_layout(
                height=250, plot_bgcolor="#0d1117", paper_bgcolor="#0d1117",
                font_color="#ccc", margin=dict(t=40, b=10), xaxis=dict(range=[0, 35]),
            )
            st.plotly_chart(fig_breakdown, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# TAB 8 — AI CHAT  (persistência MongoDB Atlas + timer + rendering melhorado)
# ══════════════════════════════════════════════════════════════════════════════
with tab_chat:
    import re as _re
    from chat_memory import (
        init_db as _init_db, new_conversation, add_message,
        load_messages, list_conversations, search_conversations,
        delete_conversation, format_relative_time,
    )

    mdb_section_header("AI Chat", badge="Claude Sonnet 4.6", badge_color="blue")

    if not ant_key:
        st.warning("Configure a **Anthropic API Key** na sidebar para usar o AI Chat.")
        st.stop()

    # ── Verifica connection string para persistência ──
    _chat_persist = bool(mongo_uri)
    if _chat_persist:
        try:
            _init_db(mongo_uri)
        except Exception as _e:
            st.warning(f"⚠️ MongoDB indisponível — histórico desativado: {_e}")
            _chat_persist = False
    else:
        st.info("💡 Configure a **Connection String** na sidebar para persistir o histórico no Atlas.")

    # ── Helper: render assistant message with code-block splitting ──
    def _render_assistant(content: str, elapsed_ms: int = 0):
        """Renderiza a resposta do assistente separando blocos de código do markdown."""
        if elapsed_ms:
            st.caption(f"⏱️ Resposta em **{elapsed_ms/1000:.1f}s**")
        parts = _re.split(r"(```[\w]*\n[\s\S]*?```)", content)
        for part in parts:
            if part.startswith("```"):
                lines = part.split("\n")
                lang  = lines[0].replace("```", "").strip() or "text"
                code  = "\n".join(lines[1:]).rstrip("`").strip()
                st.code(code, language=lang)
            elif part.strip():
                st.markdown(part)

    # ══════════════════════════════════════════════════════════════════════
    # Layout: coluna de histórico | coluna de chat
    # ══════════════════════════════════════════════════════════════════════
    col_hist, col_main = st.columns([1, 3])

    # ── COLUNA ESQUERDA — Histórico de conversas ──────────────────────────
    with col_hist:
        st.markdown("#### 🗂️ Histórico")

        if not _chat_persist:
            st.caption("Configure a Connection String na sidebar para persistir no Atlas.")
        else:
            search_q = st.text_input("🔍 Buscar", placeholder="keyword…", key="chat_search",
                                     label_visibility="collapsed")
            try:
                hist_rows = (search_conversations(mongo_uri, search_q)
                             if search_q else list_conversations(mongo_uri, limit=20))
            except Exception:
                hist_rows = []

            if not hist_rows:
                st.caption("Nenhuma conversa salva ainda.")
            else:
                for row in hist_rows:
                    label     = f"{'📎 ' if row.get('cluster') else ''}{row['title']}"
                    sub       = f"{format_relative_time(row['updated_at'])}  ·  {row.get('msg_count',0)} msgs"
                    is_active = st.session_state.get("chat_conv_id") == row["id"]
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        if st.button(label, key=f"load_conv_{row['id']}", help=sub,
                                     use_container_width=True,
                                     type="primary" if is_active else "secondary"):
                            msgs = load_messages(mongo_uri, row["id"])
                            st.session_state["chat_messages"] = [
                                {"role": m["role"], "content": m["content"],
                                 "elapsed_ms": m.get("elapsed_ms", 0)}
                                for m in msgs
                            ]
                            st.session_state["chat_conv_id"] = row["id"]
                            st.session_state.pop("chat_context_name", None)
                            st.session_state.pop("chat_system", None)
                            st.rerun()
                    with c2:
                        if st.button("🗑", key=f"del_conv_{row['id']}", help="Deletar"):
                            delete_conversation(mongo_uri, row["id"])
                            if st.session_state.get("chat_conv_id") == row["id"]:
                                st.session_state.pop("chat_conv_id",  None)
                                st.session_state.pop("chat_messages", None)
                            st.rerun()

        st.divider()
        if st.button("➕ Nova Conversa", use_container_width=True):
            st.session_state.pop("chat_messages",     None)
            st.session_state.pop("chat_conv_id",      None)
            st.session_state.pop("chat_context_name", None)
            st.session_state.pop("chat_system",       None)
            st.rerun()

    # ── COLUNA DIREITA — Chat principal ───────────────────────────────────
    with col_main:

        # ── Context loader ──
        with st.expander("🔧 Contexto do Cluster (enriquece as respostas)", expanded=False):
            if all_clusters:
                _, proj_id_ch, in_proj_ch = project_selector("ch")
                cluster_name_ch, _        = cluster_selector(in_proj_ch, "ch")
                if st.button("📥 Carregar Contexto", key="btn_ctx"):
                    with st.spinner("Carregando dados e métricas do cluster…"):
                        try:
                            pid_ch  = client.get_primary(proj_id_ch, cluster_name_ch)
                            full_c  = client.get_cluster(proj_id_ch, cluster_name_ch)
                            pa_ch   = client.get_suggested_indexes(proj_id_ch, pid_ch) if pid_ch else {}
                            sq_ch   = client.get_slow_queries(proj_id_ch, pid_ch) if pid_ch else {}
                            meas_ch = client.get_measurements(proj_id_ch, pid_ch) if pid_ch else {}
                            sys_p   = build_chat_system_prompt(full_c, pa_ch, sq_ch, meas_ch)
                            st.session_state["chat_system"]       = sys_p
                            st.session_state["chat_context_name"] = cluster_name_ch
                            st.session_state["chat_measurements"] = meas_ch
                            if meas_ch and "error" not in meas_ch:
                                cpu   = meas_ch.get("cpu_pct", 0)
                                mem   = meas_ch.get("memory_used_gb", 0)
                                conns = meas_ch.get("connections", 0)
                                st.success(
                                    f"✅ Contexto carregado! "
                                    f"CPU: **{cpu}%** · Mem: **{mem}GB** · Conexões: **{conns}**"
                                )
                            else:
                                st.success(f"✅ Contexto de `{cluster_name_ch}` carregado.")
                        except Exception as e:
                            st.error(f"Erro: {e}")
            else:
                st.info("Nenhum cluster disponível.")

        # ── Status bar ──
        bar_l, bar_r = st.columns([3, 2])
        with bar_l:
            if "chat_context_name" in st.session_state:
                meas = st.session_state.get("chat_measurements", {})
                badge_extra = ""
                if meas and "error" not in meas:
                    badge_extra = f" · CPU {meas.get('cpu_pct',0)}% · {meas.get('connections',0)} conn"
                st.markdown(
                    f'<div class="chat-context-badge">📎 <strong>{st.session_state["chat_context_name"]}</strong>'
                    f'{badge_extra}</div>',
                    unsafe_allow_html=True,
                )
            else:
                st.caption("💡 Sem contexto — respondendo questões gerais de MongoDB.")
        with bar_r:
            msgs_now = st.session_state.get("chat_messages", [])
            t1, t2 = st.columns(2)
            with t1:
                if msgs_now:
                    hist_md   = "\n\n".join(
                        f"**{'Você' if m['role']=='user' else 'Claude'}:**\n{m['content']}"
                        for m in msgs_now
                    )
                    pdf_bytes = generate_pdf_report(
                        st.session_state.get("chat_context_name", "Chat"), hist_md
                    )
                    st.download_button(
                        "📄 Exportar (.md)", data=pdf_bytes,
                        file_name=f"maestro_{datetime.now().strftime('%Y%m%d_%H%M')}.md",
                        mime="text/markdown", use_container_width=True,
                    )
            with t2:
                if st.button("🗑️ Limpar", use_container_width=True):
                    st.session_state.pop("chat_messages",      None)
                    st.session_state.pop("chat_conv_id",       None)
                    st.session_state.pop("chat_context_name",  None)
                    st.session_state.pop("chat_system",        None)
                    st.session_state.pop("chat_measurements",  None)
                    st.rerun()

        st.divider()

        # ── Initialize ──
        if "chat_messages" not in st.session_state:
            st.session_state["chat_messages"] = []

        # ── Quick prompts (só quando chat vazio) ──
        if not st.session_state["chat_messages"]:
            st.markdown("**💡 Sugestões de perguntas:**")
            suggestions = [
                "Quais índices estão sendo sugeridos para o cluster e por quê?",
                "Como funciona o WiredTiger e por que ele é importante para performance?",
                "Quando devo usar sharding vs fazer scale up do tier?",
                "Explique o Bucket Pattern para séries temporais financeiras",
                "Quais indicadores mostram que meu cluster precisa de scale up?",
                "Compare Atlas Search vs Elasticsearch para busca full-text",
            ]
            cols = st.columns(2)
            for i, sug in enumerate(suggestions):
                with cols[i % 2]:
                    if st.button(sug, key=f"sug_{i}", use_container_width=True):
                        st.session_state["chat_messages"].append(
                            {"role": "user", "content": sug, "elapsed_ms": 0}
                        )
                        st.session_state["_pending_response"] = True
                        st.rerun()

        # ── Renderiza histórico completo ──
        for msg in st.session_state["chat_messages"]:
            with st.chat_message(msg["role"]):
                if msg["role"] == "assistant":
                    _render_assistant(msg["content"], msg.get("elapsed_ms", 0))
                else:
                    st.markdown(msg["content"])

        # ── Fase 2: stream da resposta se há pergunta pendente ──
        if st.session_state.get("_pending_response"):
            st.session_state.pop("_pending_response")

            # Garante conversa salva no Atlas
            if "chat_conv_id" not in st.session_state and _chat_persist:
                st.session_state["chat_conv_id"] = new_conversation(
                    mongo_uri, st.session_state.get("chat_context_name", "")
                )
            # Salva a mensagem do usuário no Atlas (ainda não salva)
            last_user = st.session_state["chat_messages"][-1]["content"]
            if _chat_persist and "chat_conv_id" in st.session_state:
                add_message(mongo_uri, st.session_state["chat_conv_id"], "user", last_user)

            with st.chat_message("assistant"):
                timer_ph  = st.empty()
                stream_ph = st.empty()
                full_response = ""
                elapsed_ms    = 0
                t_start = time.time()
                try:
                    sys_prompt = st.session_state.get("chat_system", "")
                    api_msgs   = [
                        {"role": m["role"], "content": m["content"]}
                        for m in st.session_state["chat_messages"]
                    ]
                    for chunk in stream_chat(api_msgs, sys_prompt):
                        full_response += chunk
                        elapsed = time.time() - t_start
                        timer_ph.caption(f"⏱️ Gerando… {elapsed:.1f}s")
                        stream_ph.markdown(full_response + "▌")
                    elapsed_ms = int((time.time() - t_start) * 1000)
                    timer_ph.empty()
                    stream_ph.empty()
                    _render_assistant(full_response, elapsed_ms)
                except Exception as e:
                    elapsed_ms    = int((time.time() - t_start) * 1000)
                    full_response = f"❌ Erro ao chamar Claude: {e}"
                    stream_ph.markdown(full_response)

            st.session_state["chat_messages"].append(
                {"role": "assistant", "content": full_response, "elapsed_ms": elapsed_ms}
            )
            if _chat_persist and "chat_conv_id" in st.session_state:
                add_message(mongo_uri, st.session_state["chat_conv_id"],
                            "assistant", full_response, elapsed_ms)

        # ── Fase 1: captura input e faz rerun para renderizar antes de streamar ──
        if prompt := st.chat_input("Pergunte sobre MongoDB, performance, indexação, Atlas…"):
            st.session_state["chat_messages"].append(
                {"role": "user", "content": prompt, "elapsed_ms": 0}
            )
            st.session_state["_pending_response"] = True
            st.rerun()
