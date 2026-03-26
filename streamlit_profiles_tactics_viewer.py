"""Grevs CPL pages built from local CSV data files.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

import base64
import html
import importlib.util
from pathlib import Path
import re
import textwrap

import pandas as pd
import streamlit as st


def _load_plotly_modules():
    """Load Plotly modules when available, otherwise return (None, None)."""
    if importlib.util.find_spec("plotly.graph_objects") is None:
        return None, None
    try:
        import plotly.graph_objects as graph_objects
        from plotly.subplots import make_subplots as subplot_builder
    except Exception:
        return None, None
    return graph_objects, subplot_builder


go, make_subplots = _load_plotly_modules()

st.set_page_config(page_title="Grevs CPL Pages", layout="wide")

DATA_DIR = Path(__file__).parent / "data"
PLAYER_CSV = DATA_DIR / "PlayerDataMatser.csv"
TACTICS_CSV = DATA_DIR / "TacticsDataMaster.csv"
ACHIEVEMENTS_CSV = DATA_DIR / "Achievements.csv"
PLAYER_META_CSV_CANDIDATES = (
    DATA_DIR / "player.csv",
    DATA_DIR / "Player.csv",
    DATA_DIR / "players.csv",
)
IMAGE_FOLDERS = {
    "competition": "competition_logos",
    "map": "map_images",
    "achievement": "Achievement_png",
    "team": "team_logos",
    "player": "player_photos",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
APP_ROOT = Path(__file__).parent
MEDISPORTS_LOGO = APP_ROOT / "team_logos" / "ᴍᴇᴅɪꜱᴘᴏʀᴛꜱ ⓜ.png"
CPL_LOGO = APP_ROOT / "competition_logos" / "cpl.png"
TIER_COLOR_MAP = {"S": "#f5c451", "A": "#9c6df6", "B": "#5ea9ff", "C": "#4ed083"}
COUNTRY_TO_ALPHA2 = {
    "belarus": "BY",
    "china": "CN",
    "japan": "JP",
    "slovakia": "SK",
    "greece": "GR",
    "russia": "RU",
    "latvia": "LV",
    "ukraine": "UA",
    "poland": "PL",
    "sweden": "SE",
    "denmark": "DK",
    "norway": "NO",
    "finland": "FI",
    "germany": "DE",
    "france": "FR",
    "spain": "ES",
    "italy": "IT",
    "portugal": "PT",
    "united kingdom": "GB",
    "uk": "GB",
    "england": "GB",
    "scotland": "GB",
    "ireland": "IE",
    "netherlands": "NL",
    "belgium": "BE",
    "austria": "AT",
    "switzerland": "CH",
    "czech republic": "CZ",
    "czechia": "CZ",
    "romania": "RO",
    "serbia": "RS",
    "croatia": "HR",
    "bosnia and herzegovina": "BA",
    "slovenia": "SI",
    "hungary": "HU",
    "turkey": "TR",
    "israel": "IL",
    "kazakhstan": "KZ",
    "mongolia": "MN",
    "south korea": "KR",
    "korea": "KR",
    "vietnam": "VN",
    "thailand": "TH",
    "philippines": "PH",
    "malaysia": "MY",
    "singapore": "SG",
    "indonesia": "ID",
    "india": "IN",
    "pakistan": "PK",
    "australia": "AU",
    "new zealand": "NZ",
    "united states": "US",
    "usa": "US",
    "canada": "CA",
    "mexico": "MX",
    "brazil": "BR",
    "argentina": "AR",
    "chile": "CL",
    "uruguay": "UY",
}

PLOTLY_FONT_COLOR = "#dbe4f0"
PLOTLY_GRID_COLOR = "rgba(157, 167, 189, 0.16)"
PLOTLY_BG_COLOR = "rgba(0, 0, 0, 0)"
PLOTLY_PANEL_BG_COLOR = "rgba(12, 18, 29, 0.74)"


def _render_plotly_unavailable() -> None:
    st.warning("Plotly is unavailable in this environment. Install `plotly` to render dashboard charts.")


def _wrap_labels(labels: pd.Series, width: int = 26) -> list[str]:
    wrapped_labels = []
    for label in labels.astype(str):
        wrapped_labels.append("<br>".join(textwrap.wrap(label, width=width, break_long_words=False)) or label)
    return wrapped_labels


def _apply_plotly_dark_style(fig, *, height: int | None = None, margin: dict | None = None, hovermode: str = "closest"):
    if height is not None:
        fig.update_layout(height=height)
    fig.update_layout(
        margin=margin or dict(l=80, r=24, t=48, b=56),
        paper_bgcolor=PLOTLY_BG_COLOR,
        plot_bgcolor=PLOTLY_PANEL_BG_COLOR,
        font=dict(color=PLOTLY_FONT_COLOR, size=12),
        hoverlabel=dict(bgcolor="#0f1727", bordercolor="#243146", font=dict(color="#f5f7fb", size=12)),
        legend=dict(font=dict(size=11), orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode=hovermode,
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=PLOTLY_GRID_COLOR,
        zerolinecolor="rgba(157, 167, 189, 0.24)",
        automargin=True,
        tickfont=dict(size=11),
        title_font=dict(size=12),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=PLOTLY_GRID_COLOR,
        zerolinecolor="rgba(157, 167, 189, 0.24)",
        automargin=True,
        tickfont=dict(size=11),
        title_font=dict(size=12),
    )
    return fig


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .panel-card {
            background: linear-gradient(165deg, #101721 0%, #0b1018 100%);
            border: 1px solid rgba(151, 166, 195, 0.22);
            border-radius: 16px;
            padding: 20px 22px;
            margin-bottom: 16px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.24);
        }
        .panel-muted {
            color: #9da7bd;
            font-size: 0.76rem;
            opacity: 0.78;
            margin-bottom: 0.2rem;
        }
        .panel-title {
            color: #f0f3f9;
            font-size: 1.1rem;
            font-weight: 700;
            margin-bottom: 0.25rem;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        .overview-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .stat-chip {
            border: 1px solid rgba(151, 166, 195, 0.2);
            border-radius: 10px;
            padding: 7px 9px;
            background: rgba(16, 23, 36, 0.72);
            min-height: 70px;
        }
        .stat-label { color: #9da7bd; font-size: 0.78rem; }
        .stat-value { color: #f5f7fb; font-size: 1.15rem; font-weight: 800; line-height: 1.12; }
        .stat-trend { font-size: 0.66rem; margin-top: 4px; font-weight: 600; opacity: 0.72; }
        .trend-good { color: #31d17b; }
        .trend-mid { color: #f0be4f; }
        .trend-bad { color: #ff6c7a; }
        .chip-good {
            border-color: rgba(49, 209, 123, 0.42);
            background: linear-gradient(180deg, rgba(18, 47, 37, 0.82), rgba(14, 27, 24, 0.76));
        }
        .chip-mid {
            border-color: rgba(240, 190, 79, 0.4);
            background: linear-gradient(180deg, rgba(57, 48, 27, 0.8), rgba(28, 24, 18, 0.76));
        }
        .chip-bad {
            border-color: rgba(255, 108, 122, 0.44);
            background: linear-gradient(180deg, rgba(66, 31, 37, 0.8), rgba(30, 18, 23, 0.76));
        }
        .stat-meter {
            width: 100%;
            background: rgba(151, 166, 195, 0.2);
            border-radius: 999px;
            overflow: hidden;
            height: 4px;
            margin-top: 6px;
        }
        .stat-meter-fill {
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #ff6c7a 0%, #f0be4f 50%, #31d17b 100%);
        }
        .player-card-layout {
            display: grid;
            grid-template-columns: 140px 1fr;
            gap: 14px;
            align-items: start;
        }
        .player-headshot {
            width: 100%;
            border-radius: 12px;
            border: 1px solid rgba(151, 166, 195, 0.35);
        }
        .top-identity-grid {
            display: grid;
            grid-template-columns: 1.4fr 1fr 1.05fr;
            gap: 10px;
            align-items: stretch;
        }
        .identity-strip {
            border: 1px solid rgba(151, 166, 195, 0.2);
            border-radius: 12px;
            padding: 12px;
            background: rgba(12, 18, 29, 0.65);
        }
        .identity-strip-main {
            display: grid;
            grid-template-columns: 114px 1fr;
            gap: 10px;
            align-items: center;
        }
        .portrait-frame {
            border: 1px solid rgba(104, 143, 210, 0.5);
            border-radius: 10px;
            padding: 4px;
            background: linear-gradient(180deg, rgba(41, 59, 97, 0.25), rgba(15, 21, 34, 0.5));
        }
        .portrait-strip {
            margin-top: 4px;
            font-size: 0.7rem;
            color: #a8b8da;
            display: grid;
            gap: 2px;
        }
        .team-line {
            color: #c9d5ef;
            margin-top: 3px;
            display: flex;
            align-items: center;
            gap: 8px;
        }
        .achievement-inline-list {
            display: flex;
            flex-wrap: wrap;
            justify-content: flex-start;
            align-items: flex-start;
            gap: 6px;
            margin-top: 4px;
        }
        .achievement-inline-list-single {
            justify-content: flex-start;
        }
        .achievement-inline-item {
            width: 102px;
            height: 124px;
            border: 1px solid rgba(151, 166, 195, 0.34);
            border-radius: 10px;
            background: linear-gradient(180deg, rgba(22, 31, 47, 0.92), rgba(10, 16, 27, 0.94));
            display: block;
            flex: 0 0 102px;
            overflow: hidden;
            box-shadow: inset 0 0 0 1px rgba(9, 13, 21, 0.65);
        }
        .achievement-season {
            position: absolute;
            top: 6px;
            left: 8px;
            right: 34px;
            color: #d7e3ff;
            font-size: 0.62rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            font-weight: 800;
            text-align: left;
            z-index: 2;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.75);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .achievement-image-wrap {
            position: relative;
            width: 100%;
            height: 100%;
            overflow: hidden;
            border: none;
            background: radial-gradient(circle at 50% 44%, rgba(43, 62, 97, 0.42), rgba(10, 15, 24, 0.92));
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .achievement-inline-item img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
            display: block;
            padding: 18px 8px 22px;
            box-sizing: border-box;
        }
        .achievement-tier-icon {
            position: absolute;
            top: 6px;
            right: 7px;
            min-width: 18px;
            height: 18px;
            border-radius: 999px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.6rem;
            font-weight: 900;
            letter-spacing: 0.02em;
            border: none;
            background: rgba(10, 15, 24, 0.94);
            z-index: 2;
        }
        .achievement-inline-name {
            position: absolute;
            left: 6px;
            right: 6px;
            bottom: 6px;
            color: #f5f7fb;
            font-weight: 800;
            line-height: 1.2;
            font-size: 0.54rem;
            letter-spacing: 0.04em;
            text-transform: uppercase;
            text-align: center;
            z-index: 2;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.85);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        .quick-row {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .profile-label {
            font-size: 0.73rem;
            color: #9da7bd;
            text-transform: uppercase;
            letter-spacing: 0.09em;
        }
        .profile-name {
            font-size: 2.4rem;
            color: #f5f7fb;
            font-weight: 900;
            margin-top: 1px;
            line-height: 1.05;
        }
        .identity-meta-line {
            color: #c9d5ef;
            margin-top: 3px;
            font-size: 0.8rem;
        }
        .identity-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .identity-kv {
            border: 1px solid rgba(151, 166, 195, 0.28);
            border-radius: 10px;
            padding: 7px 9px;
            background: rgba(18, 25, 40, 0.72);
            min-height: 54px;
        }
        .identity-kv-value {
            font-size: 1rem;
            color: #f5f7fb;
            font-weight: 800;
            line-height: 1.15;
        }
        .hero-grevscore {
            border: 1px solid rgba(118, 168, 255, 0.32);
            border-radius: 14px;
            padding: 12px;
            background: linear-gradient(120deg, rgba(47, 77, 137, 0.34) 0%, rgba(25, 44, 82, 0.24) 100%);
            box-shadow: 0 0 10px rgba(54, 116, 255, 0.12);
            text-align: center;
        }
        .overview-side {
            border: 1px solid rgba(151, 166, 195, 0.2);
            border-radius: 12px;
            padding: 12px;
            background: rgba(12, 18, 29, 0.65);
        }
        .overview-side .section-label {
            margin-top: 0;
        }
        .achievement-tier {
            display: inline-block;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-size: 0.78rem;
        }
        .tier-s { color: #f5c451; }
        .tier-a { color: #9c6df6; }
        .tier-b { color: #5ea9ff; }
        .tier-c { color: #4ed083; }
        .tier-unknown { color: #9da7bd; }
        .hero-grevscore-label {
            color: #b8caf0;
            font-size: 0.82rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }
        .hero-grevscore-tier {
            font-size: 0.8rem;
            color: #d6e2ff;
            margin-top: 3px;
            letter-spacing: 0.04em;
        }
        .gauge-wrap {
            margin-top: 6px;
            position: relative;
            width: 100%;
            height: 148px;
        }
        .gauge-score {
            color: #f5f8ff;
            font-size: 2.05rem;
            font-weight: 900;
            line-height: 1.05;
            margin-bottom: 4px;
        }
        .gauge-arc {
            position: absolute;
            left: 50%;
            top: 62px;
            width: 176px;
            height: 90px;
            transform: translateX(-50%);
            border-radius: 176px 176px 0 0;
            background: linear-gradient(90deg, #ff6c7a 0%, #f0be4f 50%, #31d17b 100%);
            clip-path: polygon(0% 100%, 0% 60%, 50% 0%, 100% 60%, 100% 100%);
            opacity: 0.95;
        }
        .gauge-needle {
            position: absolute;
            left: 50%;
            top: 79px;
            width: 3px;
            height: 66px;
            background: #f5f8ff;
            transform-origin: bottom center;
            box-shadow: 0 0 10px rgba(245, 248, 255, 0.65);
            border-radius: 999px;
        }
        .gauge-hub {
            position: absolute;
            left: 50%;
            top: 144px;
            width: 14px;
            height: 14px;
            border-radius: 50%;
            background: #f5f8ff;
            transform: translate(-50%, -50%);
            box-shadow: 0 0 8px rgba(245, 248, 255, 0.75);
        }
        .grev-meter-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.68rem;
            color: #b8caf0;
            margin-top: 2px;
        }
        .section-label {
            font-size: 0.82rem;
            color: #9eb0d4;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 8px;
            margin-bottom: 4px;
        }
        .context-summary {
            margin-top: 10px;
            border: 1px solid rgba(151, 166, 195, 0.18);
            border-radius: 12px;
            background: rgba(11, 16, 26, 0.6);
            padding: 10px 12px;
        }
        .context-summary-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 7px 14px;
        }
        .context-row {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            border-bottom: 1px dashed rgba(151, 166, 195, 0.16);
            padding-bottom: 3px;
        }
        .context-row:last-child {
            border-bottom: none;
        }
        .context-key {
            font-size: 0.76rem;
            color: #9da7bd;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        .context-val {
            font-size: 0.83rem;
            color: #f5f7fb;
            font-weight: 700;
            text-align: right;
        }
        .form-mini {
            margin-top: 12px;
            border-top: 1px solid rgba(151, 166, 195, 0.18);
            padding-top: 10px;
        }
        .form-dot-row {
            display: grid;
            grid-template-columns: repeat(10, minmax(0, 1fr));
            gap: 6px;
            margin-top: 8px;
        }
        .form-dot {
            height: 10px;
            border-radius: 999px;
            background: rgba(151, 166, 195, 0.3);
        }
        .filter-shell {
            border: 1px solid rgba(151, 166, 195, 0.3);
            border-radius: 12px;
            padding: 8px 10px;
            background: rgba(8, 12, 21, 0.7);
        }
        .form-row {
            border-bottom: 1px solid rgba(151, 166, 195, 0.2);
            padding: 4px 0;
        }
        .compact-filter-header {
            color: #d3def6;
            margin: 0 0 2px 0;
            font-size: 0.95rem;
        }
        .stMultiSelect [data-baseweb="tag"] {
            padding: 0 4px;
            font-size: 0.74rem;
        }
        .hero-shell {
            position: relative;
            overflow: hidden;
            border-radius: 24px;
            border: 1px solid rgba(137, 160, 210, 0.38);
            padding: 30px 32px 26px;
            margin-bottom: 14px;
            background:
                radial-gradient(circle at 17% 22%, rgba(44, 201, 119, 0.18), transparent 46%),
                radial-gradient(circle at 84% 18%, rgba(255, 96, 72, 0.13), transparent 42%),
                linear-gradient(135deg, #101722 0%, #090d14 44%, #0b111c 100%);
            box-shadow: 0 22px 44px rgba(0, 0, 0, 0.4);
        }
        .hero-shell::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background-image: linear-gradient(rgba(136, 158, 197, 0.07) 1px, transparent 1px),
                              linear-gradient(90deg, rgba(136, 158, 197, 0.06) 1px, transparent 1px);
            background-size: 32px 32px;
            opacity: 0.18;
        }
        .hero-row {
            position: relative;
            z-index: 1;
            display: grid;
            grid-template-columns: minmax(130px, 170px) 1fr minmax(120px, 150px);
            gap: 20px;
            align-items: center;
        }
        .hero-logo-badge {
            border: 1px solid rgba(137, 160, 210, 0.4);
            border-radius: 14px;
            background: rgba(10, 16, 29, 0.74);
            min-height: 108px;
            display: grid;
            place-items: center;
            padding: 12px;
            backdrop-filter: blur(4px);
            position: relative;
        }
        .hero-logo-badge-left::after {
            content: "";
            position: absolute;
            inset: 20% 12%;
            border-radius: 14px;
            background: radial-gradient(circle, rgba(49, 209, 123, 0.26), transparent 70%);
            z-index: -1;
        }
        .hero-logo-badge-right::after {
            content: "";
            position: absolute;
            inset: 20% 12%;
            border-radius: 14px;
            background: radial-gradient(circle, rgba(255, 107, 79, 0.2), transparent 70%);
            z-index: -1;
        }
        .hero-logo-badge img {
            width: 100%;
            object-fit: contain;
        }
        .hero-title-block h1 {
            margin: 0;
            color: #f6f9ff;
            font-size: clamp(1.9rem, 2.8vw, 2.6rem);
            line-height: 1.05;
            letter-spacing: 0.01em;
        }
        .hero-subtitle {
            color: #c7d5f1;
            margin-top: 9px;
            font-size: 1.02rem;
        }
        .hero-pill-row {
            margin-top: 14px;
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }
        .hero-pill {
            border-radius: 999px;
            border: 1px solid rgba(146, 170, 220, 0.45);
            background: rgba(19, 28, 44, 0.82);
            color: #e5edff;
            font-weight: 700;
            font-size: 0.74rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            padding: 6px 10px;
        }
        .hero-shell-divider {
            position: relative;
            z-index: 1;
            margin-top: 19px;
            height: 1px;
            background: linear-gradient(90deg, rgba(41, 211, 130, 0.18), rgba(161, 183, 232, 0.52), rgba(255, 117, 79, 0.18));
        }
        .home-tab-row {
            margin-top: 8px;
        }
        .home-tab-row [data-testid="stHorizontalBlock"] {
            gap: 12px;
        }
        .home-tab-row .stButton > button {
            border-radius: 999px;
            border: 1px solid rgba(137, 160, 210, 0.48);
            background: linear-gradient(180deg, rgba(22, 32, 52, 0.92), rgba(10, 16, 29, 0.92));
            color: #e6eeff;
            min-height: 42px;
            font-size: 0.88rem;
            font-weight: 700;
            box-shadow: 0 8px 18px rgba(0, 0, 0, 0.3);
            transition: all 0.2s ease;
        }
        .home-tab-row .stButton > button:hover {
            border-color: rgba(95, 243, 165, 0.72);
            box-shadow: 0 10px 24px rgba(49, 209, 123, 0.22);
            transform: translateY(-1px);
        }
        .home-tab-row .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, rgba(34, 82, 62, 0.95), rgba(15, 39, 30, 0.95));
            border-color: rgba(95, 243, 165, 0.74);
            box-shadow: 0 12px 24px rgba(49, 209, 123, 0.26);
        }
        [data-testid="stDateInput"] input,
        [data-testid="stMultiSelect"] input {
            font-size: 0.8rem;
        }
        .vs-role-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .vs-role-chip {
            border: 1px solid rgba(151, 166, 195, 0.28);
            border-radius: 12px;
            padding: 8px 10px;
            background: rgba(11, 17, 27, 0.75);
        }
        .vs-role-label {
            color: #9da7bd;
            font-size: 0.69rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .vs-role-value {
            color: #eef4ff;
            font-size: 0.82rem;
            font-weight: 800;
            margin-top: 4px;
            line-height: 1.25;
        }
        .ranked-list {
            display: grid;
            gap: 10px;
        }
        .ranked-row {
            border: 1px solid rgba(151, 166, 195, 0.24);
            border-radius: 12px;
            background: rgba(10, 16, 26, 0.7);
            padding: 10px 12px;
            display: grid;
            grid-template-columns: auto minmax(0, 1.6fr) repeat(6, minmax(0, 1fr));
            gap: 8px;
            align-items: center;
        }
        .rank-cell-main {
            display: flex;
            align-items: center;
            gap: 8px;
            min-width: 0;
        }
        .rank-logo {
            width: 28px;
            height: 28px;
            border-radius: 7px;
            border: 1px solid rgba(151, 166, 195, 0.32);
            background: rgba(14, 22, 34, 0.9);
            object-fit: contain;
            padding: 2px;
        }
        .rank-name {
            color: #edf3ff;
            font-size: 0.84rem;
            font-weight: 800;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
        }
        .vs-pill {
            border-radius: 999px;
            border: 1px solid rgba(151, 166, 195, 0.35);
            padding: 2px 8px;
            font-size: 0.7rem;
            display: inline-block;
            font-weight: 700;
            letter-spacing: 0.02em;
            color: #eaf1ff;
            background: rgba(20, 30, 46, 0.85);
        }
        .vs-pill-good { border-color: rgba(49, 209, 123, 0.52); color: #8cf0bb; }
        .vs-pill-mid { border-color: rgba(240, 190, 79, 0.48); color: #ffd27a; }
        .vs-pill-bad { border-color: rgba(255, 108, 122, 0.54); color: #ff9daa; }
        .tier-strip-grid {
            display: grid;
            gap: 10px;
        }
        .tier-strip {
            border: 1px solid rgba(151, 166, 195, 0.23);
            border-radius: 12px;
            padding: 10px 12px;
            background: rgba(12, 18, 29, 0.7);
        }
        .tier-strip-top {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 6px;
        }
        .tier-strip-metrics {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
            font-size: 0.76rem;
            color: #d4e1fb;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


def _image_to_data_uri(image_path: Path) -> str:
    return f"data:image/{image_path.suffix.lstrip('.').lower()};base64,{base64.b64encode(image_path.read_bytes()).decode('utf-8')}"


def _render_top_hero(active_page: str, subtitle: str) -> None:
    medicart_logo_html = (
        f'<img src="{_image_to_data_uri(MEDISPORTS_LOGO)}" alt="Medicart logo" style="max-width:144px;">'
        if MEDISPORTS_LOGO.exists()
        else '<span style="color:#c7d5f1;font-size:0.8rem;">Medicart logo missing</span>'
    )
    cpl_logo_html = (
        f'<img src="{_image_to_data_uri(CPL_LOGO)}" alt="CPL logo" style="max-width:108px;">'
        if CPL_LOGO.exists()
        else '<span style="color:#c7d5f1;font-size:0.8rem;">CPL logo missing</span>'
    )
    st.markdown(
        f"""
        <section class="hero-shell">
            <div class="hero-row">
                <div class="hero-logo-badge hero-logo-badge-left">{medicart_logo_html}</div>
                <div class="hero-title-block">
                    <h1>Grev's CPL Dashboard</h1>
                    <div class="hero-subtitle">{subtitle}</div>
                    <div class="hero-pill-row">
                        <span class="hero-pill">S10 Active</span>
                    </div>
                </div>
                <div class="hero-logo-badge hero-logo-badge-right">{cpl_logo_html}</div>
            </div>
            <div class="hero-shell-divider"></div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="home-tab-row">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button(
            "👤 HLTV CPL Profile Viewer",
            use_container_width=True,
            type="primary" if active_page == "profiles" else "secondary",
            key=f"hero_nav_profiles_{active_page}",
        ):
            st.session_state["page"] = "profiles"
            st.rerun()
    with col2:
        if st.button(
            "📊 Teams Tactical Breakdown",
            use_container_width=True,
            type="primary" if active_page == "tactics" else "secondary",
            key=f"hero_nav_tactics_{active_page}",
        ):
            st.session_state["page"] = "tactics"
            st.rerun()
    with col3:
        if st.button(
            "⚔️ Medisports Vs Breakdown",
            use_container_width=True,
            type="primary" if active_page == "medisports_vs" else "secondary",
            key=f"hero_nav_medisports_{active_page}",
        ):
            st.session_state["page"] = "medisports_vs"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


@st.cache_data(show_spinner=False)
def _build_image_index() -> dict[str, dict[str, Path]]:
    image_index: dict[str, dict[str, Path]] = {}
    for image_type, folder_name in IMAGE_FOLDERS.items():
        folder = APP_ROOT / folder_name
        entries: dict[str, Path] = {}
        if folder.exists():
            for path in folder.iterdir():
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS:
                    entries[_normalize_key(path.stem)] = path
        image_index[image_type] = entries
    return image_index


def _find_image(image_index: dict[str, dict[str, Path]], image_type: str, value: str | None) -> Path | None:
    if not value:
        return None
    if image_type == "competition":
        ascii_value = (
            str(value)
            .lower()
            .translate(str.maketrans({"ᴍ": "m", "ᴀ": "a", "ᴅ": "d", "ᴇ": "e", "ɴ": "n"}))
        )
        if "madmen" in ascii_value:
            madmen_logo = APP_ROOT / IMAGE_FOLDERS["competition"] / "madmen.png"
            if madmen_logo.exists():
                return madmen_logo
    normalized = _normalize_key(value)
    entries = image_index.get(image_type, {})
    return entries.get(normalized)


def _competition_logo_uri(image_index: dict[str, dict[str, Path]], competition: str | None) -> str:
    competition_logo = _find_image(image_index, "competition", competition)
    fallback_logo = CPL_LOGO if CPL_LOGO.exists() else None
    chosen_logo = competition_logo or fallback_logo
    if chosen_logo is None:
        return ""
    return _image_to_data_uri(chosen_logo)


def _find_achievement_image(
    image_index: dict[str, dict[str, Path]],
    achievement_link: str | None,
    achievement_name: str | None,
) -> Path | None:
    if achievement_link:
        link_path = Path(str(achievement_link))
        if link_path.suffix.lower() in IMAGE_EXTENSIONS:
            by_name = _find_image(image_index, "achievement", link_path.stem)
            if by_name:
                return by_name
    return _find_image(image_index, "achievement", achievement_name)


def _normalize_match_id_column(df: pd.DataFrame) -> pd.DataFrame:
    if "match_id" in df.columns:
        df["match_id"] = df["match_id"].astype(str).str.strip()
    return df


def normalize_competition_name(competition: str | None) -> str | None:
    if competition is None or (isinstance(competition, float) and pd.isna(competition)):
        return competition
    return re.sub(r"\b(S\d+)\.\d+\b", r"\1", str(competition))


def add_grouped_competition_column(df: pd.DataFrame, source_col: str = "competition") -> pd.DataFrame:
    grouped_df = df.copy()
    if source_col not in grouped_df.columns:
        grouped_df["grouped_competition"] = pd.NA
        return grouped_df
    grouped_df["grouped_competition"] = grouped_df[source_col].apply(normalize_competition_name)
    return grouped_df


@st.cache_data(show_spinner=False)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    players = pd.read_csv(PLAYER_CSV)
    tactics = pd.read_csv(TACTICS_CSV)
    players = _normalize_match_id_column(players)
    tactics = _normalize_match_id_column(tactics)
    if "tactic_name" in tactics.columns:
        tactics["tactic_name"] = tactics["tactic_name"].apply(_normalize_tactic_name)

    # Drop accidental empty trailing columns from CSV export.
    tactics = tactics.loc[:, ~tactics.columns.str.contains(r"^Unnamed")]
    tactics = tactics.loc[:, tactics.columns.astype(str).str.strip() != ""]

    achievements = pd.read_csv(
        ACHIEVEMENTS_CSV,
        sep="|",
        quotechar='"',
        engine="python",
    )
    achievements.columns = achievements.columns.astype(str).str.strip()
    achievements = achievements.apply(lambda s: s.str.strip() if s.dtype == object else s)

    players["date"] = pd.to_datetime(players["date"], errors="coerce")
    tactics["date"] = pd.to_datetime(tactics["date"], errors="coerce")
    match_dates = players.groupby("match_id", as_index=False)["date"].max().rename(columns={"date": "match_date"})
    tactics = tactics.merge(match_dates, on="match_id", how="left")
    tactics["date"] = tactics["date"].fillna(tactics["match_date"])
    tactics.drop(columns=["match_date"], inplace=True)

    players = _coerce_numeric(
        players,
        ["kills", "deaths", "mvps", "kpd", "accuracy_pct", "hs_pct", "damage", "rounds_played"],
    )
    tactics = _coerce_numeric(tactics, ["wins", "losses", "total_rounds", "win_rate_pct"])
    players = add_grouped_competition_column(players, source_col="competition")
    tactics = add_grouped_competition_column(tactics, source_col="competition")

    return players, tactics, achievements


@st.cache_data(show_spinner=False)
def _load_player_metadata() -> pd.DataFrame:
    metadata_path = next((path for path in PLAYER_META_CSV_CANDIDATES if path.exists()), None)
    if metadata_path is None:
        return pd.DataFrame()

    try:
        metadata = pd.read_csv(metadata_path, sep=None, engine="python", on_bad_lines="skip")
    except pd.errors.ParserError:
        # Some exports are malformed enough that separator inference fails.
        # Fallback through common delimiters and keep whichever parse yields
        # usable columns.
        metadata = pd.DataFrame()
        for sep in (",", "|", ";", "\t"):
            try:
                candidate = pd.read_csv(metadata_path, sep=sep, engine="python", on_bad_lines="skip")
            except pd.errors.ParserError:
                continue
            if not candidate.empty and len(candidate.columns) > 1:
                metadata = candidate
                break
        if metadata.empty:
            return pd.DataFrame()

    metadata.columns = metadata.columns.astype(str).str.strip()
    metadata = metadata.apply(lambda col: col.str.strip() if col.dtype == object else col)
    if metadata.empty:
        return metadata

    alias_map = {
        "name": "player",
        "country": "nation",
        "nationality": "nation",
    }
    renamed_cols = {}
    for col in metadata.columns:
        normalized = col.strip().casefold()
        if normalized in alias_map:
            renamed_cols[col] = alias_map[normalized]
    if renamed_cols:
        metadata = metadata.rename(columns=renamed_cols)

    player_col = next((col for col in metadata.columns if col.casefold() == "player"), None)
    if player_col is None:
        return pd.DataFrame()

    metadata = metadata.rename(columns={player_col: "player"})
    metadata["player_lookup"] = metadata["player"].astype(str).str.strip().str.casefold()
    metadata = metadata.drop_duplicates(subset=["player_lookup"], keep="last")
    return metadata


def _nation_flag_emoji(value: str | None) -> str:
    nation = str(value or "").strip()
    if not nation:
        return ""
    normalized = nation.casefold()
    alpha2 = nation.upper() if len(nation) == 2 and nation.isalpha() else COUNTRY_TO_ALPHA2.get(normalized, "")
    if len(alpha2) != 2 or not alpha2.isalpha():
        return ""
    return "".join(chr(127397 + ord(ch)) for ch in alpha2.upper())


def _safe_mean(df: pd.DataFrame, column: str, default: float = 0.0) -> float:
    if column not in df.columns or df.empty:
        return default
    value = pd.to_numeric(df[column], errors="coerce").mean()
    return float(value) if pd.notna(value) else default


def _player_meta_value(player_meta: pd.Series | None, key: str, default: str = "-") -> str:
    if player_meta is None:
        return default
    key_aliases = {
        "nation": ("nation", "country", "nationality"),
        "role": ("role",),
        "handedness": ("handedness", "hand"),
    }
    candidates = key_aliases.get(key, (key,))
    for candidate in candidates:
        value = str(player_meta.get(candidate, "")).strip()
        if value:
            return value
    return default


def _multiselect_filter(label: str, options: list[str], key: str) -> list[str]:
    if not options:
        st.caption(f"{label}: no options")
        return []
    selected = st.multiselect(
        label,
        options,
        default=[],
        key=key,
        placeholder="All (no filter)",
    )
    active = selected if selected else options
    summary = "All" if not selected else f"{len(selected)} selected"
    st.markdown(f'<div class="panel-muted">{label}: {summary}</div>', unsafe_allow_html=True)
    return active


def _normalize_tactic_name(value: str) -> str:
    raw = str(value or "")
    match = re.match(r"^\s*((?:[\(\[\{<][^)\]}>]+[\)\]}>]\s*)+)(.*)$", raw)
    if not match:
        return re.sub(r"\s+", " ", raw).strip()

    tags = re.findall(r"[\(\[\{<][^)\]}>]+[\)\]}>]", match.group(1))
    remainder = re.sub(r"\s+", " ", match.group(2)).strip()
    normalized_prefix = "".join(tags)
    return f"{normalized_prefix} {remainder}".strip()


def _expand_tactics_by_round_type(df: pd.DataFrame) -> pd.DataFrame:
    if "tactic_name" not in df.columns:
        return df.copy()

    if df.empty:
        expanded = df.copy()
        expanded["round_type"] = pd.Series(dtype="object")
        return expanded

    expanded = df.copy()
    tactic_names = expanded["tactic_name"].fillna("").astype(str)
    round_types: list[list[str]] = []

    bracket_pattern = re.compile(r"[\(\[\{<]([^)\]}>]+)[\)\]\}>]")
    leading_tag_pattern = re.compile(r"^\s*[\(\[\{<][^)\]}>]+[\)\]\}>]\s*")

    def _strip_leading_tags(value: str) -> str:
        stripped = value.lstrip()
        while True:
            updated = leading_tag_pattern.sub("", stripped, count=1)
            if updated == stripped:
                return stripped
            stripped = updated

    for tactic_name in tactic_names:
        tags: list[str] = []
        upper_name = tactic_name.upper()

        bracket_matches = bracket_pattern.findall(upper_name)
        bracket_tokens = "".join(bracket_matches)
        prefix_name = _strip_leading_tags(upper_name)

        if "P" in bracket_tokens:
            # Pistol tactics are also available as eco + standard callups.
            tags.extend(["Pistol", "Eco", "Standard"])
        elif "E" in bracket_tokens:
            tags.append("Eco")
        elif "S" in bracket_tokens:
            tags.append("Standard")
        else:
            if prefix_name.startswith("P"):
                tags.extend(["Pistol", "Eco", "Standard"])
            elif prefix_name.startswith("E"):
                tags.append("Eco")
            elif prefix_name.startswith("S"):
                tags.append("Standard")
            else:
                tags.append("Unspecified")
        round_types.append(tags)

    expanded["round_type"] = round_types
    expanded = expanded.explode("round_type").reset_index(drop=True)
    return expanded


def _calc_player_card_metrics(filtered_players: pd.DataFrame, filtered_tactics: pd.DataFrame) -> dict[str, float]:
    matches = max(int(filtered_players["match_id"].nunique()), 1)
    kills = float(filtered_players["kills"].sum())
    deaths = float(filtered_players["deaths"].sum())
    assists = float(filtered_players["mvps"].sum())
    damage = float(filtered_players["damage"].sum())
    acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0

    kda = (kills + assists) / deaths if deaths else kills + assists
    kd = kills / deaths if deaths else kills
    dpm = damage / matches
    kpm = kills / matches

    win_rate = 0.0
    if not filtered_tactics.empty and {"wins", "losses"}.issubset(filtered_tactics.columns):
        wins = float(filtered_tactics["wins"].sum())
        losses = float(filtered_tactics["losses"].sum())
        total = wins + losses
        win_rate = (wins / total * 100) if total else 0.0

    hs = float(filtered_players["hs_pct"].mean()) if "hs_pct" in filtered_players.columns else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if "kpd" in filtered_players.columns else 0.0
    kpd_consistency = 1.0
    if "kpd" in filtered_players.columns and len(filtered_players) > 1:
        kpd_std = float(filtered_players["kpd"].std(ddof=0))
        kpd_consistency = max(0.0, min(1.0, 1.0 - (kpd_std / 1.25)))

    impact = (kd * 28.0) + (kda * 14.0) + (kpm * 22.0) + (acc * 0.14) + (win_rate * 0.22)

    score_components = {
        "kd": min(max((kd / 1.25) * 100.0, 0.0), 100.0),
        "kda": min(max((kda / 2.0) * 100.0, 0.0), 100.0),
        "kpm": min(max((kpm / 1.0) * 100.0, 0.0), 100.0),
        "dpm": min(max((dpm / 3600.0) * 100.0, 0.0), 100.0),
        "acc": min(max(acc, 0.0), 100.0),
        "hs": min(max((hs / 55.0) * 100.0, 0.0), 100.0),
        "win_rate": min(max(win_rate, 0.0), 100.0),
        "impact": min(max((impact / 100.0) * 100.0, 0.0), 100.0),
        "consistency": min(max(kpd_consistency * 100.0, 0.0), 100.0),
        "avg_kpd": min(max((avg_kpd / 1.5) * 100.0, 0.0), 100.0),
    }
    grevscore = (
        (score_components["kd"] * 0.14)
        + (score_components["kda"] * 0.11)
        + (score_components["kpm"] * 0.11)
        + (score_components["dpm"] * 0.1)
        + (score_components["acc"] * 0.08)
        + (score_components["hs"] * 0.06)
        + (score_components["win_rate"] * 0.15)
        + (score_components["impact"] * 0.14)
        + (score_components["consistency"] * 0.06)
        + (score_components["avg_kpd"] * 0.05)
    )
    grevscore_raw = min(max(grevscore, 0.0), 100.0)
    return {
        "matches": float(matches),
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "kda": kda,
        "kd": kd,
        "dpm": dpm,
        "acc": acc,
        "kpm": kpm,
        "impact": impact,
        "grevscore_raw": grevscore_raw,
        "grevscore": grevscore_raw / 100.0,
    }


def _score_tier_label(score: float) -> str:
    if score >= 1.5:
        return "Amazing"
    if score >= 1.2:
        return "Good"
    if score >= 1.0:
        return "Okay"
    if score >= 0.9:
        return "Average"
    if score >= 0.75:
        return "Poor"
    return "Very Poor"


def _stat_visual(value: float, low: float, high: float, invert: bool = False) -> tuple[str, float]:
    if high <= low:
        return "trend-mid", 50.0
    pct = ((value - low) / (high - low)) * 100.0
    pct = min(max(pct, 0.0), 100.0)
    if invert:
        pct = 100.0 - pct
    if pct >= 70:
        return "trend-good", pct
    if pct <= 35:
        return "trend-bad", pct
    return "trend-mid", pct


def _build_stat_chip(label: str, display: str, value: float, low: float, high: float, invert: bool = False) -> str:
    tier_class, meter = _stat_visual(value, low, high, invert=invert)
    arrow = "▲" if tier_class == "trend-good" else ("▼" if tier_class == "trend-bad" else "■")
    chip_class = "chip-good" if tier_class == "trend-good" else ("chip-bad" if tier_class == "trend-bad" else "chip-mid")
    return (
        f'<div class="stat-chip {chip_class}"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{display}</div>'
        f'<div class="stat-trend {tier_class}">{arrow} {meter:.0f}/100</div>'
        f'<div class="stat-meter"><div class="stat-meter-fill" style="width:{meter:.0f}%"></div></div></div>'
    )


def _achievement_tier_class(tier: str | None) -> str:
    tier_clean = str(tier or "").strip().upper()
    if tier_clean in {"S", "A", "B", "C"}:
        return f"tier-{tier_clean.lower()}"
    return "tier-unknown"


def _achievement_card_html(ach_row: pd.Series) -> str:
    ach_tier = str(ach_row.get("achievement_tier", "")).strip().upper() or "?"
    ach_tier_class = _achievement_tier_class(ach_tier)
    ach_image = ach_row.get("achievement_image")
    season = html.escape(str(ach_row.get("season_name", "-")))
    name = html.escape(str(ach_row.get("achievement_name", "-")))
    image_html = "<div class='panel-muted' style='font-size:0.68rem;text-transform:uppercase;letter-spacing:0.05em;'>No image</div>"
    if ach_image:
        image_html = f"<img src='data:image/png;base64,{base64.b64encode(ach_image.read_bytes()).decode('utf-8')}'>"
    return (
        "<div class='achievement-inline-item'>"
        "<div class='achievement-image-wrap'>"
        f"<div class='achievement-season'>{season}</div>"
        f"{image_html}"
        f"<span class='achievement-tier achievement-tier-icon {ach_tier_class}'>{html.escape(ach_tier[:1])}</span>"
        f"<span class='achievement-inline-name'>{name}</span>"
        "</div>"
        "</div>"
    )


def _calculate_form_section(player_rows: pd.DataFrame, tactics_df: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    if player_rows.empty:
        return 0.0, pd.DataFrame()

    recent = player_rows.sort_values("date", ascending=False).head(10).copy()
    match_ids = recent["match_id"].dropna().unique().tolist()
    tactics_matches = tactics_df[tactics_df["match_id"].isin(match_ids)].copy()
    tactics_summary = (
        tactics_matches.groupby("match_id", as_index=False)[["wins", "losses"]].sum()
        if not tactics_matches.empty
        else pd.DataFrame(columns=["match_id", "wins", "losses"])
    )
    recent = recent.merge(tactics_summary, on="match_id", how="left")
    recent[["wins", "losses"]] = recent[["wins", "losses"]].fillna(0)
    recent["kda"] = (recent["kills"] + recent["mvps"]) / recent["deaths"].replace(0, 1)
    recent["round_diff"] = recent["wins"] - recent["losses"]
    recent["close_game_bonus"] = (1.0 - (recent["round_diff"].abs() / 16.0)).clip(lower=0.0, upper=1.0)
    recent["dominance_bonus"] = (recent["round_diff"].abs() / 16.0).clip(lower=0.0, upper=1.0)
    recent["result_points"] = (recent["wins"] > recent["losses"]).astype(float) * 1.0

    teammate_scope = player_rows[player_rows["match_id"].isin(match_ids)].copy()
    teammate_top = (
        teammate_scope.groupby("match_id")
        .apply(
            lambda g: (
                (g["kills"] * 0.25)
                + (g["kpd"] * 0.25)
                + (((g["kills"] + g["mvps"]) / g["deaths"].replace(0, 1)) * 0.2)
                + ((g["damage"] / g["rounds_played"].replace(0, 1)) * 0.2)
                + (g["mvps"] * 0.1)
            )
            .idxmax()
        )
        .to_dict()
    )
    recent["carried"] = recent.index.map(lambda idx: 1.0 if idx == teammate_top.get(recent.loc[idx, "match_id"]) else 0.0)

    recent["match_form_score"] = (
        (recent["kpd"] / 1.5).clip(0, 1.2) * 30
        + (recent["kda"] / 2.2).clip(0, 1.2) * 20
        + (recent["accuracy_pct"] / 100).clip(0, 1.0) * 10
        + (recent["hs_pct"] / 60).clip(0, 1.0) * 6
        + recent["result_points"] * 14
        + recent["close_game_bonus"] * 6
        + recent["dominance_bonus"] * 4
        + recent["carried"] * 10
    ).clip(lower=0, upper=100)
    form_score = float(recent["match_form_score"].mean()) if not recent.empty else 0.0
    return form_score, recent


def _home() -> None:
    _inject_styles()
    _render_top_hero(
        active_page="home",
        subtitle="Player analytics, tactical breakdowns, match insights.",
    )


def _build_match_level_results(tactics_df: pd.DataFrame, competition_source_col: str) -> pd.DataFrame:
    if tactics_df.empty:
        return pd.DataFrame()
    match_cols = ["match_id", "date", "map", competition_source_col, "tier", "my_team", "opponent_team"]
    meta_cols = [col for col in match_cols if col in tactics_df.columns]
    match_meta = tactics_df.groupby("match_id", as_index=False)[meta_cols].first()
    results = (
        tactics_df.groupby("match_id", as_index=False)[["wins", "losses"]]
        .sum()
        .rename(columns={"wins": "round_wins", "losses": "round_losses"})
    )
    results["round_diff"] = results["round_wins"] - results["round_losses"]
    results["match_result"] = results["round_diff"].apply(lambda x: "Win" if x > 0 else ("Loss" if x < 0 else "Draw"))
    merged = match_meta.merge(results, on="match_id", how="inner")
    for col in match_cols:
        if col not in merged.columns:
            merged[col] = pd.NA
    merged = merged.rename(columns={competition_source_col: "competition"})
    return merged


def _apply_shared_filters(
    player_df: pd.DataFrame,
    tactics_df: pd.DataFrame,
    selected_player: str,
    competition_source_col: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered_players = player_df[player_df["player"] == selected_player].copy()

    min_date = filtered_players["date"].min().date()
    max_date = filtered_players["date"].max().date()

    st.markdown('<p class="compact-filter-header">Player Filters</p>', unsafe_allow_html=True)
    filter_cols = st.columns(5)
    tier_options = sorted(filtered_players["tier"].dropna().unique().tolist())
    with filter_cols[0]:
        selected_tiers = _multiselect_filter("Tier of Team", tier_options, key="profile_tier")

    event_options = sorted(filtered_players[competition_source_col].dropna().unique().tolist())
    with filter_cols[1]:
        selected_events = _multiselect_filter("Event", event_options, key="profile_event")

    opp_options = sorted(filtered_players["opponent_team"].dropna().unique().tolist())
    with filter_cols[2]:
        selected_opp = _multiselect_filter("Opponent", opp_options, key="profile_opp")

    side_options = sorted(tactics_df["side"].dropna().unique().tolist()) if "side" in tactics_df else []
    with filter_cols[3]:
        selected_sides = _multiselect_filter("Side (Red/Blue)", side_options, key="profile_side")

    date_range = filter_cols[4].date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    else:
        start_date = end_date = pd.to_datetime(date_range[0])

    if selected_tiers:
        filtered_players = filtered_players[filtered_players["tier"].isin(selected_tiers)]
    if selected_events:
        filtered_players = filtered_players[filtered_players[competition_source_col].isin(selected_events)]
    if selected_opp:
        filtered_players = filtered_players[filtered_players["opponent_team"].isin(selected_opp)]

    filtered_players = filtered_players[
        filtered_players["date"].between(start_date, end_date, inclusive="both")
    ]

    filtered_tactics = tactics_df[tactics_df["match_id"].isin(filtered_players["match_id"].unique())].copy()

    if selected_sides and "side" in filtered_tactics:
        filtered_tactics = filtered_tactics[filtered_tactics["side"].isin(selected_sides)]
        filtered_players = filtered_players[
            filtered_players["match_id"].isin(filtered_tactics["match_id"].unique())
        ]

    return filtered_players, filtered_tactics


def _hltv_profile_view(
    player_df: pd.DataFrame,
    tactics_df: pd.DataFrame,
    achievements_df: pd.DataFrame,
    competition_source_col: str,
) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="profiles",
        subtitle="Medicart analytics, player profiles, tactics, and event breakdowns.",
    )

    players = sorted(
        player_df[
            player_df["player"].astype(str).str.contains("ⓜ", regex=False, na=False)
        ]["player"]
        .dropna()
        .unique()
        .tolist()
    )
    if not players:
        st.warning('No players with "ⓜ" in their name were found.')
        return

    selected_player = st.selectbox('Pick a player (names containing "ⓜ")', players)

    with st.expander("Profile Filters", expanded=False):
        filtered_players, filtered_tactics = _apply_shared_filters(
            player_df,
            tactics_df,
            selected_player,
            competition_source_col,
        )
    image_index = _build_image_index()
    player_metadata = _load_player_metadata()

    if filtered_players.empty:
        st.warning("No player rows match the current filters.")
        return

    first_row = filtered_players.sort_values("date", ascending=False).iloc[0]

    player_meta_row = None
    if not player_metadata.empty and "player_lookup" in player_metadata.columns:
        selected_lookup = str(selected_player).strip().casefold()
        meta_rows = player_metadata[player_metadata["player_lookup"] == selected_lookup]
        if not meta_rows.empty:
            player_meta_row = meta_rows.iloc[0]

    player_image = _find_image(image_index, "player", selected_player)
    team_logo = _find_image(image_index, "team", first_row.get("my_team"))

    metrics = _calc_player_card_metrics(filtered_players, filtered_tactics)
    rank_scope = []
    team_scope = player_df[
        player_df["player"].astype(str).str.contains("ⓜ", regex=False, na=False)
    ]
    for player_name, rows in team_scope.groupby("player"):
        p_metrics = _calc_player_card_metrics(rows, tactics_df[tactics_df["match_id"].isin(rows["match_id"].unique())])
        rank_scope.append({"player": player_name, "score": p_metrics["grevscore"]})
    rank_df = pd.DataFrame(rank_scope).sort_values("score", ascending=False).reset_index(drop=True)
    team_rank = int(rank_df.index[rank_df["player"] == selected_player][0] + 1) if not rank_df.empty else 1
    rank_total = max(int(len(rank_df)), 1)
    percentile = ((rank_total - team_rank) / rank_total) * 100.0
    score_tier = _score_tier_label(metrics["grevscore"])
    gauge_pct = min(max(((metrics["grevscore"] - 0.75) / (1.5 - 0.75)) * 100.0, 0.0), 100.0)
    gauge_angle = -90 + (gauge_pct * 1.8)
    kills = int(metrics["kills"])
    damage = int(filtered_players["damage"].sum())
    rounds = int(filtered_players["rounds_played"].sum())
    avg_acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0
    avg_hs = float(filtered_players["hs_pct"].mean()) if not filtered_players.empty else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if not filtered_players.empty else 0.0

    stat_chips_overview = [
        _build_stat_chip("🎯 Rating", f'{metrics["grevscore"]:.2f}', metrics["grevscore"], 0.65, 1.35),
        _build_stat_chip("🏆 Matches", f'{int(metrics["matches"])}', metrics["matches"], 3, 16),
        _build_stat_chip("🗡️ K/D", f'{metrics["kd"]:.2f}', metrics["kd"], 0.7, 1.3),
        _build_stat_chip("🛡️ Impact", f'{metrics["impact"]:.1f}', metrics["impact"], 45, 95),
    ]
    stat_chips_core = [
        _build_stat_chip("DPM", f'{metrics["dpm"]:.1f}', metrics["dpm"], 1800, 3600),
        _build_stat_chip("KPM", f'{metrics["kpm"]:.2f}', metrics["kpm"], 0.45, 1.0),
        _build_stat_chip("Impact", f'{metrics["impact"]:.1f}', metrics["impact"], 45, 95),
        _build_stat_chip("Acc%", f'{metrics["acc"]:.1f}%', metrics["acc"], 45, 80),
        _build_stat_chip("Avg KPD", f"{avg_kpd:.2f}", avg_kpd, 0.8, 1.5),
        _build_stat_chip("KDA", f'{metrics["kda"]:.2f}', metrics["kda"], 1.0, 2.2),
        _build_stat_chip("HS%", f"{avg_hs:.1f}%", avg_hs, 24, 55),
        _build_stat_chip("Kills", f"{kills}", float(kills), 80, 260),
    ]
    side_split = "-"
    side_chart_data = pd.DataFrame(columns=["side", "rating"])
    if not filtered_tactics.empty and "side" in filtered_tactics.columns:
        side_summary = (
            filtered_tactics.groupby("side", as_index=False)[["wins", "losses"]].sum().sort_values("wins", ascending=False)
        )
        if not side_summary.empty:
            s = side_summary.iloc[0]
            side_split = f'{s["side"]}: {int(s["wins"])}W-{int(s["losses"])}L'
    if "side" in filtered_players.columns:
        side_chart_data = (
            filtered_players.dropna(subset=["side"])
            .groupby("side", as_index=False)["kpd"]
            .mean()
            .rename(columns={"kpd": "rating"})
            .sort_values("rating", ascending=False)
        )
    best_map = (
        filtered_players.groupby("map")["kills"].sum().sort_values(ascending=False).index[0]
        if "map" in filtered_players.columns and not filtered_players.empty
        else "-"
    )
    record_text = f"{int(filtered_tactics['wins'].sum())}W-{int(filtered_tactics['losses'].sum())}L" if not filtered_tactics.empty else "-"

    player_ach = achievements_df[
        achievements_df["player"].astype(str).str.strip().str.casefold() == str(selected_player).strip().casefold()
    ].copy()
    if not player_ach.empty:
        player_ach = player_ach.sort_values(["season_name", "position"], ascending=[False, True])
    if not player_ach.empty:
        player_ach["achievement_image"] = player_ach.apply(
            lambda row: _find_achievement_image(
                image_index,
                row.get("achievement_link"),
                row.get("achievement_name"),
            ),
            axis=1,
        )
    team_logo_html = ""
    if team_logo:
        team_logo_html = (
            f'<img style="width:42px;border-radius:8px;vertical-align:middle;margin-right:8px;" src="data:image/png;base64,{base64.b64encode(team_logo.read_bytes()).decode("utf-8")}">'
        )
    achievement_inline_html = "<div class='panel-muted'>No achievements found.</div>"
    if not player_ach.empty:
        achievement_rows = [_achievement_card_html(ach_row) for _, ach_row in player_ach.iterrows()]
        achievement_list_class = "achievement-inline-list achievement-inline-list-single" if len(achievement_rows) == 1 else "achievement-inline-list"
        achievement_inline_html = f"<div class='{achievement_list_class}'>{''.join(achievement_rows)}</div>"
    form_score, recent_form = _calculate_form_section(filtered_players, tactics_df)
    form_blocks = []
    if not recent_form.empty:
        for score in recent_form.sort_values("date")["match_form_score"].tail(10).tolist():
            color = "#31d17b" if score >= 70 else ("#f0be4f" if score >= 45 else "#ff6c7a")
            form_blocks.append(f"<div class='form-dot' style='background:{color};'></div>")
    form_block_html = "".join(form_blocks) if form_blocks else "<div class='panel-muted'>No recent form data.</div>"
    player_role = _player_meta_value(player_meta_row, "role", "Fragger")
    player_nation = _player_meta_value(player_meta_row, "nation")
    nation_flag = _nation_flag_emoji(player_nation)
    nation_with_flag = f"{nation_flag} {player_nation}".strip() if player_nation != "-" else player_nation
    handedness = _player_meta_value(player_meta_row, "handedness")

    st.markdown(
        f"""
        <div class="panel-card">
            <div class="top-identity-grid">
                <div class="identity-strip">
                    <div class="identity-strip-main">
                        <div class="portrait-frame">
                            {"<img class='player-headshot' src='data:image/png;base64," + base64.b64encode(player_image.read_bytes()).decode("utf-8") + "'>" if player_image else "<div class='panel-muted'>No portrait found.</div>"}
                        </div>
                        <div>
                            <div class="profile-label">Player Identity</div>
                            <div class="profile-name">{selected_player}</div>
                            <div class="identity-meta-line">{team_logo_html}<span>{first_row.get("my_team", "-")} · {player_role} · {nation_with_flag} · {handedness}</span></div>
                        </div>
                    </div>
                    <div class="section-label">Achievements</div>
                    {achievement_inline_html}
                </div>
                <div class="hero-grevscore">
                    <div class="hero-grevscore-label">GrevScore</div>
                    <div class="hero-grevscore-tier">{percentile:.0f}th percentile · {score_tier}</div>
                    <div class="gauge-wrap">
                        <div class="gauge-score">{metrics["grevscore"]:.2f}</div>
                        <div class="gauge-arc"></div>
                        <div class="gauge-needle" style="transform: translateX(-50%) rotate({gauge_angle:.1f}deg);"></div>
                        <div class="gauge-hub"></div>
                    </div>
                    <div class="grev-meter-labels">
                        <span>Poor</span>
                        <span>Average</span>
                        <span>Good</span>
                        <span>Star</span>
                    </div>
                    <div class="panel-muted" style="margin-top:6px;">Team rank #{team_rank}/{rank_total}</div>
                </div>
                <div class="overview-side">
                    <div class="section-label">Overview</div>
                    <div class="stats-grid overview-grid">
                        {"".join(stat_chips_overview)}
                    </div>
                </div>
            </div>
            <div class="section-label">Core Performance</div>
            <div class="stats-grid">
                {"".join(stat_chips_core)}
            </div>
            <div class="section-label">Context</div>
            <div class="context-summary">
                <div class="context-summary-grid">
                    <div class="context-row"><span class="context-key">Best map</span><span class="context-val">{best_map}</span></div>
                    <div class="context-row"><span class="context-key">Team rank</span><span class="context-val">#{team_rank}/{rank_total}</span></div>
                    <div class="context-row"><span class="context-key">Record</span><span class="context-val">{record_text}</span></div>
                    <div class="context-row"><span class="context-key">Best side split</span><span class="context-val">{side_split}</span></div>
                </div>
            </div>
            <div class="form-mini">
                <div class="section-label" style="margin-top:0;">Form (Last 10)</div>
                <div class="panel-muted">Form score <strong>{form_score:.1f}/100</strong></div>
                <div class="form-dot-row">{form_block_html}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Player Analytics")
    recent_window = (
        filtered_players.sort_values("date", ascending=False)
        .head(20)
        .sort_values("date")
        .copy()
    )
    if not recent_window.empty and go is not None:
        recent_window["match_index"] = range(1, len(recent_window) + 1)
        recent_window["rating"] = recent_window["kpd"].fillna(0.0)
        recent_window["wins"] = recent_window["wins"] if "wins" in recent_window.columns else 0
        recent_window["losses"] = recent_window["losses"] if "losses" in recent_window.columns else 0
        recent_window["result"] = recent_window["wins"].fillna(0) > recent_window["losses"].fillna(0)
        trend_chart = go.Figure()
        trend_chart.add_trace(
            go.Scatter(
                x=recent_window["match_index"],
                y=recent_window["rating"],
                mode="lines+markers",
                line=dict(color="#63b8ff", width=2.4),
                marker=dict(
                    size=9,
                    color=recent_window["result"].map({True: "#31d17b", False: "#ff6c7a"}),
                    line=dict(width=0),
                ),
                customdata=recent_window[["date", "map", "opponent_team", "wins", "losses", "kpd"]],
                hovertemplate=(
                    "Match: %{x}<br>Rating: %{y:.2f}<br>Date: %{customdata[0]}<br>"
                    "Map: %{customdata[1]}<br>Opponent: %{customdata[2]}<br>"
                    "W-L: %{customdata[3]}-%{customdata[4]}<br>K/D: %{customdata[5]:.2f}<extra></extra>"
                ),
                showlegend=False,
            )
        )
        trend_chart.update_layout(title="Recent Form (Last 20)")
        trend_chart.update_xaxes(title_text="Recent matches")
        trend_chart.update_yaxes(title_text="Rating", rangemode="normal")
        _apply_plotly_dark_style(trend_chart, height=280, hovermode="x unified")
    else:
        trend_chart = None

    map_perf = (
        filtered_players.groupby("map", as_index=False)["kpd"]
        .mean()
        .rename(columns={"kpd": "rating"})
        .sort_values("rating", ascending=False)
    )
    map_chart = None
    if not map_perf.empty and go is not None:
        map_chart = go.Figure(
            go.Bar(
                x=map_perf["rating"],
                y=map_perf["map"],
                orientation="h",
                marker=dict(color="#5ea9ff"),
                hovertemplate="Map: %{y}<br>Rating: %{x:.2f}<extra></extra>",
                showlegend=False,
            )
        )
        map_chart.update_layout(title="Map Performance")
        map_chart.update_xaxes(title_text="Rating")
        map_chart.update_yaxes(title_text=None, autorange="reversed")
        _apply_plotly_dark_style(map_chart, height=280)

    comparison_metrics = pd.DataFrame(
        [
            {"metric": "Rating", "player": metrics["grevscore"], "team_avg": _safe_mean(team_scope, "kpd")},
            {"metric": "K/D", "player": metrics["kd"], "team_avg": _safe_mean(team_scope, "kpd")},
            {
                "metric": "Impact",
                "player": metrics["impact"],
                "team_avg": _safe_mean(team_scope, "impact_score", _safe_mean(team_scope, "impact")),
            },
            {"metric": "HS%", "player": avg_hs, "team_avg": _safe_mean(team_scope, "hs_pct")},
            {"metric": "Acc%", "player": avg_acc, "team_avg": _safe_mean(team_scope, "accuracy_pct")},
            {"metric": "DPM", "player": metrics["dpm"], "team_avg": _safe_mean(team_scope, "dpm")},
        ]
    ).melt("metric", var_name="group", value_name="value")
    comparison_metrics["group"] = comparison_metrics["group"].map({"player": selected_player, "team_avg": "Team Avg"})
    comparison_chart = None
    if go is not None:
        comparison_chart = go.Figure()
        for group_name, color in [(selected_player, "#31d17b"), ("Team Avg", "#9da7bd")]:
            group_df = comparison_metrics[comparison_metrics["group"] == group_name]
            comparison_chart.add_trace(
                go.Bar(
                    x=group_df["value"],
                    y=group_df["metric"],
                    orientation="h",
                    name=group_name,
                    marker=dict(color=color),
                    hovertemplate="Metric: %{y}<br>Group: " + group_name + "<br>Value: %{x:.2f}<extra></extra>",
                )
            )
        comparison_chart.update_layout(title="Player vs Team Average", barmode="group")
        comparison_chart.update_xaxes(title_text="Value")
        comparison_chart.update_yaxes(title_text=None, categoryorder="array", categoryarray=list(reversed(comparison_metrics["metric"].drop_duplicates().tolist())))
        _apply_plotly_dark_style(comparison_chart, height=280)

    side_chart = None
    if not side_chart_data.empty and go is not None:
        side_chart = go.Figure(
            go.Bar(
                x=side_chart_data["side"],
                y=side_chart_data["rating"],
                marker=dict(color="#f0be4f"),
                hovertemplate="Side: %{x}<br>Avg K/D: %{y:.2f}<extra></extra>",
                showlegend=False,
            )
        )
        side_chart.update_layout(title="Side Split")
        side_chart.update_xaxes(title_text="Side")
        side_chart.update_yaxes(title_text="Avg K/D")
        _apply_plotly_dark_style(side_chart, height=280)

    top_row_left, top_row_right = st.columns(2)
    with top_row_left:
        if trend_chart is None:
            if go is None:
                _render_plotly_unavailable()
            else:
                st.info("Not enough recent match data for trend graph.")
        else:
            st.plotly_chart(trend_chart, use_container_width=True)
    with top_row_right:
        if map_chart is None:
            if go is None:
                _render_plotly_unavailable()
            else:
                st.info("No map data available for selected filters.")
        else:
            st.plotly_chart(map_chart, use_container_width=True)

    bottom_row_left, bottom_row_right = st.columns(2)
    with bottom_row_left:
        if comparison_chart is None:
            _render_plotly_unavailable()
        else:
            st.plotly_chart(comparison_chart, use_container_width=True)
    with bottom_row_right:
        if side_chart is None:
            if go is None:
                _render_plotly_unavailable()
            else:
                st.info("No side split data available for selected filters.")
        else:
            st.plotly_chart(side_chart, use_container_width=True)

    st.caption(f"Total rounds played in filter: {rounds}")

    st.subheader("Tactical Context for Selected Matches")
    if filtered_tactics.empty:
        st.info("No tactic data after side/date filters.")
    else:
        top_tactics = (
            filtered_tactics.groupby("tactic_name", as_index=False)[["wins", "losses"]]
            .sum()
            .assign(win_rate=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
            .sort_values(["wins", "win_rate"], ascending=False)
            .head(10)
        )
        st.dataframe(top_tactics, use_container_width=True, hide_index=True)

    st.subheader("Achievements")
    if player_ach.empty:
        st.info("No achievements found for this player.")
    else:
        achievement_html = "".join(_achievement_card_html(ach_row) for _, ach_row in player_ach.iterrows())
        achievement_list_class = "achievement-inline-list achievement-inline-list-single" if len(player_ach) == 1 else "achievement-inline-list"
        st.markdown(f"<div class='{achievement_list_class}'>{achievement_html}</div>", unsafe_allow_html=True)

    st.subheader("Full Player Match Stats")
    show_cols = [
        "date",
        competition_source_col,
        "map",
        "opponent_team",
        "tier",
        "kills",
        "deaths",
        "kpd",
        "accuracy_pct",
        "hs_pct",
        "mvps",
        "damage",
        "rounds_played",
    ]
    show_cols = [c for c in show_cols if c in filtered_players.columns]
    display_df = filtered_players[show_cols].rename(columns={competition_source_col: "competition"})
    st.dataframe(display_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)


def _teams_tactical_breakdown(tactics_df: pd.DataFrame, player_df: pd.DataFrame, competition_source_col: str) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="tactics",
        subtitle="Team tactical breakdowns, map outcomes, and strategic performance context.",
    )

    tier_lookup = (
        player_df.groupby("match_id", as_index=False)["tier"]
        .agg(lambda s: s.dropna().iloc[0] if not s.dropna().empty else None)
    )

    df = tactics_df.merge(
        tier_lookup,
        on="match_id",
        how="left",
    )
    df = df[df["date"].notna()].copy()
    if "total_rounds" in df.columns:
        df = df[df["total_rounds"].fillna(0) > 0]
    else:
        df = df[(df["wins"].fillna(0) + df["losses"].fillna(0)) > 0]
    if df.empty:
        st.warning("No tactic data found.")
        return

    tactic_opts = sorted(df["tactic_name"].dropna().unique().tolist())
    if not tactic_opts:
        st.warning("No tactics found in the selected data.")
        return

    st.subheader("Tactical Decision Console")
    with st.expander("Filters", expanded=False):
        filter_cols = st.columns(6)
        map_opts = sorted(df["map"].dropna().unique().tolist())
        with filter_cols[0]:
            maps = st.multiselect("Map", map_opts, default=[], key="tactic_map", placeholder="All")
        side_opts = sorted(df["side"].dropna().unique().tolist())
        with filter_cols[1]:
            sides = st.multiselect("Side", side_opts, default=[], key="tactic_side", placeholder="All")
        tier_opts = sorted(df["tier"].dropna().unique().tolist())
        with filter_cols[2]:
            tiers = st.multiselect("Tier", tier_opts, default=[], key="tactic_tier", placeholder="All")
        comp_opts = sorted(df[competition_source_col].dropna().unique().tolist())
        with filter_cols[3]:
            comps = st.multiselect("Event", comp_opts, default=[], key="tactic_event", placeholder="All")
        opp_opts = sorted(df["opponent_team"].dropna().unique().tolist())
        with filter_cols[4]:
            opps = st.multiselect("Opponent", opp_opts, default=[], key="tactic_opp", placeholder="All")
        round_type_opts = ["Pistol", "Eco", "Standard"]
        with filter_cols[5]:
            selected_round_types = st.multiselect(
                "Round Type",
                round_type_opts,
                default=round_type_opts,
                key="tactic_round_type_filter",
                placeholder="All",
            )
        selected_tactics = st.multiselect(
            "Tactics",
            tactic_opts,
            default=[],
            key="tactic_name_filter",
            placeholder="All (no filter)",
        )
        active_tactics = selected_tactics if selected_tactics else tactic_opts

    if sides:
        df = df[df["side"].isin(sides)]
    if maps:
        df = df[df["map"].isin(maps)]
    if tiers:
        df = df[df["tier"].isin(tiers)]
    if comps:
        df = df[df[competition_source_col].isin(comps)]
    if opps:
        df = df[df["opponent_team"].isin(opps)]
    df = df[df["tactic_name"].isin(active_tactics)].copy()

    expanded_round_type_df = _expand_tactics_by_round_type(df)
    selected_round_types = selected_round_types or round_type_opts
    expanded_round_type_df = expanded_round_type_df[
        expanded_round_type_df["round_type"].isin(selected_round_types)
    ].copy()
    allowed_keys = expanded_round_type_df[["tactic_name", "map", "side"]].drop_duplicates()
    if not allowed_keys.empty:
        df = df.merge(allowed_keys, on=["tactic_name", "map", "side"], how="inner")

    if df.empty or expanded_round_type_df.empty:
        st.warning("No tactics found for selected filters.")
        return

    map_side_totals = (
        df.groupby(["map", "side"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(total_map_side_rounds=lambda d: d["wins"] + d["losses"])
    )
    tactic_perf = (
        df.groupby(["tactic_name", "map", "side"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            times_used=lambda d: d["wins"] + d["losses"],
            win_pct=lambda d: (d["wins"] / d["times_used"].clip(lower=1) * 100).round(1),
            net_rounds=lambda d: d["wins"] - d["losses"],
        )
        .merge(map_side_totals[["map", "side", "total_map_side_rounds"]], on=["map", "side"], how="left")
        .assign(round_share_pct=lambda d: (d["times_used"] / d["total_map_side_rounds"].clip(lower=1) * 100).round(1))
    )
    if tactic_perf.empty:
        st.warning("No tactics found for selected filters.")
        return

    min_sample = int(st.slider("Minimum sample (uses)", 1, max(int(tactic_perf["times_used"].max()), 1), 1, key="tactic_min_sample"))
    tactic_perf = tactic_perf[tactic_perf["times_used"] >= min_sample].copy()
    if tactic_perf.empty:
        st.warning("No tactics meet the minimum sample threshold.")
        return

    total_rounds_selected = int(tactic_perf["times_used"].sum())
    tactic_perf["usage_pct"] = (tactic_perf["times_used"] / max(total_rounds_selected, 1) * 100).round(1)

    tier_perf = (
        df.groupby(["tactic_name", "map", "side", "tier"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(tier_win_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
    )
    tier_pivot = (
        tier_perf.pivot_table(
            index=["tactic_name", "map", "side"],
            columns="tier",
            values="tier_win_pct",
            aggfunc="first",
        )
        .rename(columns={tier: f"vs {tier} tier win %" for tier in ["S", "A", "B", "C"]})
        .reset_index()
    )
    tactic_perf = tactic_perf.merge(tier_pivot, on=["tactic_name", "map", "side"], how="left")
    for tier_col in ("vs S tier win %", "vs A tier win %", "vs B tier win %", "vs C tier win %"):
        if tier_col not in tactic_perf.columns:
            tactic_perf[tier_col] = pd.NA

    family_map = (
        expanded_round_type_df.groupby(["tactic_name", "map", "side"], as_index=False)["round_type"]
        .agg(lambda x: x.dropna().iloc[0] if not x.dropna().empty else "Unspecified")
        .rename(columns={"round_type": "family"})
    )
    tactic_perf = tactic_perf.merge(family_map, on=["tactic_name", "map", "side"], how="left")
    tactic_perf["family"] = tactic_perf["family"].fillna("Unspecified")

    ten_day_cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=10)
    active_tactic_keys = (
        df.loc[df["date"] >= ten_day_cutoff, ["tactic_name", "map", "side"]]
        .drop_duplicates()
    )
    if active_tactic_keys.empty:
        st.warning("No tactics have been used in the last 10 days for the selected filters.")
        return
    df = df.merge(active_tactic_keys, on=["tactic_name", "map", "side"], how="inner")
    tactic_perf = tactic_perf.merge(active_tactic_keys, on=["tactic_name", "map", "side"], how="inner")

    round_rows: list[dict[str, object]] = []
    for row in df.sort_values(["date", "match_id", "tactic_name"]).itertuples(index=False):
        row_dict = row._asdict()
        for _ in range(int(max(row_dict.get("wins", 0), 0))):
            round_rows.append({**row_dict, "round_result": 1})
        for _ in range(int(max(row_dict.get("losses", 0), 0))):
            round_rows.append({**row_dict, "round_result": -1})
    rounds_long = pd.DataFrame(round_rows)

    last10_records = []
    if not rounds_long.empty:
        grouped = rounds_long.groupby(["tactic_name", "map", "side"], as_index=False)
        for _, g in grouped:
            g = g.sort_values(["date", "match_id"]).copy()
            wins_last_10 = int((g["round_result"].tail(10) > 0).sum())
            uses_last_10 = int(min(10, len(g)))
            wins_last_5 = int((g["round_result"].tail(5) > 0).sum())
            uses_last_5 = int(min(5, len(g)))
            last10_records.append(
                {
                    "tactic_name": g["tactic_name"].iloc[0],
                    "map": g["map"].iloc[0],
                    "side": g["side"].iloc[0],
                    "last_10_usage_win_pct": round((wins_last_10 / max(uses_last_10, 1)) * 100, 1),
                    "recent_form_5": f"{wins_last_5}-{uses_last_5 - wins_last_5}",
                    "recent_form_10": f"{wins_last_10}-{uses_last_10 - wins_last_10}",
                    "trend_delta": round(((wins_last_5 / max(uses_last_5, 1)) - (wins_last_10 / max(uses_last_10, 1))) * 100, 1),
                }
            )
    last10_df = pd.DataFrame(last10_records)
    tactic_perf = tactic_perf.merge(last10_df, on=["tactic_name", "map", "side"], how="left")
    tactic_perf["last_10_usage_win_pct"] = tactic_perf["last_10_usage_win_pct"].fillna(tactic_perf["win_pct"])
    tactic_perf["trend"] = tactic_perf["trend_delta"].fillna(0).apply(
        lambda v: "Rising" if v >= 8 else ("Falling" if v <= -8 else "Stable")
    )

    def _confidence_label(row: pd.Series) -> str:
        uses = row["times_used"]
        win = row["win_pct"]
        if uses < 5:
            return "Too little sample"
        if uses < 8:
            return "Early signal"
        if uses >= 10 and win >= 60:
            return "Proven good"
        if uses >= 10 and win < 45:
            return "Proven poor"
        return "Early signal"

    tactic_perf["confidence"] = tactic_perf.apply(_confidence_label, axis=1)
    confidence_badges = {
        "Too little sample": "⚪ Too little sample",
        "Early signal": "🟡 Early signal",
        "Proven good": "🟢 Proven good",
        "Proven poor": "🔴 Proven poor",
    }
    tactic_perf["confidence_badge"] = tactic_perf["confidence"].map(confidence_badges).fillna("⚪ Too little sample")

    eco_context_bonus = 6.0
    tactic_perf["context_adjusted_win_pct"] = tactic_perf["win_pct"] + tactic_perf["family"].eq("Eco").astype(float) * eco_context_bonus

    def _action_label(row: pd.Series, avg_win: float) -> str:
        adjusted_win = row["context_adjusted_win_pct"]
        if adjusted_win >= 58 and row["times_used"] >= 10:
            return "Keep"
        if adjusted_win < 45 and row["times_used"] >= 10:
            return "Drop"
        if adjusted_win >= 60 and row["times_used"] < 6:
            return "Test More"
        if row["usage_pct"] > 12 and adjusted_win < avg_win:
            return "Rework"
        if row["usage_pct"] < 8 and adjusted_win >= 58 and row["times_used"] >= 6:
            return "Use More"
        return "Monitor"

    overall_avg_win = float(tactic_perf["context_adjusted_win_pct"].mean())
    tactic_perf["recommended_action"] = tactic_perf.apply(lambda r: _action_label(r, overall_avg_win), axis=1)

    def _reason_label(row: pd.Series) -> str:
        adjusted_win = row["context_adjusted_win_pct"]
        if row["times_used"] >= 12 and adjusted_win < 45:
            return "Poor overall in strong sample"
        if row["trend"] == "Falling" and row["last_10_usage_win_pct"] < row["win_pct"]:
            return "Poor recent form"
        if row["usage_pct"] >= 12 and adjusted_win < overall_avg_win:
            return "Overused, low return"
        if pd.notna(row.get("vs S tier win %")) and float(row.get("vs S tier win %", 0)) < 45:
            return "Bad vs strong teams"
        if row["round_share_pct"] >= 30 and adjusted_win < 50:
            return "Map-side liability"
        if row["times_used"] < 8:
            return "Low sample volatility"
        if row["family"] == "Eco" and row["win_pct"] < row["context_adjusted_win_pct"]:
            return "Eco context considered (back-foot rounds)"
        return "Monitor trend"

    tactic_perf["reason"] = tactic_perf.apply(_reason_label, axis=1)
    tactic_perf["urgency_score"] = (
        (50 - tactic_perf["context_adjusted_win_pct"]).clip(lower=0) * 1.3
        + tactic_perf["usage_pct"] * 0.9
        + tactic_perf["times_used"].clip(upper=30) * 0.5
    ).round(1)
    tactic_perf["tags"] = tactic_perf.apply(
        lambda r: ", ".join(
            [
                tag
                for tag in [
                    "Reliable" if (r["confidence"] == "Proven good") else None,
                    "Underused" if (r["recommended_action"] == "Use More") else None,
                    "Overused" if (r["recommended_action"] == "Rework") else None,
                    "Unclear sample" if (r["confidence"] == "Too little sample") else None,
                    "Falling off" if (r["trend"] == "Falling") else None,
                    "Map-specific" if (r["round_share_pct"] > 25) else None,
                ]
                if tag
            ]
        ),
        axis=1,
    )

    summary_keys = tactic_perf.apply(lambda r: f'{r["map"]} | {r["side"]} | {r["tactic_name"]}', axis=1)
    summary_key_df = tactic_perf.assign(summary_key=summary_keys)

    recent_usage_keys = (
        df.loc[df["date"] >= ten_day_cutoff, ["tactic_name", "map", "side"]]
        .drop_duplicates()
        .merge(summary_key_df[["tactic_name", "map", "side", "summary_key"]], on=["tactic_name", "map", "side"], how="inner")
    )
    summary_options = recent_usage_keys["summary_key"].drop_duplicates().tolist()
    if not summary_options:
        summary_options = summary_key_df["summary_key"].tolist()

    overall_wr = float((tactic_perf["wins"].sum() / max((tactic_perf["wins"].sum() + tactic_perf["losses"].sum()), 1)) * 100)
    proven = tactic_perf[tactic_perf["times_used"] >= max(min_sample, 8)].copy()
    if proven.empty:
        proven = tactic_perf.copy()
    best_proven = proven.sort_values(["win_pct", "times_used"], ascending=[False, False]).iloc[0]
    worst_proven = proven.sort_values(["win_pct", "times_used"], ascending=[True, False]).iloc[0]
    usage_avg = float(tactic_perf["usage_pct"].mean())
    overused_weak_pool = tactic_perf[(tactic_perf["usage_pct"] >= usage_avg) & (tactic_perf["win_pct"] < overall_avg_win)]
    overused_weak = (
        overused_weak_pool.sort_values(["usage_pct", "win_pct"], ascending=[False, True]).iloc[0]
        if not overused_weak_pool.empty
        else worst_proven
    )
    underused_strong_pool = tactic_perf[
        (tactic_perf["usage_pct"] < usage_avg) & (tactic_perf["win_pct"] >= max(overall_avg_win, 55)) & (tactic_perf["times_used"] >= 6)
    ]
    underused_strong = (
        underused_strong_pool.sort_values(["win_pct", "usage_pct"], ascending=[False, True]).iloc[0]
        if not underused_strong_pool.empty
        else best_proven
    )

    def _kpi_card(title: str, row: pd.Series, accent: str, tag: str) -> None:
        st.markdown(
            f"""
            <div class="panel-card" style="border-left:4px solid {accent}; padding:14px 16px;">
                <div class="panel-muted">{title}</div>
                <div style="font-weight:700;color:#f5f7fb;line-height:1.25;">{row["tactic_name"]}</div>
                <div class="panel-muted">{row["map"]} • {row["side"]}</div>
                <div style="color:#cfd6e5;font-size:0.84rem;">{row["win_pct"]:.1f}% WR across {int(row["times_used"])} uses</div>
                <div style="margin-top:6px;color:{accent};font-size:0.75rem;font-weight:700;">{tag}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    kpi_cols = st.columns(5)
    st.caption(f"Eco tactics are context-adjusted by +{eco_context_bonus:.0f}pp in decision scoring to reflect back-foot round economics.")
    with kpi_cols[0]:
        st.markdown(
            f"""
            <div class="panel-card" style="padding:14px 16px;">
                <div class="panel-muted">Overall tactic WR</div>
                <div style="font-size:1.25rem;font-weight:800;color:#f5f7fb;">{overall_wr:.1f}%</div>
                <div class="panel-muted">{int(tactic_perf["times_used"].sum())} tracked uses</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi_cols[1]:
        _kpi_card("Best proven", best_proven, "#31d17b", "Proven good")
    with kpi_cols[2]:
        _kpi_card("Worst proven", worst_proven, "#ff6c7a", "Needs rework")
    with kpi_cols[3]:
        _kpi_card("Overused weak", overused_weak, "#f0be4f", "Drop/Rework")
    with kpi_cols[4]:
        _kpi_card("Underused strong", underused_strong, "#60a5fa", "Use more")

    st.subheader("Decision layer")
    decision_left, decision_right = st.columns(2)
    needs_attention = tactic_perf[tactic_perf["recommended_action"].isin(["Drop", "Rework", "Test More"])].copy()
    needs_attention = needs_attention.sort_values(["urgency_score", "times_used"], ascending=[False, False])
    use_more = tactic_perf[tactic_perf["recommended_action"].isin(["Use More", "Keep"])].copy()
    use_more = use_more.sort_values(["win_pct", "times_used"], ascending=[False, False])

    with decision_left:
        st.markdown("#### Needs Attention")
        if needs_attention.empty:
            st.info("No urgent tactics flagged by the current rules.")
        else:
            st.dataframe(
                needs_attention[
                    ["tactic_name", "map", "side", "times_used", "win_pct", "last_10_usage_win_pct", "reason", "recommended_action", "urgency_score"]
                ]
                .rename(
                    columns={
                        "tactic_name": "Tactic",
                        "map": "Map",
                        "side": "Side",
                        "times_used": "Uses",
                        "win_pct": "Win %",
                        "last_10_usage_win_pct": "Last 10",
                        "reason": "Reason",
                        "recommended_action": "Action",
                        "urgency_score": "Severity",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )
    with decision_right:
        st.markdown("#### Use More / Keep")
        if use_more.empty:
            st.info("No high-value tactics found in the current filter scope.")
        else:
            st.dataframe(
                use_more[
                    ["tactic_name", "map", "side", "times_used", "win_pct", "last_10_usage_win_pct", "reason", "recommended_action"]
                ]
                .rename(
                    columns={
                        "tactic_name": "Tactic",
                        "map": "Map",
                        "side": "Side",
                        "times_used": "Uses",
                        "win_pct": "Win %",
                        "last_10_usage_win_pct": "Last 10",
                        "reason": "Reason",
                        "recommended_action": "Action",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

    st.subheader("Tactic performance table")
    perf_table = tactic_perf.rename(
        columns={
            "tactic_name": "Tactic",
            "map": "Map",
            "side": "Side",
            "times_used": "Uses",
            "wins": "Wins",
            "losses": "Losses",
            "win_pct": "Win %",
            "net_rounds": "Net rounds",
            "usage_pct": "Usage %",
            "last_10_usage_win_pct": "Last 10 Win %",
            "context_adjusted_win_pct": "Context Win %",
            "vs S tier win %": "vs S",
            "vs A tier win %": "vs A",
            "vs B tier win %": "vs B",
            "vs C tier win %": "vs C",
            "confidence_badge": "Confidence",
            "recommended_action": "Action",
        }
    )
    perf_cols = ["Tactic", "Map", "Side", "Uses", "Win %", "Context Win %", "Last 10 Win %", "Net rounds", "Usage %", "vs S", "vs A", "vs B", "vs C", "Confidence", "Action"]
    st.dataframe(perf_table[perf_cols].sort_values(["Win %", "Uses"], ascending=[False, False]), use_container_width=True, hide_index=True)

    selected_key = st.selectbox("Selected tactic summary", summary_options, key="selected_tactic_summary")
    selected_row = summary_key_df[summary_key_df["summary_key"] == selected_key].iloc[0]
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-muted">Selected tactic detail</div>
            <div class="panel-title">{selected_row["tactic_name"]}</div>
            <div class="panel-muted">{selected_row["map"]} • {selected_row["side"]} • {selected_row["recommended_action"]} • {selected_row["confidence_badge"]}</div>
            <div style="margin-top:6px;color:#cfd6e5;font-size:0.88rem;"><strong>Why flagged:</strong> {selected_row.get("reason", "Monitor trend")}</div>
            <div class="stats-grid">
                <div class="stat-chip"><div class="stat-label">Uses</div><div class="stat-value">{int(selected_row["times_used"])}</div></div>
                <div class="stat-chip"><div class="stat-label">WR</div><div class="stat-value">{selected_row["win_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Net rounds</div><div class="stat-value">{int(selected_row["net_rounds"])}</div></div>
                <div class="stat-chip"><div class="stat-label">Usage share</div><div class="stat-value">{selected_row["usage_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Last 5</div><div class="stat-value">{selected_row.get("recent_form_5", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">Last 10</div><div class="stat-value">{selected_row.get("recent_form_10", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">vs S</div><div class="stat-value">{selected_row.get("vs S tier win %", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">vs C</div><div class="stat-value">{selected_row.get("vs C tier win %", "n/a")}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Trend over time")
    selected_rounds = rounds_long[
        (rounds_long["tactic_name"] == selected_row["tactic_name"])
        & (rounds_long["map"] == selected_row["map"])
        & (rounds_long["side"] == selected_row["side"])
    ].sort_values(["date", "match_id"])
    if selected_rounds.empty:
        st.info("No round-level trend data available.")
    else:
        selected_rounds = selected_rounds.assign(
            use_idx=range(1, len(selected_rounds) + 1),
            rolling_5=lambda d: (d["round_result"].gt(0).rolling(5, min_periods=1).mean() * 100).round(1),
            rolling_10=lambda d: (d["round_result"].gt(0).rolling(10, min_periods=1).mean() * 100).round(1),
        )
        if go is None or make_subplots is None:
            _render_plotly_unavailable()
        else:
            trend_fig = make_subplots(
                rows=2,
                cols=1,
                shared_xaxes=True,
                vertical_spacing=0.08,
                row_heights=[0.35, 0.65],
            )
            trend_fig.add_trace(
                go.Scatter(
                    x=selected_rounds["use_idx"],
                    y=selected_rounds["round_result"],
                    mode="markers",
                    marker=dict(
                        size=9,
                        color=selected_rounds["round_result"].gt(0).map({True: "#31d17b", False: "#ff6c7a"}),
                        opacity=0.75,
                    ),
                    customdata=selected_rounds[["date", "match_id"]],
                    hovertemplate="Use: %{x}<br>Round result: %{y:+.0f}<br>Date: %{customdata[0]}<br>Match: %{customdata[1]}<extra></extra>",
                    showlegend=False,
                ),
                row=1,
                col=1,
            )
            trend_fig.add_trace(
                go.Scatter(
                    x=selected_rounds["use_idx"],
                    y=selected_rounds["rolling_5"],
                    mode="lines+markers",
                    name="rolling_5",
                    line=dict(color="#63b8ff", width=2),
                    marker=dict(size=6),
                    customdata=selected_rounds[["date", "match_id", "round_result", "rolling_10"]],
                    hovertemplate="Use: %{x}<br>Rolling 5: %{y:.1f}%<br>Date: %{customdata[0]}<br>Match: %{customdata[1]}<br>Round: %{customdata[2]:+.0f}<br>Rolling 10: %{customdata[3]:.1f}%<extra></extra>",
                ),
                row=2,
                col=1,
            )
            trend_fig.add_trace(
                go.Scatter(
                    x=selected_rounds["use_idx"],
                    y=selected_rounds["rolling_10"],
                    mode="lines+markers",
                    name="rolling_10",
                    line=dict(color="#f0be4f", width=2),
                    marker=dict(size=6),
                    customdata=selected_rounds[["date", "match_id", "round_result", "rolling_5"]],
                    hovertemplate="Use: %{x}<br>Rolling 10: %{y:.1f}%<br>Date: %{customdata[0]}<br>Match: %{customdata[1]}<br>Round: %{customdata[2]:+.0f}<br>Rolling 5: %{customdata[3]:.1f}%<extra></extra>",
                ),
                row=2,
                col=1,
            )
            trend_fig.update_xaxes(title_text="Match/Round order", row=2, col=1)
            trend_fig.update_yaxes(title_text="Round result (+1/-1)", row=1, col=1)
            trend_fig.update_yaxes(title_text="Rolling win rate %", row=2, col=1)
            _apply_plotly_dark_style(trend_fig, height=500, hovermode="x unified")
            st.plotly_chart(trend_fig, use_container_width=True)

    st.subheader("Map + side split heatmap")
    top_n_tactics = int(st.slider("Heatmap tactic limit", 6, 20, 15, key="heatmap_top_n"))
    heatmap_data = tactic_perf.copy()
    top_tactics = (
        heatmap_data.groupby("tactic_name", as_index=False)["times_used"]
        .sum()
        .sort_values("times_used", ascending=False)
        .head(top_n_tactics)["tactic_name"]
        .tolist()
    )
    heatmap_data = heatmap_data[heatmap_data["tactic_name"].isin(top_tactics)].copy()
    map_tabs = st.tabs(sorted(heatmap_data["map"].dropna().unique().tolist()))
    for map_name, map_tab in zip(sorted(heatmap_data["map"].dropna().unique().tolist()), map_tabs):
        with map_tab:
            map_heat = heatmap_data[heatmap_data["map"] == map_name].copy()
            side_order = [side for side in ["T", "CT"] if side in map_heat["side"].astype(str).unique().tolist()]
            if not side_order:
                side_order = sorted(map_heat["side"].astype(str).unique().tolist())
            tactic_order = (
                map_heat.groupby("tactic_name", as_index=False)["times_used"]
                .sum()
                .sort_values("times_used", ascending=False)["tactic_name"]
                .tolist()
            )
            if go is None:
                _render_plotly_unavailable()
            else:
                pivot = (
                    map_heat.pivot(index="tactic_name", columns="side", values="win_pct")
                    .reindex(index=tactic_order, columns=side_order)
                )
                text_vals = (
                    map_heat.pivot(index="tactic_name", columns="side", values="times_used")
                    .reindex(index=tactic_order, columns=side_order)
                    .fillna(0)
                    .astype(int)
                    .astype(str)
                )
                heatmap_fig = go.Figure(
                    data=go.Heatmap(
                        z=pivot.values,
                        x=pivot.columns.tolist(),
                        y=_wrap_labels(pd.Series(pivot.index.tolist()), width=28),
                        colorscale=[[0.0, "#e85c6b"], [0.5, "#f0be4f"], [1.0, "#44c06f"]],
                        zmin=0,
                        zmax=100,
                        text=text_vals.values,
                        texttemplate="%{text}",
                        hovertemplate="Tactic: %{y}<br>Side: %{x}<br>Win %: %{z:.1f}<br>Times used: %{text}<extra></extra>",
                        colorbar=dict(title="Win %"),
                    )
                )
                heatmap_fig.update_layout(title=f"{map_name} side split", margin=dict(l=220, r=24, t=48, b=48))
                heatmap_fig.update_xaxes(title_text="Side", side="top")
                heatmap_fig.update_yaxes(title_text="Tactic", autorange="reversed")
                _apply_plotly_dark_style(heatmap_fig, height=max(420, 40 * max(len(tactic_order), 8)))
                st.plotly_chart(heatmap_fig, use_container_width=True)

    st.subheader("Round share vs success")
    if go is None:
        _render_plotly_unavailable()
    else:
        confidence_colors = {"High": "#31d17b", "Medium": "#f0be4f", "Low": "#ff6c7a"}
        scatter_fig = go.Figure()
        for confidence in sorted(tactic_perf["confidence"].dropna().astype(str).unique().tolist()):
            subset = tactic_perf[tactic_perf["confidence"].astype(str) == confidence]
            scatter_fig.add_trace(
                go.Scatter(
                    x=subset["usage_pct"],
                    y=subset["win_pct"],
                    mode="markers",
                    name=confidence,
                    marker=dict(
                        size=subset["times_used"].clip(lower=1).pow(0.5) * 6,
                        color=confidence_colors.get(confidence, "#5ea9ff"),
                        sizemode="diameter",
                        opacity=0.82,
                        line=dict(width=1, color="rgba(10, 16, 27, 0.9)"),
                    ),
                    customdata=subset[["tactic_name", "map", "side", "times_used", "recommended_action"]],
                    hovertemplate=(
                        "Tactic: %{customdata[0]}<br>Map/Side: %{customdata[1]} / %{customdata[2]}<br>"
                        "Times used: %{customdata[3]}<br>Usage %: %{x:.1f}<br>Win %: %{y:.1f}<br>"
                        "Action: %{customdata[4]}<extra></extra>"
                    ),
                )
            )
        scatter_fig.update_layout(title="Round share vs success")
        scatter_fig.update_xaxes(title_text="Usage rate / round share %")
        scatter_fig.update_yaxes(title_text="Win rate %")
        _apply_plotly_dark_style(scatter_fig, height=400)
        st.plotly_chart(scatter_fig, use_container_width=True)

    st.subheader("By enemy tier")
    sel_tier = tier_perf[
        (tier_perf["tactic_name"] == selected_row["tactic_name"])
        & (tier_perf["map"] == selected_row["map"])
        & (tier_perf["side"] == selected_row["side"])
    ].copy()
    if sel_tier.empty:
        st.info("No tier-split data for selected tactic.")
    else:
        sel_tier["tier_adjusted_score"] = sel_tier["tier_win_pct"] * sel_tier["tier"].map({"S": 1.35, "A": 1.15, "B": 1.0, "C": 0.85}).fillna(1.0)
        tier_palette_domain = ["S", "A", "B", "C"]
        tier_palette_range = [TIER_COLOR_MAP[t] for t in tier_palette_domain]
        if go is None:
            _render_plotly_unavailable()
        else:
            tier_chart = go.Figure(
                go.Bar(
                    x=sel_tier["tier"],
                    y=sel_tier["tier_win_pct"],
                    marker=dict(color=sel_tier["tier"].map(TIER_COLOR_MAP).fillna("#5ea9ff")),
                    customdata=sel_tier[["wins", "losses", "tier_adjusted_score"]],
                    hovertemplate="Tier: %{x}<br>Wins: %{customdata[0]}<br>Losses: %{customdata[1]}<br>Win %: %{y:.1f}<br>Adjusted: %{customdata[2]:.1f}<extra></extra>",
                    showlegend=False,
                )
            )
            tier_chart.update_layout(title="By enemy tier")
            tier_chart.update_xaxes(title_text="Tier", categoryorder="array", categoryarray=["S", "A", "B", "C"])
            tier_chart.update_yaxes(title_text="Win rate %")
            _apply_plotly_dark_style(tier_chart, height=320)
            st.plotly_chart(tier_chart, use_container_width=True)

    st.subheader("Tactic family grouping")
    family_summary = (
        tactic_perf.groupby("family", as_index=False)
        .agg(
            total_rounds_played=("times_used", "sum"),
            total_wins=("wins", "sum"),
            total_losses=("losses", "sum"),
            most_used_tactic=("tactic_name", lambda s: s.value_counts().index[0] if not s.empty else None),
        )
        .assign(total_win_pct=lambda d: (d["total_wins"] / (d["total_wins"] + d["total_losses"]).clip(lower=1) * 100).round(1))
    )
    st.dataframe(family_summary, use_container_width=True, hide_index=True)

    def _render_family_breakdown(section_title: str, family_name: str, rounds_label: str) -> None:
        st.subheader(section_title)
        family_df = tactic_perf[tactic_perf["family"] == family_name].copy()
        if family_df.empty:
            st.info(f"No {family_name.lower()} tactics for the selected filters.")
            return

        c1, c2, c3 = st.columns(3)
        total_rounds = int(family_df["times_used"].sum())
        total_wins = float(family_df["wins"].sum())
        total_losses = float(family_df["losses"].sum())
        family_win_rate = (total_wins / max((total_wins + total_losses), 1) * 100)
        best_tactic = family_df.sort_values(["win_pct", "times_used"], ascending=[False, False]).iloc[0]["tactic_name"]
        c1.metric(rounds_label, total_rounds)
        c2.metric(f"{family_name} win rate", f"{family_win_rate:.1f}%")
        c3.metric(f"Best {family_name.lower()} tactic", best_tactic)

        map_breakdown = (
            family_df.groupby("map", as_index=False)
            .agg(rounds=("times_used", "sum"), wins=("wins", "sum"), losses=("losses", "sum"))
            .assign(win_rate=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
            .sort_values(["rounds", "win_rate"], ascending=[False, False])
        )
        st.caption("Split by map")
        st.dataframe(
            map_breakdown[["map", "rounds", "wins", "losses", "win_rate"]],
            use_container_width=True,
            hide_index=True,
        )

        for _, map_row in map_breakdown.iterrows():
            map_name = map_row["map"]
            map_df = family_df[family_df["map"] == map_name].copy()
            with st.expander(
                f'{map_name} — {int(map_row["rounds"])} rounds ({float(map_row["win_rate"]):.1f}% win rate)',
                expanded=False,
            ):
                side_summary = (
                    map_df.groupby("side", as_index=False)
                    .agg(rounds=("times_used", "sum"), wins=("wins", "sum"), losses=("losses", "sum"))
                    .assign(win_rate=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
                )
                st.dataframe(side_summary, use_container_width=True, hide_index=True)
                st.dataframe(
                    map_df[["tactic_name", "side", "times_used", "win_pct", "usage_pct", "trend", "recommended_action"]]
                    .sort_values(["win_pct", "times_used"], ascending=[False, False]),
                    use_container_width=True,
                    hide_index=True,
                )

    _render_family_breakdown("Pistol breakdown", "Pistol", "Pistol rounds")
    _render_family_breakdown("Eco breakdown", "Eco", "Eco rounds")
    _render_family_breakdown("Standard rounds section", "Standard", "Standard rounds")

    st.subheader("Recommended actions")
    recs = tactic_perf[["tactic_name", "map", "side", "times_used", "win_pct", "usage_pct", "trend", "confidence", "recommended_action"]].sort_values(
        ["recommended_action", "win_pct"], ascending=[True, False]
    )
    st.dataframe(recs, use_container_width=True, hide_index=True)

    st.subheader("Match context drilldown")
    drilldown = df[
        (df["tactic_name"] == selected_row["tactic_name"])
        & (df["map"] == selected_row["map"])
        & (df["side"] == selected_row["side"])
    ].copy()
    drill_cols = ["match_id", "opponent_team", "tier", "map", "side", "wins", "losses", competition_source_col, "date"]
    drill_df = drilldown[drill_cols].rename(columns={competition_source_col: "competition"})
    st.dataframe(drill_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)


def _medisports_vs_breakdown(
    tactics_df: pd.DataFrame,
    player_df: pd.DataFrame,
    competition_source_col: str,
) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="medisports_vs",
        subtitle="Head-to-head Medisports performance, opponent trends, and matchup insights.",
    )

    team_df = tactics_df[
        tactics_df["my_team"].astype(str).str.contains("ⓜ", regex=False, na=False)
    ].copy()
    if team_df.empty:
        st.warning("No Medisports tactics data found.")
        return

    if "tier" not in team_df.columns or team_df["tier"].isna().all():
        tier_lookup = (
            player_df.groupby("match_id", as_index=False)["tier"]
            .agg(lambda s: s.dropna().iloc[0] if not s.dropna().empty else pd.NA)
        )
        team_df = team_df.merge(tier_lookup, on="match_id", how="left")

    match_results = _build_match_level_results(team_df, competition_source_col)
    if match_results.empty:
        st.warning("No match-level results available.")
        return

    st.markdown("### A) Overall team health")
    c1, c2, c3 = st.columns([1.1, 1.2, 1.7])
    with c1:
        min_matches = int(st.slider("Minimum matches", 1, 8, 2, key="medisports_min_matches"))
    with c2:
        form_window = st.selectbox(
            "Form window",
            ["All time", "Last 10", "Last 20", "Last 30"],
            index=0,
            key="medisports_form_window",
        )
    with c3:
        comp_options = sorted(match_results["competition"].dropna().astype(str).unique().tolist())
        selected_comp = st.multiselect(
            "Tournament filter",
            comp_options,
            default=[],
            placeholder="All tournaments",
            key="medisports_comp_filter",
        )

    filtered = match_results.copy()
    if selected_comp:
        filtered = filtered[filtered["competition"].isin(selected_comp)]
    if form_window != "All time":
        n_recent = int(form_window.split(" ")[1])
        filtered = filtered.sort_values("date", ascending=False).head(n_recent)
    if filtered.empty:
        st.info("No matches left after filters.")
        return
    image_index = _build_image_index()
    role_blocks = [
        ("Top summary / health", "summary cards"),
        ("Auto insights", "summary cards"),
        ("Opponent summary / spotlight", "ranked visual rows"),
        ("Matchup strength + heatmap", "hero chart"),
        ("Tournament + tier context", "ranked visual rows"),
        ("Match explorer + opponent table", "detailed table"),
    ]
    st.markdown(
        "<div class='panel-card'><div class='panel-muted'>Section role map</div><div class='vs-role-grid'>"
        + "".join(
            f"<div class='vs-role-chip'><div class='vs-role-label'>{label}</div><div class='vs-role-value'>{value}</div></div>"
            for label, value in role_blocks
        )
        + "</div></div>",
        unsafe_allow_html=True,
    )

    vs_summary = (
        filtered.groupby("opponent_team", as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            draws=("match_result", lambda s: int((s == "Draw").sum())),
            round_wins=("round_wins", "sum"),
            round_losses=("round_losses", "sum"),
            tier=("tier", lambda s: s.dropna().astype(str).mode().iloc[0] if not s.dropna().empty else "—"),
            most_played_map=("map", lambda s: s.dropna().astype(str).mode().iloc[0] if not s.dropna().empty else "—"),
        )
        .assign(
            round_diff=lambda d: d["round_wins"] - d["round_losses"],
            win_rate_pct=lambda d: (
                pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                / (
                    pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                    + pd.to_numeric(d["losses"], errors="coerce").fillna(0)
                ).clip(lower=1)
                * 100
            ).round(1),
            round_win_pct=lambda d: (
                pd.to_numeric(d["round_wins"], errors="coerce").fillna(0)
                / (
                    pd.to_numeric(d["round_wins"], errors="coerce").fillna(0)
                    + pd.to_numeric(d["round_losses"], errors="coerce").fillna(0)
                ).clip(lower=1)
                * 100
            ).round(1),
            round_diff_per_match=lambda d: (d["round_diff"] / d["matches"].clip(lower=1)).round(2),
            record=lambda d: d["wins"].astype(str) + "-" + d["losses"].astype(str) + "-" + d["draws"].astype(str),
        )
        .sort_values(["round_diff", "win_rate_pct"], ascending=[False, False])
    )

    vs_summary["confidence"] = pd.cut(
        vs_summary["matches"],
        bins=[0, 1, 3, 5, 1000],
        labels=["Unreliable", "Limited", "Decent", "Strong"],
        include_lowest=True,
    ).astype(str)
    vs_summary["status"] = "Even"
    vs_summary.loc[(vs_summary["round_diff"] >= 8) | (vs_summary["win_rate_pct"] >= 65), "status"] = "Strong"
    vs_summary.loc[(vs_summary["round_diff"] <= -8) | (vs_summary["win_rate_pct"] <= 40), "status"] = "Weak"
    vs_summary.loc[vs_summary["matches"] < min_matches, "status"] = "Low Sample"

    map_rollup = (
        filtered.groupby("map", as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            round_diff=("round_diff", "sum"),
        )
        .assign(
            win_rate_pct=lambda d: (
                pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                / (
                    pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                    + pd.to_numeric(d["losses"], errors="coerce").fillna(0)
                ).clip(lower=1)
                * 100
            ).round(1)
        )
    )
    tier_rollup = (
        filtered.groupby("tier", as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            round_diff=("round_diff", "sum"),
        )
        .assign(
            win_rate_pct=lambda d: (
                pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                / (
                    pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                    + pd.to_numeric(d["losses"], errors="coerce").fillna(0)
                ).clip(lower=1)
                * 100
            ).round(1)
        )
    )
    tournament_rollup = (
        filtered.groupby("competition", as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            draws=("match_result", lambda s: int((s == "Draw").sum())),
            round_diff=("round_diff", "sum"),
            best_map=("map", lambda s: s.dropna().astype(str).mode().iloc[0] if not s.dropna().empty else "—"),
        )
        .assign(
            win_rate_pct=lambda d: (
                pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                / (
                    pd.to_numeric(d["wins"], errors="coerce").fillna(0)
                    + pd.to_numeric(d["losses"], errors="coerce").fillna(0)
                ).clip(lower=1)
                * 100
            ).round(1)
        )
    )
    tournament_rollup["competition_logo"] = tournament_rollup["competition"].apply(
        lambda comp: _competition_logo_uri(image_index, comp)
    )

    overall_matches = int(filtered["match_id"].nunique())
    overall_wins = int((filtered["match_result"] == "Win").sum())
    overall_losses = int((filtered["match_result"] == "Loss").sum())
    overall_win_rate = (overall_wins / max(overall_wins + overall_losses, 1)) * 100
    overall_round_diff = int(filtered["round_diff"].sum())
    overall_round_win_pct = (
        filtered["round_wins"].sum() / max(filtered["round_wins"].sum() + filtered["round_losses"].sum(), 1) * 100
    )

    best_map = map_rollup.sort_values(["win_rate_pct", "round_diff"], ascending=[False, False]).head(1)
    worst_map = map_rollup.sort_values(["win_rate_pct", "round_diff"], ascending=[True, True]).head(1)
    best_tier = tier_rollup.sort_values(["win_rate_pct", "round_diff"], ascending=[False, False]).head(1)
    worst_tier = tier_rollup.sort_values(["win_rate_pct", "round_diff"], ascending=[True, True]).head(1)
    reliable = vs_summary[vs_summary["matches"] >= min_matches]
    best_seg = reliable.head(1)
    worst_seg = reliable.sort_values(["round_diff", "win_rate_pct"], ascending=[True, True]).head(1)

    cards = [
        ("Matches", str(overall_matches)),
        ("Win rate", f"{overall_win_rate:.1f}%"),
        ("Round diff", f"{overall_round_diff:+d}"),
        ("Round win %", f"{overall_round_win_pct:.1f}%"),
        ("Best map", f'{best_map.iloc[0]["map"]} ({best_map.iloc[0]["win_rate_pct"]:.1f}%)' if not best_map.empty else "n/a"),
        ("Worst map", f'{worst_map.iloc[0]["map"]} ({worst_map.iloc[0]["win_rate_pct"]:.1f}%)' if not worst_map.empty else "n/a"),
        ("Best tier", f'{best_tier.iloc[0]["tier"]} ({best_tier.iloc[0]["win_rate_pct"]:.1f}%)' if not best_tier.empty else "n/a"),
        ("Worst tier", f'{worst_tier.iloc[0]["tier"]} ({worst_tier.iloc[0]["win_rate_pct"]:.1f}%)' if not worst_tier.empty else "n/a"),
        ("Best opponent segment", f'{best_seg.iloc[0]["opponent_team"]} ({int(best_seg.iloc[0]["round_diff"]):+d})' if not best_seg.empty else "n/a"),
        ("Worst opponent segment", f'{worst_seg.iloc[0]["opponent_team"]} ({int(worst_seg.iloc[0]["round_diff"]):+d})' if not worst_seg.empty else "n/a"),
    ]
    cards_html = "".join(
        f'<div class="stat-chip"><div class="stat-label">{label}</div><div class="stat-value">{value}</div></div>'
        for label, value in cards
    )
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-muted">At-a-glance layer</div>
            <div class="stats-grid" style="grid-template-columns: repeat(5, minmax(0, 1fr));">{cards_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### D) What needs fixing? (Auto insights)")
    insights = []
    if overall_win_rate < 50 and overall_round_diff > 0:
        insights.append("Win rate is low while round differential is positive (close losses / unstable conversion).")
    if not vs_summary[(vs_summary["win_rate_pct"] >= 70) & (vs_summary["matches"] < min_matches)].empty:
        insights.append("Several great-looking matchups are low sample and should be treated as tentative.")
    if not worst_map.empty:
        insights.append(
            f'Lowest-impact map is {worst_map.iloc[0]["map"]} with {worst_map.iloc[0]["win_rate_pct"]:.1f}% WR and {int(worst_map.iloc[0]["round_diff"]):+d} round diff.'
        )
    same_tier = tier_rollup[tier_rollup["tier"].astype(str).str.upper() == "A"]
    if not same_tier.empty and float(same_tier.iloc[0]["win_rate_pct"]) + 8 < overall_win_rate:
        insights.append("A-tier performance is significantly below your current baseline.")
    weak_tournaments = tournament_rollup[tournament_rollup["win_rate_pct"] < max(overall_win_rate - 10, 0)]
    if not weak_tournaments.empty:
        insights.append("At least one tournament underperforms your overall baseline by 10+ percentage points.")
    if not insights:
        insights.append("No major red flags triggered for the current filter setup.")
    st.markdown(
        "<div class='panel-card'>" + "".join(f"<div class='stat-label'>• {html.escape(i)}</div>" for i in insights[:6]) + "</div>",
        unsafe_allow_html=True,
    )

    st.markdown("### B) Who do we beat / lose to?")
    leaderboard = vs_summary[vs_summary["matches"] >= min_matches].copy()
    if leaderboard.empty:
        st.info("No opponents meet minimum matches.")
    else:
        leaderboard["rank"] = range(1, len(leaderboard) + 1)
        status_class = {"Strong": "vs-pill-good", "Even": "vs-pill-mid", "Weak": "vs-pill-bad", "Low Sample": "vs-pill-mid"}
        rows_html = []
        for _, row in leaderboard.head(12).iterrows():
            round_class = "vs-pill-good" if float(row["round_diff"]) >= 0 else "vs-pill-bad"
            wr_class = "vs-pill-good" if float(row["win_rate_pct"]) >= 55 else ("vs-pill-mid" if float(row["win_rate_pct"]) >= 45 else "vs-pill-bad")
            status = str(row["status"])
            rows_html.append(
                f"""
                <div class="ranked-row">
                    <div class="vs-pill">#{int(row["rank"])}</div>
                    <div class="rank-cell-main"><span class="rank-name">{html.escape(str(row["opponent_team"]))}</span></div>
                    <div class="stat-label">Matches <b>{int(row["matches"])}</b></div>
                    <div class="stat-label">Record <b>{html.escape(str(row["record"]))}</b></div>
                    <div><span class="vs-pill {wr_class}">WR {float(row["win_rate_pct"]):.1f}%</span></div>
                    <div><span class="vs-pill {round_class}">RD {int(row["round_diff"]):+d}</span></div>
                    <div><span class="vs-pill">Map {html.escape(str(row["most_played_map"]))}</span></div>
                    <div><span class="vs-pill {status_class.get(status, 'vs-pill-mid')}">{html.escape(status)}</span></div>
                </div>
                """
            )
        st.markdown("<div class='panel-card'><div class='ranked-list'>" + "".join(rows_html) + "</div></div>", unsafe_allow_html=True)

    st.markdown("### Spotlight")
    if not leaderboard.empty:
        cards = []
        cards.append(("Best matchup", leaderboard.sort_values(["round_diff", "win_rate_pct"], ascending=[False, False]).head(1)))
        cards.append(("Most played", leaderboard.sort_values("matches", ascending=False).head(1)))
        cards.append(("Worst matchup", leaderboard.sort_values(["round_diff", "win_rate_pct"], ascending=[True, True]).head(1)))
        rivalry = leaderboard[(leaderboard["matches"] >= max(2, min_matches)) & (leaderboard["round_diff"].abs() <= 4)]
        if not rivalry.empty:
            cards.append(("Rivalry", rivalry.sort_values("matches", ascending=False).head(1)))
        trap = leaderboard[(leaderboard["win_rate_pct"] >= 50) & (leaderboard["round_diff"] < 0)]
        if not trap.empty:
            cards.append(("Trap matchup", trap.sort_values("round_diff").head(1)))

        cols = st.columns(len(cards))
        for i, (label, frame) in enumerate(cards):
            row = frame.iloc[0]
            with cols[i]:
                st.markdown(
                    f"""
                    <div class="panel-card">
                        <div class="panel-muted">{label}</div>
                        <div class="panel-title">{row["opponent_team"]}</div>
                        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
                            <span class="vs-pill">{int(row["wins"])}W-{int(row["losses"])}L-{int(row["draws"])}D</span>
                            <span class="vs-pill {'vs-pill-good' if float(row["win_rate_pct"]) >= 55 else 'vs-pill-bad'}">WR {float(row["win_rate_pct"]):.1f}%</span>
                            <span class="vs-pill {'vs-pill-good' if int(row["round_diff"]) >= 0 else 'vs-pill-bad'}">RD {int(row["round_diff"]):+d}</span>
                            <span class="vs-pill">Map {row["most_played_map"]}</span>
                            <span class="vs-pill">Tier {row["tier"]}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("### C) Where do we perform best?")
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.markdown("#### Matchup strength (round differential)")
        diff_data = vs_summary[vs_summary["matches"] >= min_matches].sort_values("round_diff", ascending=False)
        if go is not None:
            wrapped_labels = _wrap_labels(diff_data["opponent_team"], width=26)
            bar_height = 30
            min_height = 340
            chart_height = max(min_height, len(diff_data) * bar_height + 80)
            longest_label = max((len(name) for name in diff_data["opponent_team"].astype(str)), default=0)
            left_margin = min(420, max(170, 80 + longest_label * 6))

            diff_chart = go.Figure(
                go.Bar(
                    x=diff_data["round_diff"],
                    y=wrapped_labels,
                    orientation="h",
                    marker_color=["#44c06f" if value >= 0 else "#e85c6b" for value in diff_data["round_diff"]],
                    customdata=diff_data[["opponent_team", "record", "matches", "round_diff_per_match"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Record: %{customdata[1]}<br>"
                        "Matches: %{customdata[2]}<br>"
                        "Round diff: %{x:+d}<br>"
                        "Round diff / match: %{customdata[3]:+.2f}<extra></extra>"
                    ),
                )
            )
            diff_chart.update_layout(
                height=chart_height,
                margin=dict(l=left_margin, r=20, t=20, b=45),
                bargap=0.22,
            )
            diff_chart.update_yaxes(showticklabels=True, title_text="Opponent", tickfont=dict(size=12), autorange="reversed")
            diff_chart.update_xaxes(title_text="Round differential", zeroline=True, zerolinewidth=1)
            _apply_plotly_dark_style(diff_chart, margin=dict(l=left_margin, r=20, t=20, b=45))
            st.plotly_chart(diff_chart, use_container_width=True)
        else:
            _render_plotly_unavailable()
    with chart_col_2:
        st.markdown("#### Matchup strength (Win/Lose)")
        wl_data = (
            vs_summary[vs_summary["matches"] >= min_matches]
            .assign(
                match_diff=lambda d: d["wins"] - d["losses"],
                win_loss_per_match=lambda d: ((d["wins"] - d["losses"]) / d["matches"].clip(lower=1)).round(2),
            )
            .sort_values("match_diff", ascending=False)
        )
        if go is not None:
            wrapped_labels = _wrap_labels(wl_data["opponent_team"], width=26)
            bar_height = 30
            min_height = 340
            chart_height = max(min_height, len(wl_data) * bar_height + 80)
            longest_label = max((len(name) for name in wl_data["opponent_team"].astype(str)), default=0)
            left_margin = min(420, max(170, 80 + longest_label * 6))

            wl_chart = go.Figure(
                go.Bar(
                    x=wl_data["match_diff"],
                    y=wrapped_labels,
                    orientation="h",
                    marker_color=["#44c06f" if value >= 0 else "#e85c6b" for value in wl_data["match_diff"]],
                    customdata=wl_data[["opponent_team", "record", "matches", "win_loss_per_match"]],
                    hovertemplate=(
                        "<b>%{customdata[0]}</b><br>"
                        "Record: %{customdata[1]}<br>"
                        "Matches: %{customdata[2]}<br>"
                        "Win/Lose diff: %{x:+d}<br>"
                        "Win/Lose diff / match: %{customdata[3]:+.2f}<extra></extra>"
                    ),
                )
            )
            wl_chart.update_layout(
                height=chart_height,
                margin=dict(l=left_margin, r=20, t=20, b=45),
                bargap=0.22,
            )
            wl_chart.update_yaxes(showticklabels=True, title_text="Opponent", tickfont=dict(size=12), autorange="reversed")
            wl_chart.update_xaxes(title_text="Win/Lose differential", zeroline=True, zerolinewidth=1)
            _apply_plotly_dark_style(wl_chart, margin=dict(l=left_margin, r=20, t=20, b=45))
            st.plotly_chart(wl_chart, use_container_width=True)
        else:
            _render_plotly_unavailable()

    st.markdown("#### Opponent × Map heatmap")
    map_summary = (
        filtered.groupby(["map", "opponent_team"], as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            round_diff=("round_diff", "sum"),
        )
        .assign(
            win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
            record=lambda d: d["wins"].astype(str) + "-" + d["losses"].astype(str),
        )
    )
    map_heat = map_summary[map_summary["matches"] >= min_matches]
    if map_heat.empty:
        st.info("No opponent-map pairs meet minimum matches.")
    else:
        if go is None:
            _render_plotly_unavailable()
        else:
            opponent_order = (
                map_heat.groupby("opponent_team", as_index=False)["win_rate_pct"]
                .mean()
                .sort_values("win_rate_pct", ascending=False)["opponent_team"]
                .tolist()
            )
            map_order = sorted(map_heat["map"].astype(str).unique().tolist())
            z = (
                map_heat.pivot(index="opponent_team", columns="map", values="win_rate_pct")
                .reindex(index=opponent_order, columns=map_order)
            )
            matches_text = (
                map_heat.pivot(index="opponent_team", columns="map", values="matches")
                .reindex(index=opponent_order, columns=map_order)
                .fillna(0)
                .astype(int)
                .astype(str)
            )
            heat_fig = go.Figure(
                data=go.Heatmap(
                    z=z.values,
                    x=z.columns.tolist(),
                    y=_wrap_labels(pd.Series(z.index.tolist()), width=26),
                    colorscale=[[0.0, "#e85c6b"], [0.5, "#f0be4f"], [1.0, "#44c06f"]],
                    zmin=0,
                    zmax=100,
                    text=matches_text.values,
                    texttemplate="%{text}",
                    hovertemplate="Opponent: %{y}<br>Map: %{x}<br>Win rate: %{z:.1f}%<br>Matches: %{text}<extra></extra>",
                    colorbar=dict(title="Win rate %"),
                )
            )
            longest_opp = max((len(name) for name in opponent_order), default=0)
            left_margin = min(420, max(170, 80 + longest_opp * 6))
            heat_fig.update_layout(title="Opponent × Map heatmap", margin=dict(l=left_margin, r=24, t=48, b=48))
            heat_fig.update_xaxes(title_text="Map")
            heat_fig.update_yaxes(title_text="Opponent", autorange="reversed")
            _apply_plotly_dark_style(heat_fig, height=max(420, len(opponent_order) * 32 + 120), hovermode="closest")
            st.plotly_chart(heat_fig, use_container_width=True)

    st.markdown("### Context sections")
    tcol1, tcol2 = st.columns(2)
    with tcol1:
        st.markdown("#### Tournament performance")
        t_rows = []
        sorted_tournament = tournament_rollup.sort_values(["round_diff", "win_rate_pct"], ascending=[False, False])
        for _, row in sorted_tournament.iterrows():
            wr_class = "vs-pill-good" if float(row["win_rate_pct"]) >= 55 else ("vs-pill-mid" if float(row["win_rate_pct"]) >= 45 else "vs-pill-bad")
            rd_class = "vs-pill-good" if int(row["round_diff"]) >= 0 else "vs-pill-bad"
            logo_html = (
                f'<img class="rank-logo" src="{row["competition_logo"]}" alt="competition logo">'
                if row["competition_logo"]
                else '<span class="rank-logo"></span>'
            )
            t_rows.append(
                f"""
                <div class="ranked-row" style="grid-template-columns: minmax(0, 1.8fr) repeat(6, minmax(0, 1fr));">
                    <div class="rank-cell-main">{logo_html}<span class="rank-name">{html.escape(str(row["competition"]))}</span></div>
                    <div class="stat-label">Matches <b>{int(row["matches"])}</b></div>
                    <div class="stat-label">Record <b>{int(row["wins"])}-{int(row["losses"])}-{int(row["draws"])}</b></div>
                    <div><span class="vs-pill {wr_class}">WR {float(row["win_rate_pct"]):.1f}%</span></div>
                    <div><span class="vs-pill {rd_class}">RD {int(row["round_diff"]):+d}</span></div>
                    <div><span class="vs-pill">Best map {html.escape(str(row["best_map"]))}</span></div>
                    <div></div>
                </div>
                """
            )
        st.markdown("<div class='panel-card'><div class='ranked-list'>" + "".join(t_rows) + "</div></div>", unsafe_allow_html=True)
    with tcol2:
        st.markdown("#### Tier performance ladder")
        ladder = tier_rollup.copy()
        ladder["Read"] = ladder["win_rate_pct"].apply(
            lambda v: "Strong" if v >= 60 else ("Even" if v >= 50 else ("Shaky" if v >= 45 else "Struggling"))
        )
        tier_order = pd.Categorical(ladder["tier"], categories=["S", "A", "B", "C"], ordered=True)
        ladder = ladder.assign(_tier_order=tier_order).sort_values("_tier_order").drop(columns="_tier_order")
        tier_rows = []
        for _, row in ladder.iterrows():
            read_class = "vs-pill-good" if row["Read"] == "Strong" else ("vs-pill-mid" if row["Read"] in {"Even", "Shaky"} else "vs-pill-bad")
            rd_class = "vs-pill-good" if int(row["round_diff"]) >= 0 else "vs-pill-bad"
            tier_rows.append(
                f"""
                <div class="tier-strip">
                    <div class="tier-strip-top">
                        <div class="panel-title">Tier {html.escape(str(row["tier"]))}</div>
                        <span class="vs-pill {read_class}">{row["Read"]}</span>
                    </div>
                    <div class="tier-strip-metrics">
                        <div>Matches <b>{int(row["matches"])}</b></div>
                        <div>Record <b>{int(row["wins"])}-{int(row["losses"])}</b></div>
                        <div><span class="vs-pill {'vs-pill-good' if float(row["win_rate_pct"]) >= 55 else 'vs-pill-bad'}">WR {float(row["win_rate_pct"]):.1f}%</span></div>
                        <div><span class="vs-pill {rd_class}">RD {int(row["round_diff"]):+d}</span></div>
                    </div>
                </div>
                """
            )
        st.markdown("<div class='panel-card'><div class='tier-strip-grid'>" + "".join(tier_rows) + "</div></div>", unsafe_allow_html=True)

    st.subheader("Full opponent table")
    opponent_table = vs_summary.copy()
    opponent_table["status_dot"] = opponent_table["status"].map(
        {"Strong": "🟢", "Even": "🟡", "Weak": "🔴", "Low Sample": "⚪"}
    ).fillna("🟡")
    opponent_table["map_pill"] = "🗺️ " + opponent_table["most_played_map"].astype(str)
    opponent_table["tier_pill"] = "🏷️ " + opponent_table["tier"].astype(str)
    opponent_table["status"] = opponent_table["status_dot"] + " " + opponent_table["status"].astype(str)
    st.dataframe(
        opponent_table[
            ["opponent_team", "matches", "record", "win_rate_pct", "round_diff", "map_pill", "tier_pill", "confidence", "status"]
        ].rename(
            columns={
                "opponent_team": "Opponent",
                "record": "Record",
                "win_rate_pct": "WR %",
                "round_diff": "RD",
                "map_pill": "Most played map",
                "tier_pill": "Tier",
                "confidence": "Sample",
                "status": "Status",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.subheader("Match-by-match explorer")
    result_filter = st.multiselect(
        "Result filter",
        ["Win", "Loss", "Draw"],
        default=["Win", "Loss", "Draw"],
        key="medisports_result_filter",
    )
    opp_filter = st.multiselect(
        "Opponent filter",
        sorted(filtered["opponent_team"].dropna().astype(str).unique().tolist()),
        default=[],
        key="medisports_opp_filter",
    )
    match_table = filtered[filtered["match_result"].isin(result_filter)].copy()
    if opp_filter:
        match_table = match_table[match_table["opponent_team"].isin(opp_filter)]
    match_table["competition_logo"] = match_table["competition"].apply(lambda comp: _competition_logo_uri(image_index, comp))
    match_table["result_pill"] = match_table["match_result"].map({"Win": "🟢 Win", "Loss": "🔴 Loss", "Draw": "🟡 Draw"}).fillna("⚪ Unknown")
    match_table["map_badge"] = "🗺️ " + match_table["map"].astype(str)
    match_table["tier_badge"] = "🏷️ " + match_table["tier"].astype(str)

    st.dataframe(
        match_table.sort_values("date", ascending=False)[
            [
                "date",
                "competition_logo",
                "competition",
                "opponent_team",
                "map_badge",
                "tier_badge",
                "round_wins",
                "round_losses",
                "round_diff",
                "result_pill",
            ]
        ],
        column_config={
            "competition_logo": st.column_config.ImageColumn("Logo", width="small"),
            "competition": st.column_config.TextColumn("Competition", width="medium"),
            "opponent_team": st.column_config.TextColumn("Opponent", width="medium"),
            "map_badge": st.column_config.TextColumn("Map"),
            "tier_badge": st.column_config.TextColumn("Tier"),
            "result_pill": st.column_config.TextColumn("Result"),
            "round_wins": st.column_config.NumberColumn("RW"),
            "round_losses": st.column_config.NumberColumn("RL"),
            "round_diff": st.column_config.NumberColumn("RD"),
        },
        use_container_width=True,
        hide_index=True,
    )

def main() -> None:
    player_df, tactics_df, achievements_df = _load_data()
    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    page = st.session_state["page"]
    competition_source_col = "competition"
    if page in {"profiles", "tactics", "medisports_vs"}:
        competition_view = st.radio(
            "Competition View",
            ["Raw competition names", "Grouped competition names"],
            index=0,
            horizontal=True,
            key="competition_view_mode",
        )
        competition_source_col = "competition" if competition_view == "Raw competition names" else "grouped_competition"

    if page == "profiles":
        _hltv_profile_view(player_df, tactics_df, achievements_df, competition_source_col)
    elif page == "tactics":
        _teams_tactical_breakdown(tactics_df, player_df, competition_source_col)
    elif page == "medisports_vs":
        _medisports_vs_breakdown(tactics_df, player_df, competition_source_col)
    else:
        _home()


if __name__ == "__main__":
    main()
