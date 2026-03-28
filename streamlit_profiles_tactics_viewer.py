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
import unicodedata

import numpy as np
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
    DATA_DIR / "play.csv",
    DATA_DIR / "Play.csv",
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


def _render_html(html_string: str) -> None:
    """Render trusted custom HTML blocks consistently."""
    st.markdown(html_string, unsafe_allow_html=True)


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
            border-color: rgba(255, 124, 136, 0.34);
            background: linear-gradient(180deg, rgba(56, 30, 35, 0.62), rgba(26, 18, 22, 0.66));
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
        .achievement-season {
            color: #9eb2d7;
            font-size: 0.5rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            font-weight: 760;
            line-height: 1.1;
            white-space: nowrap;
            text-align: center;
            opacity: 0.95;
        }
        .achievement-season-badge {
            justify-self: center;
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
        .achievement-tier-badge {
            width: 24px;
            height: 24px;
            min-width: 24px;
            min-height: 24px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0;
            margin: 0;
            border: 1px solid rgba(148, 173, 214, 0.44);
            box-shadow: 0 0 0 1px rgba(4, 9, 18, 0.64) inset;
            background: radial-gradient(circle at 35% 30%, rgba(37, 57, 88, 0.92), rgba(12, 20, 33, 0.98));
            flex: 0 0 auto;
            vertical-align: middle;
        }
        .achievement-tier-badge__text {
            display: block;
            margin: 0;
            padding: 0;
            font-size: 0.66rem;
            font-weight: 900;
            letter-spacing: 0;
            line-height: 1;
            text-transform: uppercase;
            transform: none;
        }
        .achievement-position {
            height: 24px;
            min-height: 24px;
            min-width: 34px;
            max-width: 64px;
            padding: 0 9px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 0.56rem;
            font-weight: 860;
            letter-spacing: 0.055em;
            text-transform: uppercase;
            border: 1px solid rgba(156, 178, 215, 0.44);
            background: rgba(10, 16, 27, 0.92);
            color: #dbe8ff;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            flex: 0 1 auto;
            line-height: 1;
        }
        .achievement-position.pos-gold {
            border-color: rgba(244, 199, 103, 0.7);
            background: linear-gradient(180deg, rgba(100, 70, 18, 0.82), rgba(48, 34, 10, 0.92));
            color: #ffebc0;
        }
        .achievement-position.pos-silver {
            border-color: rgba(191, 208, 232, 0.7);
            background: linear-gradient(180deg, rgba(73, 86, 105, 0.82), rgba(37, 46, 59, 0.92));
            color: #eaf4ff;
        }
        .achievement-position.pos-bronze {
            border-color: rgba(226, 157, 109, 0.7);
            background: linear-gradient(180deg, rgba(109, 65, 33, 0.82), rgba(58, 34, 18, 0.92));
            color: #ffe0c8;
        }
        .achievement-position.pos-ladder {
            border-color: rgba(108, 216, 199, 0.62);
            background: linear-gradient(180deg, rgba(27, 82, 83, 0.82), rgba(12, 41, 48, 0.92));
            color: #d6fffa;
        }
        .achievement-inline-name {
            color: #ebf3ff;
            font-weight: 820;
            line-height: 1.18;
            font-size: 0.53rem;
            letter-spacing: 0.045em;
            text-transform: uppercase;
            text-align: center;
            text-shadow: 0 1px 2px rgba(0, 0, 0, 0.7);
            white-space: normal;
            overflow: hidden;
            width: 100%;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
        }
        .achievement-footer .achievement-season {
            max-width: 100%;
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
        .compact-toolbar {
            border: 1px solid rgba(151, 166, 195, 0.28);
            border-radius: 14px;
            padding: 12px 14px 8px 14px;
            margin-bottom: 8px;
            background: linear-gradient(180deg, rgba(14, 21, 34, 0.88), rgba(10, 15, 24, 0.82));
        }
        .status-strip {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-bottom: 10px;
        }
        .status-chip {
            border: 1px solid rgba(151, 166, 195, 0.2);
            border-radius: 10px;
            background: rgba(11, 17, 28, 0.75);
            padding: 8px 10px;
        }
        .status-chip .label {
            color: #94a4c3;
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        .status-chip .value {
            color: #edf3ff;
            font-size: 0.88rem;
            font-weight: 750;
            margin-top: 2px;
            line-height: 1.2;
        }
        .kpi-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
        }
        .kpi-card {
            border: 1px solid rgba(151, 166, 195, 0.24);
            border-radius: 12px;
            background: rgba(12, 18, 29, 0.76);
            padding: 10px 12px;
        }
        .kpi-value { color: #f5f8ff; font-size: 1.36rem; font-weight: 850; line-height: 1.08; }
        .kpi-label {
            color: #9da7bd;
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-top: 4px;
        }
        .kpi-sub { color: #c8d4ed; font-size: 0.72rem; margin-top: 3px; }
        .insight-panel {
            border: 1px solid rgba(255, 194, 88, 0.45);
            border-left: 4px solid rgba(255, 194, 88, 0.9);
            border-radius: 12px;
            background: linear-gradient(180deg, rgba(56, 45, 24, 0.42), rgba(22, 18, 12, 0.44));
            padding: 12px 14px;
        }
        .insight-title {
            color: #ffe0a2;
            font-size: 0.88rem;
            font-weight: 800;
            margin-bottom: 6px;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        .insight-list {
            margin: 0;
            padding-left: 18px;
            color: #f5ddb2;
            font-size: 0.8rem;
            line-height: 1.45;
        }

        :root {
            --dashboard-max-width: 1720px;
            --dashboard-max-width-xl: 1840px;
        }

        .stApp [data-testid="stMainBlockContainer"] {
            width: 100%;
            max-width: var(--dashboard-max-width);
            margin-left: auto;
            margin-right: auto;
            padding-top: 1.1rem;
            padding-bottom: 1.6rem;
            padding-left: clamp(1.45rem, 3.3vw, 2.8rem);
            padding-right: clamp(1.45rem, 3.3vw, 2.8rem);
        }
        .cpl-hero {
            border: 1px solid rgba(156, 182, 236, 0.34);
            border-radius: 18px;
            padding: 10px 14px;
            margin-bottom: 10px;
            background:
                radial-gradient(circle at 12% 12%, rgba(61, 209, 132, 0.18), transparent 43%),
                radial-gradient(circle at 84% 16%, rgba(122, 166, 255, 0.19), transparent 42%),
                linear-gradient(140deg, #0f1728 0%, #0d1321 58%, #0a0f18 100%);
            box-shadow: 0 14px 32px rgba(0, 0, 0, 0.33);
        }
        .cpl-hero-grid {
            display: grid;
            grid-template-columns: minmax(160px, 220px) minmax(0, 1fr) minmax(60px, 78px);
            align-items: center;
            gap: 10px;
        }
        .cpl-hero-main-logo,
        .cpl-hero-side-logo {
            border-radius: 14px;
            border: 1px solid rgba(156, 182, 236, 0.42);
            background: linear-gradient(170deg, rgba(18, 28, 44, 0.88), rgba(9, 15, 28, 0.92));
            display: grid;
            place-items: center;
            padding: 8px 7px;
        }
        .cpl-hero-main-logo { min-height: 68px; }
        .cpl-hero-side-logo {
            min-height: 48px;
            max-width: 66px;
            justify-self: end;
        }
        .cpl-hero-main-logo img,
        .cpl-hero-side-logo img {
            width: 100%;
            object-fit: contain;
        }
        .cpl-hero-title {
            text-align: center;
            display: grid;
            gap: 3px;
            justify-items: center;
        }
        .cpl-hero-title h1 {
            margin: 0;
            color: #f6fbff;
            font-size: clamp(1.32rem, 1.62vw, 1.8rem);
            line-height: 1.05;
            letter-spacing: 0.01em;
        }
        .cpl-hero-subtitle {
            color: #c9d6ed;
            font-size: clamp(0.78rem, 0.92vw, 0.9rem);
            line-height: 1.24;
            margin-top: 1px;
        }
        .cpl-hero-badge {
            margin-top: 0;
            border-radius: 999px;
            border: 1px solid rgba(156, 182, 236, 0.5);
            background: rgba(13, 20, 35, 0.88);
            color: #dbe7ff;
            font-size: 0.64rem;
            font-weight: 760;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 5px 10px;
        }
        .cpl-top-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.95fr) minmax(0, 0.8fr);
            gap: 18px;
            align-items: stretch;
        }
        .cpl-player-card,
        .cpl-grev-card,
        .cpl-stats-card,
        .chart-panel,
        .impact-card,
        .form-card,
        .support-table {
            border: 1px solid rgba(151, 166, 195, 0.24);
            border-radius: 16px;
            background: linear-gradient(180deg, rgba(13, 20, 32, 0.92), rgba(8, 12, 20, 0.94));
            padding: 10px;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.3);
        }
        .panel-card {
            max-width: var(--dashboard-max-width);
            margin-left: auto;
            margin-right: auto;
            padding: 14px;
            margin-bottom: 14px;
        }
        .cpl-player-card,
        .cpl-grev-card,
        .cpl-stats-card {
            height: 100%;
        }
        .cpl-player-layout {
            display: grid;
            grid-template-columns: minmax(0, 0.94fr) minmax(0, 1.06fr);
            gap: 10px;
            height: 100%;
        }
        .cpl-player-left {
            display: grid;
            grid-template-columns: 118px minmax(0, 1fr);
            gap: 10px;
            align-content: start;
        }
        .portrait-shell {
            border: 1px solid rgba(122, 164, 240, 0.62);
            border-radius: 14px;
            background:
                radial-gradient(circle at 50% 0%, rgba(95, 173, 255, 0.35), transparent 58%),
                linear-gradient(180deg, rgba(30, 47, 78, 0.72), rgba(11, 17, 28, 0.92));
            min-height: 198px;
            overflow: hidden;
            display: grid;
            place-items: center;
            box-shadow: inset 0 0 0 1px rgba(197, 221, 255, 0.09), 0 12px 26px rgba(4, 9, 19, 0.55);
        }
        .portrait-shell img.player-headshot {
            width: 100%;
            height: 100%;
            min-height: 198px;
            object-fit: cover;
            object-position: center top;
        }
        .portrait-fallback {
            text-align: center;
            color: #c6d5f2;
            font-size: 0.76rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            padding: 12px;
            display: grid;
            gap: 6px;
        }
        .portrait-fallback-badge {
            width: 68px;
            height: 68px;
            border-radius: 50%;
            margin: 0 auto;
            display: grid;
            place-items: center;
            font-size: 1.55rem;
            font-weight: 800;
            color: #eef4ff;
            border: 1px solid rgba(165, 197, 255, 0.55);
            background: linear-gradient(180deg, rgba(94, 151, 245, 0.42), rgba(28, 40, 64, 0.9));
        }
        .cpl-player-right {
            border: 1px solid rgba(151, 166, 195, 0.2);
            border-radius: 12px;
            background: rgba(11, 17, 28, 0.66);
            padding: 10px;
            display: grid;
            grid-template-rows: auto 1fr auto;
            gap: 7px;
        }
        .cpl-player-right .section-label {
            margin: 0;
            font-size: 0.72rem;
        }
        .quick-profile-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 8px;
        }
        .quick-profile-tile {
            border: 1px solid rgba(151, 166, 195, 0.3);
            border-radius: 11px;
            background: linear-gradient(180deg, rgba(15, 22, 35, 0.92), rgba(10, 16, 27, 0.88));
            padding: 8px 10px;
            min-height: 52px;
        }
        .quick-profile-tile .label {
            color: #8fa0c2;
            font-size: 0.62rem;
            letter-spacing: 0.07em;
            text-transform: uppercase;
        }
        .quick-profile-tile .value {
            color: #f1f6ff;
            font-size: 0.88rem;
            font-weight: 760;
            margin-top: 2px;
            line-height: 1.18;
        }
        .cpl-stats-card {
            display: grid;
            align-content: start;
            gap: 9px;
            padding: 11px;
        }
        .headline-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }
        .headline-card {
            border: 1px solid rgba(151, 166, 195, 0.22);
            border-radius: 12px;
            padding: 9px;
            background: rgba(11, 17, 28, 0.78);
            min-height: 90px;
            display: grid;
            align-content: center;
        }
        .headline-label { color: #97a7c7; font-size: 0.68rem; text-transform: uppercase; letter-spacing: 0.08em; }
        .headline-value { color: #f5f8ff; font-size: 2.35rem; font-weight: 900; margin-top: 2px; line-height: 1.01; }
        .headline-sub { color: #c8d5f0; font-size: 0.7rem; margin-top: 2px; }
        .achievement-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 4px;
            align-items: flex-start;
        }
        .achievement-premium {
            width: 110px;
            height: 144px;
            border-radius: 12px;
            overflow: hidden;
            border: 1px solid rgba(151, 166, 195, 0.32);
            background: linear-gradient(180deg, rgba(19, 28, 43, 0.95), rgba(9, 14, 24, 0.96));
            flex: 0 0 110px;
            display: grid;
            grid-template-rows: 1fr auto;
            position: relative;
            box-shadow: inset 0 1px 0 rgba(210, 225, 247, 0.08), 0 10px 24px rgba(2, 6, 12, 0.28);
        }
        .achievement-top-row {
            position: absolute;
            top: 6px;
            left: 8px;
            right: 8px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 6px;
            min-height: 24px;
            z-index: 3;
            pointer-events: none;
        }
        .achievement-top-left {
            display: none;
        }
        .achievement-top-right,
        .achievement-badge-stack {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 6px;
            min-width: 0;
            max-width: 100%;
            flex: 0 0 auto;
        }
        .achievement-header-cluster {
            justify-self: center;
        }
        .achievement-premium .achievement-image-wrap {
            width: 100%;
            height: 100%;
            padding: 22px 10px 6px;
            box-sizing: border-box;
            background:
                radial-gradient(circle at 50% 38%, rgba(62, 90, 132, 0.42), rgba(12, 18, 30, 0.88) 70%),
                linear-gradient(180deg, rgba(21, 32, 49, 0.55), rgba(8, 14, 24, 0.94));
            position: relative;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        .achievement-premium img {
            width: 100%;
            height: 100%;
            object-fit: contain;
            object-position: center;
            display: block;
        }
        .achievement-header-gradient,
        .achievement-footer-gradient { display: none; }
        .achievement-footer {
            display: grid;
            align-content: end;
            justify-items: center;
            min-height: 38px;
            gap: 2px;
            padding: 6px 8px 8px;
            background: linear-gradient(180deg, rgba(13, 20, 33, 0.22), rgba(10, 16, 27, 0.88) 32%, rgba(8, 13, 22, 0.97));
        }
        @media (min-width: 1100px) {
            .achievement-top-row {
                top: 7px;
                left: 9px;
                right: 9px;
                gap: 7px;
            }
            .achievement-badge-stack {
                gap: 7px;
            }
            .achievement-premium .achievement-image-wrap {
                padding: 24px 11px 7px;
            }
            .achievement-footer {
                padding: 6px 9px 9px;
            }
        }
        .achievement-missing {
            color: #dce7ff;
            font-size: 0.58rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            text-align: center;
            border: 1px dashed rgba(151, 166, 195, 0.34);
            border-radius: 8px;
            padding: 8px 6px;
            background: rgba(9, 14, 24, 0.62);
            width: 100%;
        }
        .achievement-finish { display: none; }
        .achievement-inline-cabinet {
            border-top: none;
            padding-top: 0;
            min-height: 150px;
            align-content: start;
        }
        .achievement-inline-empty {
            margin-top: 10px;
            border: 1px dashed rgba(150, 170, 205, 0.35);
            border-radius: 12px;
            background: rgba(12, 19, 30, 0.68);
            padding: 11px 10px;
            text-align: center;
        }
        .achievement-empty-title {
            font-size: 0.66rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            color: #95a4c5;
            margin-bottom: 5px;
        }
        .achievement-empty-sub {
            color: #c8d4ea;
            font-size: 0.72rem;
        }
        .glow-s { box-shadow: 0 0 16px rgba(245, 196, 81, 0.26); }
        .glow-a { box-shadow: 0 0 15px rgba(156, 109, 246, 0.24); }
        .glow-b { box-shadow: 0 0 14px rgba(94, 169, 255, 0.24); }
        .glow-c { box-shadow: 0 0 13px rgba(78, 208, 131, 0.2); }
        .core-grid {
            margin-top: 6px;
            max-width: var(--dashboard-max-width);
            margin-left: auto;
            margin-right: auto;
        }
        .performance-grid {
            display: grid;
            grid-template-columns: repeat(5, minmax(0, 1fr));
            gap: 8px;
        }
        .metric-card {
            --tier-color: #f0be4f;
            --accent-1: #5ec7ff;
            border: 1px solid rgba(151,166,195,0.24);
            border-top: 2px solid color-mix(in srgb, var(--tier-color) 62%, #7ea9ff 38%);
            border-radius: 12px;
            padding: 8px 10px;
            background: linear-gradient(180deg, rgba(11,17,28,0.9), rgba(9,14,24,0.82));
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.02), 0 8px 18px rgba(0,0,0,0.18);
        }
        .metric-card.priority { min-height: 74px; }
        .metric-title { color: color-mix(in srgb, var(--accent-1) 62%, #d4def3 38%); font-size:0.58rem; text-transform:uppercase; letter-spacing:0.11em; font-weight:780; }
        .metric-value { color: color-mix(in srgb, var(--tier-color) 72%, #f8fbff 28%); font-size:1.46rem; font-weight:900; line-height:1.01; margin-top:3px; }
        .metric-state { font-size:0.67rem; font-weight:780; margin-top:3px; text-transform:uppercase; letter-spacing:0.07em; color: color-mix(in srgb, var(--tier-color) 82%, #ffffff 18%); }
        .metric-delta { margin-top:2px; font-size:0.62rem; color:#b5c6e7; letter-spacing:0.03em; }
        .metric-card.group-fragging { --accent-1: #ff8b6d; }
        .metric-card.group-accuracy { --accent-1: #66d3ff; }
        .metric-card.group-form { --accent-1: #56e1a8; }
        .metric-card.group-utility { --accent-1: #9f8dff; }
        .metric-card.tier-excellent { --tier-color: #31d17b; }
        .metric-card.tier-good { --tier-color: #5cb8ff; }
        .metric-card.tier-average { --tier-color: #f0be4f; }
        .metric-card.tier-poor { --tier-color: #ff9b48; }
        .metric-card.tier-very-poor { --tier-color: #ff5f6d; }
        .form-card .stat-chip {
            background: rgba(16, 23, 36, 0.68);
            border-color: rgba(151, 166, 195, 0.18);
        }
        .form-card .stat-value {
            font-size: 1.28rem;
            font-weight: 860;
        }
        .form-card .chip-bad {
            border-color: rgba(255, 125, 136, 0.3);
            background: linear-gradient(180deg, rgba(52, 28, 34, 0.52), rgba(24, 18, 22, 0.56));
            box-shadow: none;
        }
        .cpl-grev-card {
            display: grid;
            grid-template-rows: auto auto auto 1fr auto;
            align-items: center;
            text-align: center;
            padding: 13px 12px 11px;
            gap: 6px;
            background:
                radial-gradient(circle at 50% 0%, rgba(80, 138, 255, 0.35), rgba(13, 21, 34, 0.95) 72%),
                linear-gradient(180deg, rgba(10, 15, 25, 0.95), rgba(8, 13, 22, 0.96));
        }
        .cpl-grev-label {
            color: #b8caf0;
            font-size: 0.76rem;
            letter-spacing: 0.2em;
            text-transform: uppercase;
            font-weight: 820;
        }
        .cpl-grev-score {
            font-size: clamp(3.9rem, 5vw, 5.5rem);
            font-weight: 920;
            line-height: 0.89;
            letter-spacing: 0.01em;
            color: #f7fbff;
            text-shadow: 0 0 24px rgba(123, 177, 255, 0.2);
        }
        .cpl-grev-status {
            display: grid;
            justify-items: center;
            gap: 3px;
            margin-top: -1px;
            margin-bottom: 0;
        }
        .grev-status-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 999px;
            border: 1px solid rgba(151, 166, 195, 0.46);
            padding: 5px 12px;
            background: linear-gradient(180deg, rgba(21, 32, 51, 0.9), rgba(11, 18, 29, 0.88));
            color: #f1f5ff;
            font-size: 0.8rem;
            font-weight: 820;
        }
        .grev-percentile {
            color: #bfd0ed;
            font-size: 0.8rem;
            letter-spacing: 0.02em;
            font-weight: 700;
        }
        .cpl-grev-dial-wrap {
            display: grid;
            justify-items: center;
            align-items: center;
            margin: 1px 0 2px;
        }
        .cpl-grev-dial {
            width: min(100%, 360px);
            height: 220px;
        }
        .cpl-grev-dial .track {
            fill: none;
            stroke: rgba(129, 154, 196, 0.34);
            stroke-width: 18;
            stroke-linecap: round;
        }
        .cpl-grev-dial .fill {
            fill: none;
            stroke: url(#grevGrad);
            stroke-width: 18;
            stroke-linecap: round;
            transition: stroke-dasharray 0.35s ease;
        }
        .grev-micro-row {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 5px;
        }
        .grev-micro-item {
            border: 1px solid rgba(151, 166, 195, 0.22);
            border-radius: 10px;
            background: rgba(10, 16, 27, 0.7);
            padding: 6px 7px;
            text-align: center;
        }
        .grev-micro-item .label {
            color: #96a8ca;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.07em;
        }
        .grev-micro-item .value {
            color: #f2f6ff;
            font-size: 0.82rem;
            font-weight: 820;
            margin-top: 3px;
        }
        .block-container {
            max-width: var(--dashboard-max-width);
            margin-left: auto;
            margin-right: auto;
        }
        .cpl-hero {
            max-width: var(--dashboard-max-width);
            margin: 0 auto 8px;
            padding: 10px 12px;
            border-radius: 18px;
            border: 1px solid rgba(156, 182, 236, 0.34);
            background:
                radial-gradient(circle at 12% 12%, rgba(61, 209, 132, 0.18), transparent 43%),
                radial-gradient(circle at 84% 16%, rgba(122, 166, 255, 0.19), transparent 42%),
                linear-gradient(140deg, #0f1728 0%, #0d1321 58%, #0a0f18 100%);
            box-shadow: 0 14px 32px rgba(0, 0, 0, 0.33);
            display: grid;
            grid-template-columns: 110px 1fr 92px;
            gap: 16px;
            align-items: center;
        }
        .hero-logo,
        .hero-side-logo {
            border-radius: 14px;
            border: 1px solid rgba(156, 182, 236, 0.42);
            background: linear-gradient(170deg, rgba(18, 28, 44, 0.88), rgba(9, 15, 28, 0.92));
            display: grid;
            place-items: center;
            padding: 6px;
        }
        .hero-logo { min-height: 72px; }
        .hero-side-logo { min-height: 58px; }
        .hero-logo img,
        .hero-side-logo img {
            width: 100%;
            object-fit: contain;
        }
        .hero-copy {
            display: grid;
            gap: 5px;
            align-content: center;
        }
        .hero-copy h1 {
            margin: 0;
            color: #f6fbff;
            font-size: clamp(1.32rem, 1.62vw, 1.86rem);
            line-height: 1.04;
            letter-spacing: 0.01em;
        }
        .hero-copy p {
            margin: 0;
            color: #c9d6ed;
            font-size: clamp(0.78rem, 0.92vw, 0.92rem);
            line-height: 1.24;
        }
        .hero-badge {
            margin-top: 2px;
            border-radius: 999px;
            border: 1px solid rgba(156, 182, 236, 0.5);
            background: rgba(13, 20, 35, 0.88);
            color: #dbe7ff;
            font-size: 0.62rem;
            font-weight: 760;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            padding: 4px 9px;
            justify-self: start;
        }
        .cpl-top-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.45fr) minmax(0, 1.02fr) minmax(0, 0.86fr);
            gap: 24px;
            align-items: stretch;
        }
        .player-card,
        .grevscore-card,
        .stats-card {
            border: 1px solid rgba(155, 174, 214, 0.27);
            border-radius: 20px;
            background: linear-gradient(180deg, rgba(14, 20, 32, 0.95), rgba(9, 13, 22, 0.96));
            padding: 13px;
            min-height: 374px;
            box-shadow: 0 18px 34px rgba(0, 0, 0, 0.38);
        }
        .player-card-inner {
            display: grid;
            grid-template-columns: minmax(0, 1.2fr) minmax(0, 0.8fr);
            gap: 14px;
            height: 100%;
        }
        .player-main {
            display: grid;
            grid-template-columns: 138px minmax(0, 1fr);
            gap: 12px;
            align-content: start;
            padding-right: 6px;
        }
        .player-side {
            border: 1px solid rgba(151, 166, 195, 0.2);
            border-radius: 14px;
            background: linear-gradient(180deg, rgba(13, 20, 33, 0.75), rgba(9, 14, 24, 0.76));
            padding: 10px 11px;
            display: grid;
            grid-template-rows: auto 1fr auto;
            gap: 8px;
        }
        .player-side .section-label { margin: 0; font-size: 0.72rem; }
        .grevscore-wrap {
            display: grid;
            grid-template-rows: auto auto auto auto auto auto;
            align-items: center;
            justify-items: center;
            text-align: center;
            gap: 8px;
            height: 100%;
            align-content: center;
        }
        .grevscore-card {
            position: relative;
            overflow: hidden;
            border-color: rgba(130, 176, 255, 0.36);
            background:
                radial-gradient(circle at 14% 16%, rgba(100, 175, 255, 0.16), transparent 48%),
                radial-gradient(circle at 86% -8%, rgba(61, 212, 167, 0.14), transparent 44%),
                linear-gradient(164deg, rgba(14, 22, 36, 0.96), rgba(7, 12, 22, 0.98));
            box-shadow: 0 18px 34px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(217, 232, 255, 0.07);
        }
        .grevscore-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-radius: inherit;
            border: 1px solid rgba(189, 214, 255, 0.06);
        }
        .grevscore-card::after {
            content: "";
            position: absolute;
            left: 16px;
            right: 16px;
            top: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(175, 208, 255, 0.78), transparent);
            pointer-events: none;
        }
        .grevscore-card.tier-very-poor {
            box-shadow: 0 20px 34px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(255, 116, 139, 0.15), inset 0 0 34px rgba(139, 25, 54, 0.18);
        }
        .grevscore-card.tier-poor {
            box-shadow: 0 20px 34px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(255, 164, 82, 0.15), inset 0 0 34px rgba(139, 67, 25, 0.18);
        }
        .grevscore-card.tier-average {
            box-shadow: 0 20px 34px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(245, 204, 89, 0.15), inset 0 0 34px rgba(151, 104, 19, 0.2);
        }
        .grevscore-card.tier-good {
            box-shadow: 0 20px 34px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(78, 226, 225, 0.15), inset 0 0 36px rgba(23, 94, 111, 0.2);
        }
        .grevscore-card.tier-elite {
            box-shadow: 0 20px 34px rgba(0, 0, 0, 0.42), 0 0 0 1px rgba(89, 230, 149, 0.18), inset 0 0 36px rgba(20, 102, 55, 0.23);
        }
        .grevscore-label {
            color: #cbddff;
            font-size: 0.7rem;
            letter-spacing: 0.15em;
            text-transform: uppercase;
            font-weight: 900;
            text-shadow: 0 0 12px rgba(109, 185, 255, 0.24);
            text-align: center;
        }
        .grevscore-value {
            font-size: clamp(4rem, 5.9vw, 5.8rem);
            font-weight: 940;
            line-height: 0.9;
            letter-spacing: 0.008em;
            color: #f7fbff;
            text-shadow: 0 0 16px rgba(198, 222, 255, 0.35), 0 0 34px rgba(68, 222, 160, 0.24);
            text-align: center;
            width: 100%;
        }
        .grevscore-card.tier-very-poor .grevscore-value { color: #ffd8e0; text-shadow: 0 0 14px rgba(255, 147, 171, 0.42), 0 0 35px rgba(172, 33, 70, 0.4); }
        .grevscore-card.tier-poor .grevscore-value { color: #ffe4c4; text-shadow: 0 0 14px rgba(255, 177, 114, 0.4), 0 0 35px rgba(186, 87, 19, 0.36); }
        .grevscore-card.tier-average .grevscore-value { color: #fff0ca; text-shadow: 0 0 14px rgba(244, 194, 75, 0.38), 0 0 35px rgba(151, 108, 19, 0.34); }
        .grevscore-card.tier-good .grevscore-value { color: #d2f8ff; text-shadow: 0 0 14px rgba(109, 233, 235, 0.42), 0 0 35px rgba(25, 126, 142, 0.36); }
        .grevscore-card.tier-elite .grevscore-value { color: #d9ffe7; text-shadow: 0 0 14px rgba(88, 240, 152, 0.42), 0 0 35px rgba(27, 138, 69, 0.4); }
        .grevscore-status {
            color: #bcd2f6;
            font-size: 0.8rem;
            letter-spacing: 0.02em;
            font-weight: 760;
            line-height: 1.25;
            text-align: center;
            max-width: 290px;
        }
        .grevscore-status .accent { font-weight: 860; color: #9fd7ff; }
        .grevscore-card.tier-very-poor .grevscore-status .accent { color: #ff9fb3; }
        .grevscore-card.tier-poor .grevscore-status .accent { color: #ffc283; }
        .grevscore-card.tier-average .grevscore-status .accent { color: #ffd57f; }
        .grevscore-card.tier-good .grevscore-status .accent { color: #8cecf4; }
        .grevscore-card.tier-elite .grevscore-status .accent { color: #8cf2ba; }
        .grevscore-band {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: fit-content;
            border-radius: 999px;
            padding: 5px 14px;
            border: 1px solid rgba(151, 166, 195, 0.5);
            font-size: 0.66rem;
            letter-spacing: 0.1em;
            text-transform: uppercase;
            font-weight: 860;
            box-shadow: inset 0 0 0 1px rgba(236, 244, 255, 0.07), 0 0 16px rgba(54, 130, 202, 0.17);
        }
        .grevscore-band.good {
            color: #d8fff1;
            border-color: rgba(68, 226, 224, 0.55);
            background: linear-gradient(170deg, rgba(20, 77, 95, 0.8), rgba(13, 38, 46, 0.66));
        }
        .grevscore-band.mid {
            color: #fff0cf;
            border-color: rgba(240, 190, 79, 0.62);
            background: linear-gradient(170deg, rgba(75, 55, 20, 0.82), rgba(38, 30, 14, 0.68));
        }
        .grevscore-band.bad {
            color: #ffd7de;
            border-color: rgba(255, 115, 132, 0.62);
            background: linear-gradient(170deg, rgba(87, 35, 46, 0.82), rgba(45, 20, 28, 0.72));
        }
        .grevscore-meter {
            margin-top: 3px;
            display: grid;
            gap: 7px;
            width: 100%;
        }
        .grevscore-meter-track {
            width: 100%;
            border-radius: 999px;
            height: 12px;
            background: linear-gradient(90deg, rgba(109, 32, 51, 0.42), rgba(143, 115, 39, 0.4) 48%, rgba(23, 89, 56, 0.46));
            overflow: hidden;
            border: 1px solid rgba(146, 166, 205, 0.38);
            box-shadow: inset 0 1px 0 rgba(207, 226, 255, 0.11), inset 0 -8px 18px rgba(2, 6, 14, 0.58);
        }
        .grevscore-meter-fill {
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #ff6878 0%, #f0bf4f 52%, #49da9f 100%);
            box-shadow: 0 0 18px rgba(80, 225, 168, 0.34), inset 0 0 10px rgba(255, 255, 255, 0.22);
        }
        .grevscore-meter-labels {
            display: flex;
            justify-content: space-between;
            font-size: 0.62rem;
            color: #afc2e6;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            font-weight: 760;
        }
        .grevscore-meter-labels span:first-child { color: #ff9bab; }
        .grevscore-meter-labels span:nth-child(2) { color: #ffd986; }
        .grevscore-meter-labels span:last-child { color: #8df0b9; }
        .grevscore-meta {
            display: grid;
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 7px;
            width: 100%;
        }
        .grevscore-meta span {
            border: 1px solid rgba(151, 166, 195, 0.34);
            border-radius: 10px;
            background: linear-gradient(170deg, rgba(17, 31, 50, 0.84), rgba(9, 16, 28, 0.88));
            padding: 7px 7px 8px;
            text-align: center;
            font-size: 0.64rem;
            color: #dde9ff;
            font-weight: 770;
            box-shadow: inset 0 1px 0 rgba(211, 231, 255, 0.08);
        }
        .grevscore-card .grevscore-meta span:nth-child(1) { border-color: rgba(108, 183, 255, 0.44); color: #cfe9ff; }
        .grevscore-card .grevscore-meta span:nth-child(2) { border-color: rgba(104, 240, 194, 0.4); color: #ccffe8; }
        .grevscore-card .grevscore-meta span:nth-child(3) { border-color: rgba(246, 200, 116, 0.42); color: #ffe7bf; }
        .stats-card {
            display: grid;
            align-content: start;
            gap: 10px;
            padding: 12px;
            background:
                radial-gradient(circle at 16% 0%, rgba(72, 211, 194, 0.18), transparent 40%),
                radial-gradient(circle at 88% 8%, rgba(93, 176, 255, 0.18), transparent 36%),
                linear-gradient(160deg, rgba(13, 21, 36, 0.96), rgba(8, 13, 23, 0.98));
            border-color: rgba(125, 173, 245, 0.38);
            box-shadow: 0 18px 34px rgba(0, 0, 0, 0.42), inset 0 1px 0 rgba(210, 229, 255, 0.08);
        }
        .headline-header {
            display: grid;
            gap: 2px;
            margin-bottom: 1px;
            border-bottom: 1px solid rgba(140, 183, 245, 0.24);
            padding-bottom: 7px;
        }
        .headline-header .section-label {
            margin: 0;
            color: #d2e4ff;
            font-weight: 860;
            letter-spacing: 0.11em;
        }
        .headline-header-sub {
            color: #9ec6f6;
            font-size: 0.65rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            font-weight: 700;
        }
        .stats-tile-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
        }
        .headline-card {
            border: 1px solid rgba(151, 166, 195, 0.34);
            border-radius: 13px;
            padding: 10px 11px;
            background: linear-gradient(170deg, rgba(18, 29, 44, 0.94), rgba(9, 15, 26, 0.9));
            min-height: 134px;
            display: grid;
            align-content: center;
            gap: 2px;
            box-shadow: inset 0 1px 0 rgba(219, 234, 255, 0.08);
            position: relative;
            overflow: hidden;
        }
        .headline-card::before {
            content: "";
            position: absolute;
            left: 10px;
            right: 10px;
            top: 0;
            height: 1px;
            background: linear-gradient(90deg, transparent, rgba(184, 218, 255, 0.82), transparent);
            opacity: 0.72;
        }
        .headline-label { color: #95bce6; font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.11em; font-weight: 780; }
        .headline-value { color: #f5f8ff; text-shadow: 0 0 16px rgba(92,184,255,0.2); font-size: 2.22rem; font-weight: 910; margin-top: 1px; line-height: 1.01; }
        .headline-sub { color: #bfd6fa; font-size: 0.67rem; margin-top: 2px; }
        .headline-card.metric-rating { border-color: rgba(110, 189, 255, 0.44); background: linear-gradient(165deg, rgba(20, 47, 78, 0.84), rgba(10, 20, 35, 0.94)); box-shadow: inset 0 1px 0 rgba(207, 236, 255, 0.1), 0 0 18px rgba(66, 173, 255, 0.16); }
        .headline-card.metric-impact { border-color: rgba(115, 218, 223, 0.45); background: linear-gradient(165deg, rgba(24, 56, 74, 0.84), rgba(16, 26, 42, 0.95)); box-shadow: inset 0 1px 0 rgba(211, 248, 255, 0.09), 0 0 18px rgba(92, 206, 225, 0.17); }
        .headline-card.metric-form { border-color: rgba(244, 189, 98, 0.45); background: linear-gradient(165deg, rgba(75, 52, 24, 0.84), rgba(33, 24, 15, 0.95)); box-shadow: inset 0 1px 0 rgba(255, 232, 191, 0.08), 0 0 18px rgba(246, 178, 79, 0.18); }
        .headline-card.metric-matches { border-color: rgba(146, 176, 219, 0.42); background: linear-gradient(165deg, rgba(36, 52, 73, 0.84), rgba(16, 25, 39, 0.95)); box-shadow: inset 0 1px 0 rgba(218, 231, 255, 0.08), 0 0 16px rgba(118, 154, 212, 0.16); }
        .headline-card.metric-rating .headline-label,
        .headline-card.metric-rating .headline-value { color: #bde9ff; }
        .headline-card.metric-impact .headline-label,
        .headline-card.metric-impact .headline-value { color: #bff9f8; }
        .headline-card.metric-form .headline-label,
        .headline-card.metric-form .headline-value { color: #ffe0ab; }
        .headline-card.metric-matches .headline-label,
        .headline-card.metric-matches .headline-value { color: #d4e8ff; }
        .headline-card.metric-impact .headline-sub { color: #bde5ff; }
        .headline-card.metric-form .headline-sub { color: #ffd9a0; }
        .headline-card.metric-matches .headline-sub { color: #c8dbf8; }
        .stat-help { color:#9ce4c0; font-size:0.73em; margin-left:4px; cursor: help; }
        .chart-section-grid { display:grid; grid-template-columns: repeat(2,minmax(0,1fr)); gap:10px; }
        .pv-shell {
            max-width: var(--dashboard-max-width);
            margin: 0 auto 16px;
            display: grid;
            gap: 14px;
        }
        .pv-hero {
            position: relative;
            overflow: hidden;
            border-radius: 22px;
            border: 1px solid rgba(145, 169, 216, 0.48);
            background:
                radial-gradient(circle at 8% 8%, rgba(72, 224, 161, 0.24), transparent 38%),
                radial-gradient(circle at 82% -4%, rgba(92, 169, 255, 0.28), transparent 42%),
                radial-gradient(circle at 100% 80%, rgba(243, 186, 86, 0.12), transparent 36%),
                linear-gradient(140deg, rgba(15, 22, 36, 0.95), rgba(8, 12, 20, 0.96));
            box-shadow: 0 18px 34px rgba(0, 0, 0, 0.42), inset 0 0 0 1px rgba(208, 227, 255, 0.08);
            padding: 14px 16px 13px;
        }
        .pv-hero-grid {
            display: grid;
            grid-template-columns: 180px minmax(0, 1fr) minmax(300px, 0.85fr);
            gap: 12px;
            align-items: stretch;
        }
        .pv-portrait {
            border-radius: 16px;
            overflow: hidden;
            border: 1px solid rgba(157, 188, 236, 0.5);
            min-height: 222px;
            background: linear-gradient(180deg, rgba(23, 40, 66, 0.9), rgba(11, 17, 29, 0.96));
            box-shadow: 0 16px 30px rgba(1, 8, 18, 0.64);
        }
        .pv-portrait img.player-headshot {
            width: 100%;
            min-height: 222px;
            height: 100%;
            object-fit: cover;
        }
        .pv-main-copy {
            display: grid;
            align-content: center;
            gap: 8px;
            padding: 3px 0;
        }
        .pv-context-pill {
            display: inline-flex;
            width: fit-content;
            border-radius: 999px;
            border: 1px solid rgba(131, 195, 248, 0.52);
            background: linear-gradient(120deg, rgba(22, 63, 93, 0.7), rgba(10, 25, 43, 0.82));
            color: #d5efff;
            padding: 4px 11px;
            font-size: 0.62rem;
            text-transform: uppercase;
            letter-spacing: 0.11em;
            font-weight: 800;
        }
        .pv-name { font-size: clamp(2.2rem, 3.3vw, 3.2rem); color: #f4f9ff; font-weight: 920; line-height: 0.95; margin: 0; }
        .pv-teamline { display:flex; align-items:center; gap:8px; color:#cfe2ff; font-size:0.86rem; font-weight:760; }
        .pv-meta-row { display:flex; flex-wrap:wrap; gap:6px; }
        .pv-meta-chip {
            border-radius: 999px;
            border: 1px solid rgba(151, 173, 214, 0.44);
            background: linear-gradient(170deg, rgba(20, 39, 67, 0.66), rgba(10, 17, 30, 0.72));
            color: #dce9ff;
            font-size: 0.62rem;
            padding: 5px 9px;
            letter-spacing: 0.045em;
            font-weight: 700;
        }
        .pv-meta-chip.role { border-color: rgba(104, 211, 255, 0.55); color: #d4f2ff; }
        .pv-meta-chip.nation { border-color: rgba(113, 232, 196, 0.54); color: #d9fff1; }
        .pv-meta-chip.map { border-color: rgba(244, 190, 109, 0.5); color: #ffe8c2; }
        .pv-meta-chip.side { border-color: rgba(150, 176, 237, 0.48); color: #d9e5ff; }
        .pv-summary {
            border: 1px solid rgba(92, 180, 255, 0.36);
            border-left: 3px solid rgba(91, 224, 168, 0.86);
            padding: 7px 10px;
            background: linear-gradient(90deg, rgba(24, 63, 101, 0.34), rgba(18, 60, 52, 0.3) 46%, rgba(10, 19, 33, 0.22));
            color: #e3efff;
            font-size: 0.79rem;
            line-height: 1.34;
            border-radius: 10px;
            margin-top: 1px;
        }
        .pv-side-stack {
            display: grid;
            gap: 7px;
            align-content: center;
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .pv-side-tile {
            border: 1px solid rgba(143, 165, 208, 0.38);
            border-radius: 12px;
            min-height: 76px;
            padding: 7px 9px;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            text-align: center;
            background: linear-gradient(165deg, rgba(14, 29, 50, 0.78), rgba(10, 18, 31, 0.82));
            box-shadow: inset 0 0 0 1px rgba(216, 231, 255, 0.03);
            position: relative;
            overflow: hidden;
        }
        .pv-side-tile::before {
            content: "";
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 2px;
            background: linear-gradient(90deg, rgba(123, 196, 255, 0.75), rgba(93, 228, 181, 0.6));
            opacity: 0.8;
        }
        .pv-side-tile .k {
            color: #a9c6f5;
            font-size: 0.56rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            font-weight: 780;
        }
        .pv-side-tile .v {
            color: #f3f8ff;
            font-size: 1.08rem;
            font-weight: 870;
            margin-top: 5px;
            line-height: 1.03;
        }
        .pv-side-tile.rank { border-color: rgba(105, 198, 255, 0.44); }
        .pv-side-tile.rank .k { color: #8bd8ff; }
        .pv-side-tile.record { border-color: rgba(130, 224, 182, 0.4); }
        .pv-side-tile.record .k { color: #95f0c5; }
        .pv-side-tile.streak { border-color: rgba(255, 180, 112, 0.46); }
        .pv-side-tile.streak .k { color: #ffcda5; }
        .pv-side-tile.delta { border-color: rgba(166, 155, 245, 0.46); }
        .pv-side-tile.delta .k { color: #c4bbff; }
        .pv-side-tile .v.up { color: #84efb8; text-shadow: 0 0 12px rgba(77, 219, 148, 0.18); }
        .pv-side-tile .v.down { color: #ffb2a0; text-shadow: 0 0 12px rgba(245, 115, 115, 0.18); }
        .pv-side-tile .v.flat { color: #dbe8ff; }
        .pv-achievement-ribbon {
            border-radius: 16px;
            border: 1px solid rgba(143, 168, 213, 0.36);
            background:
                linear-gradient(130deg, rgba(22, 35, 58, 0.34), rgba(15, 40, 38, 0.24) 42%, rgba(8, 13, 22, 0.94)),
                linear-gradient(180deg, rgba(14, 20, 33, 0.9), rgba(8, 13, 22, 0.95));
            padding: 8px 10px 9px;
        }
        .pv-achievement-title {
            color:#cce6ff;
            font-size:0.68rem;
            font-weight:820;
            letter-spacing:0.1em;
            text-transform:uppercase;
            margin-bottom:6px;
            text-align: center;
        }
        .pv-achievement-scroll {
            display: flex;
            gap: 8px;
            overflow-x: auto;
            padding: 1px 1px 2px;
        }
        .pv-achievement-scroll .achievement-premium { width: 114px; height: 146px; flex: 0 0 114px; }
        .pv-score-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.15fr) minmax(0, 0.85fr);
            gap: 14px;
        }
        .analysis-module {
            border: 1px solid rgba(147, 173, 220, 0.3);
            border-radius: 17px;
            padding: 12px;
            background:
                radial-gradient(circle at 16% 0%, rgba(78, 146, 255, 0.12), transparent 42%),
                linear-gradient(170deg, rgba(15, 23, 38, 0.94), rgba(8, 13, 23, 0.97));
            box-shadow: 0 14px 30px rgba(0, 0, 0, 0.32);
            max-width: var(--dashboard-max-width);
            margin-left: auto;
            margin-right: auto;
        }
        .analysis-head {
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
            gap: 10px;
            margin-bottom: 10px;
        }
        .analysis-head h4 {
            margin: 0;
            color: #ecf3ff;
            font-size: 0.98rem;
            letter-spacing: 0.02em;
        }
        .analysis-head p {
            margin: 2px 0 0;
            color: #a5b7d8;
            font-size: 0.72rem;
            line-height: 1.3;
        }
        .analysis-chip {
            border-radius: 999px;
            border: 1px solid rgba(146, 170, 220, 0.46);
            background: rgba(17, 27, 44, 0.8);
            color: #d8e8ff;
            font-size: 0.66rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 760;
            padding: 5px 10px;
            white-space: nowrap;
        }
        .premium-card-grid {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 10px;
        }
        .premium-stat-card {
            border: 1px solid rgba(147, 173, 220, 0.28);
            border-radius: 13px;
            min-height: 114px;
            background: linear-gradient(180deg, rgba(19, 28, 46, 0.84), rgba(10, 16, 28, 0.9));
            padding: 10px;
            display: grid;
            place-items: center;
            text-align: center;
            gap: 4px;
        }
        .premium-stat-card .k {
            color: #9db2d8;
            font-size: 0.63rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            font-weight: 760;
        }
        .premium-stat-card .v {
            color: #f5f9ff;
            font-size: 1.24rem;
            font-weight: 880;
            line-height: 1.04;
        }
        .premium-stat-card .s {
            color: #c9d7f2;
            font-size: 0.7rem;
            font-weight: 650;
        }
        .premium-stat-card.form { border-color: rgba(90, 231, 174, 0.42); }
        .premium-stat-card.impact { border-color: rgba(246, 195, 109, 0.42); }
        .premium-stat-card.delta-positive .v { color: #90f1c0; }
        .premium-stat-card.delta-negative .v { color: #ffb1ad; }
        .pv-form-summary {
            display: grid;
            gap: 8px;
            border: 1px solid rgba(151, 166, 195, 0.24);
            border-radius: 14px;
            padding: 10px;
            background: linear-gradient(180deg, rgba(12, 18, 29, 0.84), rgba(9, 14, 24, 0.9));
        }
        .pv-form-track { display:grid; gap:5px; }
        .pv-form-track .label { color:#9eb2d8; font-size:0.63rem; letter-spacing:0.08em; text-transform:uppercase; }
        .pv-form-track .bar { height:8px; border-radius:999px; background:rgba(141,162,200,0.2); overflow:hidden; }
        .pv-form-track .bar > span { height:100%; display:block; background: linear-gradient(90deg, #ff7f8e 0%, #f2c25f 52%, #52ddab 100%); }
        .analysis-note {
            margin-top: 8px;
            border-radius: 12px;
            border: 1px solid rgba(141, 163, 201, 0.28);
            background: rgba(12, 18, 30, 0.7);
            padding: 8px 10px;
            color: #d7e5ff;
            font-size: 0.76rem;
            text-align: center;
        }
        .sparkline-strip {
            margin-top: 10px;
            display: grid;
            grid-template-columns: repeat(14, minmax(0, 1fr));
            gap: 5px;
        }
        .sparkline-strip span {
            display: block;
            border-radius: 999px;
            height: 8px;
            background: rgba(152, 173, 210, 0.25);
        }
        .section-block-title {
            margin: 10px auto 6px;
            color:#e9f1ff;
            font-size:1rem;
            font-weight:800;
            letter-spacing:0.02em;
            max-width: var(--dashboard-max-width);
        }
        .form-card, .impact-card, .support-table, .chart-panel {
            max-width: var(--dashboard-max-width);
            margin-left: auto;
            margin-right: auto;
        }
        .insight-shell {
            max-width: var(--dashboard-max-width);
            margin: 0 auto 14px;
            display: grid;
            gap: 12px;
        }
        .snapshot-grid {
            display: grid;
            grid-template-columns: minmax(0, 1.15fr) minmax(0, 1.15fr) minmax(0, 0.85fr) minmax(0, 0.85fr);
            gap: 10px;
        }
        .snapshot-card {
            border-radius: 14px;
            border: 1px solid rgba(148, 172, 214, 0.28);
            background: linear-gradient(180deg, rgba(18, 27, 44, 0.86), rgba(8, 13, 24, 0.94));
            min-height: 112px;
            display: grid;
            align-content: center;
            justify-items: center;
            text-align: center;
            gap: 5px;
            padding: 12px 10px;
        }
        .snapshot-card.feature {
            min-height: 126px;
            border-color: rgba(130, 176, 245, 0.46);
            box-shadow: inset 0 0 0 1px rgba(189, 211, 248, 0.06);
        }
        .snapshot-card.feature.impact { border-color: rgba(243, 191, 95, 0.5); }
        .snapshot-card .label {
            color: #a8bfdc;
            font-size: 0.62rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            font-weight: 770;
        }
        .snapshot-card .value {
            color: #f4f8ff;
            font-size: 1.34rem;
            line-height: 1.05;
            font-weight: 880;
        }
        .snapshot-card.feature .value { font-size: 1.56rem; }
        .snapshot-card .meta {
            color: #cedcf5;
            font-size: 0.72rem;
            line-height: 1.28;
            font-weight: 650;
        }
        .snapshot-insight-strip {
            border-radius: 12px;
            border: 1px solid rgba(130, 173, 232, 0.34);
            background: linear-gradient(100deg, rgba(16, 31, 56, 0.82), rgba(10, 17, 29, 0.92));
            padding: 10px 12px;
            text-align: center;
            color: #ddedff;
            font-size: 0.8rem;
            font-weight: 650;
        }
        .recent-form-shell {
            display: grid;
            gap: 12px;
        }
        .recent-form-meta {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
        }
        .form-stat-chip {
            border-radius: 11px;
            border: 1px solid rgba(148, 171, 212, 0.28);
            background: rgba(10, 16, 28, 0.84);
            padding: 8px;
            display: grid;
            justify-items: center;
            gap: 3px;
            min-height: 70px;
        }
        .form-stat-chip .k {
            color:#9fb6d8;
            font-size:0.6rem;
            letter-spacing:0.08em;
            text-transform:uppercase;
            font-weight:760;
        }
        .form-stat-chip .v {
            color:#f2f7ff;
            font-size:1rem;
            line-height:1.02;
            font-weight:860;
        }
        .form-stat-chip .s {
            color:#c6d7f1;
            font-size:0.66rem;
            font-weight:640;
        }
        .momentum-row {
            display: grid;
            gap: 8px;
            border-radius: 12px;
            border: 1px solid rgba(140, 164, 204, 0.26);
            background: rgba(9, 15, 25, 0.78);
            padding: 9px 10px;
        }
        .momentum-track {
            display: grid;
            grid-template-columns: 88px minmax(0, 1fr) 52px;
            align-items: center;
            gap: 8px;
        }
        .momentum-track .name {
            color:#a7bcdd;
            font-size:0.67rem;
            font-weight:740;
            text-transform:uppercase;
            letter-spacing:0.06em;
        }
        .momentum-track .bar {
            height: 8px;
            border-radius: 999px;
            background: rgba(144, 164, 198, 0.22);
            overflow: hidden;
        }
        .momentum-track .bar span {
            display: block;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #ff949e 0%, #f2c35d 52%, #58d8af 100%);
        }
        .momentum-track .num {
            color:#deebff;
            font-size:0.72rem;
            font-weight:730;
            text-align:right;
        }
        .compact-breakdown details {
            border-radius: 13px;
            border: 1px solid rgba(138, 165, 205, 0.3);
            background: rgba(9, 14, 24, 0.82);
            padding: 0;
        }
        .compact-breakdown summary {
            list-style: none;
            cursor: pointer;
            padding: 11px 12px;
            color: #e6f0ff;
            font-size: 0.82rem;
            font-weight: 760;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }
        .compact-breakdown summary::-webkit-details-marker { display:none; }
        .breakdown-body {
            border-top: 1px solid rgba(135, 162, 205, 0.26);
            padding: 10px 11px 11px;
            display: grid;
            gap: 12px;
        }
        .component-group {
            display: grid;
            gap: 7px;
        }
        .component-title {
            color:#cdddf8;
            font-size:0.72rem;
            text-transform:uppercase;
            letter-spacing:0.08em;
            font-weight:780;
        }
        .component-row {
            display:grid;
            grid-template-columns: 120px minmax(0,1fr) 50px;
            align-items:center;
            gap:8px;
        }
        .component-row .name {
            color:#a8bedf;
            font-size:0.7rem;
            font-weight:700;
        }
        .component-row .track {
            height:7px;
            border-radius:999px;
            background:rgba(141,164,202,0.22);
            overflow:hidden;
        }
        .component-row .track span {
            display:block;
            height:100%;
            background:linear-gradient(90deg, #6aaeff 0%, #54d9aa 100%);
            border-radius: inherit;
        }
        .component-row .val {
            color:#eff5ff;
            font-size:0.69rem;
            font-weight:730;
            text-align:right;
        }
        .tb-shell {
            max-width: var(--dashboard-max-width);
            margin: 0 auto 16px;
            display: grid;
            gap: 12px;
        }
        .tb-section-title {
            color: #eef5ff;
            font-size: 1.02rem;
            font-weight: 860;
            letter-spacing: 0.02em;
            margin: 6px 0 4px;
        }
        .tb-console {
            border-radius: 18px;
            border: 1px solid rgba(131, 176, 245, 0.42);
            background:
                radial-gradient(circle at 12% 0%, rgba(68, 217, 195, 0.2), transparent 34%),
                radial-gradient(circle at 92% 2%, rgba(88, 164, 255, 0.22), transparent 38%),
                linear-gradient(145deg, rgba(14, 23, 39, 0.96), rgba(8, 13, 24, 0.98));
            box-shadow: 0 16px 30px rgba(0, 0, 0, 0.4), inset 0 0 0 1px rgba(216, 230, 255, 0.06);
            padding: 12px 14px;
        }
        .tb-console-head {
            display: grid;
            gap: 4px;
            margin-bottom: 8px;
        }
        .tb-kpi-strip {
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 8px;
        }
        .tb-kpi {
            border-radius: 12px;
            border: 1px solid rgba(139, 167, 217, 0.36);
            background: linear-gradient(160deg, rgba(20, 34, 57, 0.84), rgba(9, 16, 28, 0.92));
            padding: 9px 10px;
        }
        .tb-kpi .k { color: #9fc3f8; font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.09em; font-weight: 780; }
        .tb-kpi .v { color: #f0f6ff; font-size: 1.04rem; font-weight: 860; margin-top: 4px; }
        .tb-slider-note {
            margin-top: 8px;
            border-radius: 10px;
            border: 1px solid rgba(116, 203, 255, 0.36);
            background: linear-gradient(90deg, rgba(29, 66, 101, 0.34), rgba(11, 22, 37, 0.46));
            color: #d2e9ff;
            font-size: 0.76rem;
            padding: 6px 10px;
        }
        .tb-action-col {
            border-radius: 14px;
            border: 1px solid rgba(140, 165, 211, 0.34);
            background: linear-gradient(180deg, rgba(14, 23, 37, 0.88), rgba(8, 12, 23, 0.9));
            padding: 8px;
            min-height: 100%;
        }
        .tb-action-head {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid rgba(161, 184, 227, 0.2);
            padding-bottom: 6px;
            margin-bottom: 7px;
            color: #e7f0ff;
            font-size: 0.8rem;
            font-weight: 830;
        }
        .tb-action-pill {
            border-radius: 999px;
            border: 1px solid currentColor;
            padding: 2px 8px;
            font-size: 0.62rem;
            font-weight: 780;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .tb-action-col.keep { border-color: rgba(74, 213, 143, 0.42); box-shadow: inset 0 0 0 1px rgba(85, 231, 153, 0.1); }
        .tb-action-col.use-more { border-color: rgba(103, 182, 255, 0.45); box-shadow: inset 0 0 0 1px rgba(109, 198, 255, 0.12); }
        .tb-action-col.monitor { border-color: rgba(235, 192, 103, 0.44); box-shadow: inset 0 0 0 1px rgba(245, 201, 109, 0.1); }
        .tb-action-col.rework { border-color: rgba(247, 158, 95, 0.45); box-shadow: inset 0 0 0 1px rgba(246, 157, 86, 0.11); }
        .tb-action-col.drop { border-color: rgba(241, 108, 128, 0.44); box-shadow: inset 0 0 0 1px rgba(244, 114, 136, 0.1); }
        .tb-decision-card {
            border-radius: 11px;
            border: 1px solid rgba(136, 160, 204, 0.33);
            background: linear-gradient(165deg, rgba(17, 30, 49, 0.88), rgba(10, 17, 29, 0.92));
            padding: 8px 10px;
            margin-bottom: 8px;
            position: relative;
            overflow: hidden;
        }
        .tb-decision-card::before {
            content: "";
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: var(--accent, rgba(132, 201, 255, 0.8));
            box-shadow: 0 0 12px var(--accent, rgba(132, 201, 255, 0.45));
        }
        .tb-card-head {
            margin-left: 6px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .tb-card-title { color: #f2f7ff; font-weight: 830; font-size: 0.84rem; }
        .tb-card-sub { color: #aacaef; font-size: 0.68rem; margin-left: 6px; margin-top: 2px; }
        .tb-card-meta { color: #d6e4fa; font-size: 0.7rem; margin-left: 6px; margin-top: 5px; line-height: 1.35; }
        .tb-card-chips {
            margin-left: 6px;
            margin-top: 6px;
            display: flex;
            flex-wrap: wrap;
            gap: 6px;
        }
        .tb-priority-pill {
            border-radius: 999px;
            padding: 2px 8px;
            border: 1px solid color-mix(in srgb, var(--accent, #7ab4ff) 68%, #ffffff 32%);
            background: color-mix(in srgb, var(--accent, #7ab4ff) 28%, rgba(11, 19, 32, 0.84));
            color: var(--accent-text, #e7f2ff);
            font-size: 0.62rem;
            font-weight: 810;
            letter-spacing: 0.04em;
            text-transform: uppercase;
        }
        .tb-card-reason {
            color: #d4e2f7;
            font-size: 0.73rem;
            margin-left: 6px;
            margin-top: 6px;
            line-height: 1.35;
            padding-top: 5px;
            border-top: 1px solid rgba(136, 161, 201, 0.22);
        }
        .tb-category-pill {
            border-radius: 999px;
            padding: 2px 8px;
            border: 1px solid color-mix(in srgb, var(--accent, #7ab4ff) 70%, #ffffff 30%);
            color: #e9f2ff;
            font-size: 0.62rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            font-weight: 800;
            background: color-mix(in srgb, var(--accent, #7ab4ff) 22%, rgba(10, 18, 31, 0.84));
            white-space: nowrap;
        }
        .tb-feature {
            border-radius: 16px;
            border: 1px solid rgba(133, 171, 233, 0.44);
            background:
                radial-gradient(circle at 7% 0%, rgba(74, 218, 186, 0.15), transparent 34%),
                radial-gradient(circle at 92% 0%, rgba(99, 163, 255, 0.16), transparent 38%),
                linear-gradient(155deg, rgba(13, 24, 43, 0.95), rgba(8, 13, 24, 0.97));
            padding: 12px 14px;
            box-shadow: 0 16px 30px rgba(0, 0, 0, 0.42), inset 0 0 0 1px rgba(204, 226, 255, 0.05);
        }
        .tb-badge-row { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 5px; }
        .tb-chip {
            border-radius: 999px;
            padding: 2px 8px;
            border: 1px solid rgba(140, 165, 212, 0.42);
            color: #deebff;
            font-size: 0.64rem;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            font-weight: 760;
            background: linear-gradient(180deg, rgba(28, 46, 74, 0.65), rgba(10, 17, 30, 0.72));
        }
        .tb-empty {
            border-radius: 14px;
            border: 1px dashed rgba(143, 169, 218, 0.45);
            background: linear-gradient(180deg, rgba(16, 27, 44, 0.72), rgba(8, 13, 24, 0.8));
            color: #c7d9f4;
            text-align: center;
            padding: 18px 12px;
            font-size: 0.82rem;
        }
        .tb-legend-strip {
            border-radius: 14px;
            border: 1px solid rgba(126, 166, 226, 0.34);
            background: linear-gradient(155deg, rgba(17, 30, 49, 0.85), rgba(10, 16, 29, 0.92));
            padding: 10px 12px;
            margin: 8px 0 2px;
        }
        .tb-legend-row {
            display: flex;
            flex-wrap: wrap;
            gap: 7px;
            margin-top: 7px;
        }
        .tb-legend-item {
            border-radius: 999px;
            border: 1px solid rgba(140, 165, 212, 0.42);
            background: linear-gradient(180deg, rgba(30, 49, 78, 0.64), rgba(11, 18, 32, 0.76));
            display: inline-flex;
            align-items: center;
            gap: 7px;
            padding: 4px 9px 4px 7px;
            color: #deebff;
            font-size: 0.66rem;
            font-weight: 760;
        }
        .tb-legend-swatch {
            width: 8px;
            height: 8px;
            border-radius: 999px;
            box-shadow: 0 0 8px currentColor;
            flex-shrink: 0;
        }
        .tb-tier-row {
            margin-left: 6px;
            margin-top: 7px;
            display: grid;
            grid-template-columns: repeat(4, minmax(0, 1fr));
            gap: 6px;
        }
        .tb-tier-chip {
            border-radius: 7px;
            border: 1px solid rgba(141, 170, 214, 0.34);
            background: linear-gradient(180deg, rgba(26, 40, 66, 0.74), rgba(9, 16, 30, 0.8));
            padding: 4px 6px;
            text-align: center;
            color: #daebff;
            font-size: 0.64rem;
            line-height: 1.22;
        }
        .tb-tier-chip .tier-label {
            color: #a9c6ef;
            font-size: 0.58rem;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            display: block;
        }
        .tb-module-grid {
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 10px;
            margin-top: 4px;
        }
        .tb-module {
            grid-column: span 12;
            border-radius: 16px;
            border: 1px solid rgba(133, 172, 230, 0.36);
            background:
                radial-gradient(circle at 11% 0%, rgba(75, 214, 186, 0.12), transparent 36%),
                radial-gradient(circle at 95% 0%, rgba(99, 161, 255, 0.12), transparent 40%),
                linear-gradient(160deg, rgba(15, 26, 44, 0.92), rgba(8, 13, 25, 0.96));
            padding: 12px;
        }
        .tb-module h4 {
            margin: 0;
            color: #eef5ff;
            font-size: 0.9rem;
            font-weight: 840;
            letter-spacing: 0.02em;
        }
        .tb-module-sub {
            margin-top: 4px;
            color: #a9c3e8;
            font-size: 0.72rem;
            line-height: 1.35;
        }
        .tb-alt-group { margin-top: 10px; }
        .tb-alt-group-head {
            color: #dbe9ff;
            font-size: 0.75rem;
            font-weight: 810;
            margin-bottom: 6px;
        }
        .tb-alt-item {
            border-radius: 12px;
            border: 1px solid rgba(131, 160, 206, 0.34);
            border-left: 3px solid var(--accent, #7cb6ff);
            background: linear-gradient(155deg, rgba(17, 29, 48, 0.8), rgba(10, 16, 28, 0.9));
            padding: 8px 10px;
            margin-bottom: 6px;
        }
        .tb-alt-item-top {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 8px;
        }
        .tb-alt-name { color: #f0f6ff; font-size: 0.79rem; font-weight: 790; }
        .tb-alt-meta { color: #c4d8f5; font-size: 0.69rem; margin-top: 4px; line-height: 1.35; }
        .tb-alt-reason {
            color: #afc4e4;
            font-size: 0.69rem;
            margin-top: 5px;
            padding-top: 5px;
            border-top: 1px solid rgba(135, 163, 208, 0.24);
        }
        .tb-balance-strip {
            margin-top: 9px;
            border-radius: 999px;
            height: 9px;
            overflow: hidden;
            background: rgba(137, 160, 201, 0.2);
        }
        .tb-balance-strip > span {
            display: block;
            height: 100%;
            border-radius: inherit;
            background: linear-gradient(90deg, #f58e86 0%, #f2be55 42%, #59d5a8 100%);
        }
        .tb-insight-grid {
            margin-top: 10px;
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 7px;
        }
        .tb-insight {
            border-radius: 11px;
            border: 1px solid rgba(136, 164, 211, 0.34);
            background: linear-gradient(165deg, rgba(20, 33, 54, 0.82), rgba(10, 16, 28, 0.92));
            padding: 8px 9px;
            color: #dce9ff;
            font-size: 0.7rem;
            line-height: 1.32;
        }
        .tb-insight.good { border-color: rgba(91, 215, 161, 0.42); }
        .tb-insight.warn { border-color: rgba(244, 187, 101, 0.42); }
        .tb-insight.bad { border-color: rgba(244, 128, 128, 0.42); }
        .tb-why-points {
            margin-top: 8px;
            display: grid;
            gap: 6px;
        }
        .tb-why-point {
            border-radius: 10px;
            border: 1px solid rgba(138, 164, 208, 0.35);
            background: linear-gradient(170deg, rgba(18, 31, 52, 0.82), rgba(10, 16, 29, 0.92));
            color: #d9e8ff;
            font-size: 0.72rem;
            line-height: 1.34;
            padding: 7px 9px;
        }
        .tb-recent-summary {
            margin-top: 6px;
            border-radius: 14px;
            border: 1px solid rgba(127, 167, 226, 0.36);
            background: linear-gradient(155deg, rgba(17, 31, 51, 0.86), rgba(9, 15, 28, 0.92));
            padding: 10px 12px;
        }
        .tb-recent-grid {
            display: grid;
            grid-template-columns: repeat(12, minmax(0, 1fr));
            gap: 10px;
            margin-top: 8px;
        }
        .tb-recent-card {
            grid-column: span 12;
            border-radius: 12px;
            border: 1px solid rgba(132, 163, 209, 0.34);
            background: linear-gradient(165deg, rgba(16, 29, 49, 0.84), rgba(9, 16, 29, 0.92));
            padding: 8px 10px;
        }
        .tb-recent-head { display:flex; justify-content:space-between; align-items:center; gap:8px; }
        .tb-recent-name { color:#f0f6ff; font-size:0.8rem; font-weight:810; }
        .tb-recent-meta { margin-top:5px; color:#cfe0fb; font-size:0.69rem; line-height:1.35; }
        .tb-recent-note {
            margin-top: 6px;
            padding-top: 6px;
            border-top: 1px solid rgba(134, 166, 212, 0.22);
            color: #bfd3f2;
            font-size: 0.69rem;
            line-height: 1.34;
        }
        .tb-wash-grid {
            display: grid;
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 10px;
            margin-top: 8px;
        }
        .tb-wash-col {
            border-radius: 14px;
            border: 1px solid rgba(132, 162, 208, 0.35);
            background: linear-gradient(160deg, rgba(16, 28, 47, 0.86), rgba(9, 15, 28, 0.94));
            padding: 10px 11px;
        }
        .tb-wash-col.good { border-color: rgba(85, 212, 161, 0.5); box-shadow: inset 0 0 0 1px rgba(89, 229, 173, 0.08); }
        .tb-wash-col.bad { border-color: rgba(241, 138, 122, 0.5); box-shadow: inset 0 0 0 1px rgba(243, 137, 120, 0.08); }
        .tb-wash-item {
            border-radius: 10px;
            border: 1px solid rgba(137, 167, 211, 0.32);
            background: linear-gradient(170deg, rgba(20, 33, 55, 0.82), rgba(10, 16, 29, 0.9));
            padding: 7px 8px;
            margin-top: 7px;
        }
        .tb-wash-item.good { border-color: rgba(80, 207, 156, 0.5); }
        .tb-wash-item.bad { border-color: rgba(237, 127, 113, 0.5); }
        .tb-wash-title { display:flex; justify-content:space-between; align-items:center; gap:7px; }
        .tb-wash-name { color:#eff6ff; font-size:0.76rem; font-weight:800; }
        .tb-wash-meta { margin-top:4px; color:#c7daf7; font-size:0.67rem; line-height:1.3; }
        .tb-wash-reason { margin-top:5px; color:#b7cdf0; font-size:0.68rem; line-height:1.32; }
        .roster-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
            gap: 14px;
            margin-top: 12px;
        }
        .roster-card {
            border: 1px solid rgba(151, 166, 195, 0.25);
            border-radius: 14px;
            background: linear-gradient(165deg, rgba(14, 21, 33, 0.96), rgba(10, 14, 23, 0.96));
            padding: 14px;
        }
        .roster-head { display: grid; grid-template-columns: 62px 1fr; gap: 10px; align-items: center; }
        .roster-photo {
            width: 62px; height: 62px; border-radius: 10px; object-fit: cover;
            border: 1px solid rgba(151, 166, 195, 0.4);
        }
        .roster-name { font-size: 1rem; font-weight: 750; color: #f2f6ff; line-height: 1.2; }
        .roster-meta { color: #9da7bd; font-size: 0.76rem; }
        .roster-kpis { margin-top: 10px; display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px; }
        .roster-kpi {
            border: 1px solid rgba(151, 166, 195, 0.2); border-radius: 10px; background: rgba(16, 24, 36, 0.72); padding: 6px 7px;
        }
        .roster-kpi .k { font-size: 0.67rem; color: #9da7bd; }
        .roster-kpi .v { font-size: 0.95rem; color: #f5f7fb; font-weight: 760; line-height: 1.1; }
        .match-card-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(245px, 1fr));
            gap: 10px;
            margin-top: 10px;
        }
        .match-card {
            border: 1px solid rgba(151, 166, 195, 0.25);
            border-radius: 12px;
            padding: 10px 11px;
            background: rgba(13, 20, 30, 0.82);
        }
        .match-card.win { border-color: rgba(49, 209, 123, 0.45); }
        .match-card.loss { border-color: rgba(255, 108, 122, 0.36); }
        .match-card.draw { border-color: rgba(240, 190, 79, 0.35); }
        .mini-note { font-size: 0.72rem; color: #9da7bd; margin-top: 4px; }
        .tb-family-card {
            border-radius: 12px;
            border: 1px solid rgba(136, 163, 212, 0.36);
            padding: 10px;
            background: linear-gradient(170deg, rgba(18, 34, 57, 0.86), rgba(10, 18, 31, 0.9));
        }
        .tb-family-card.pistol { border-color: rgba(96, 192, 255, 0.45); }
        .tb-family-card.eco { border-color: rgba(244, 186, 97, 0.44); }
        .tb-family-card.standard { border-color: rgba(101, 224, 163, 0.43); }
        .tb-note {
            color: #9ebeea;
            font-size: 0.72rem;
            letter-spacing: 0.04em;
        }
        @media (min-width: 1600px) {
            .cpl-top-grid,
            .cpl-hero,
            .core-grid,
            .section-block-title,
            .form-card, .impact-card, .support-table, .chart-panel,
            .panel-card,
            .tb-shell {
                max-width: var(--dashboard-max-width-xl);
            }
        }
        @media (max-width: 1280px) {
            .cpl-top-grid { grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr); gap: 16px; }
            .stats-card { grid-column: 1 / -1; }
            .player-card-inner { grid-template-columns: 1fr; }
            .player-main { grid-template-columns: 132px minmax(0, 1fr); }
            .chart-section-grid { grid-template-columns: 1fr; }
            .performance-grid { grid-template-columns: repeat(2,minmax(0,1fr)); }
            .pv-hero-grid { grid-template-columns: 150px minmax(0, 1fr); }
            .pv-side-stack { grid-column: 1 / -1; grid-template-columns: repeat(4, minmax(0, 1fr)); }
            .pv-score-grid { grid-template-columns: 1fr; }
        }
        @media (max-width: 1024px) {
            .cpl-top-grid { grid-template-columns: 1fr; }
            .cpl-hero { grid-template-columns: minmax(90px, 120px) minmax(0, 1fr) minmax(70px, 90px); }
            .pv-side-stack { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        }
        @media (max-width: 1200px) {
            .kpi-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
            .status-strip { grid-template-columns: 1fr; }
        }
        @media (max-width: 768px) {
            .stApp [data-testid="stMainBlockContainer"] {
                padding-left: 0.84rem;
                padding-right: 0.84rem;
                padding-top: 0.78rem;
            }
            .cpl-hero {
                padding: 10px;
                border-radius: 12px;
                margin-bottom: 8px;
                grid-template-columns: 1fr;
            }
            .hero-logo,
            .hero-side-logo {
                min-height: auto;
                width: 124px;
                margin: 0 auto;
                padding: 7px;
                border-radius: 10px;
            }
            .hero-side-logo {
                display: none;
            }
            .hero-copy h1 {
                font-size: clamp(1.45rem, 7vw, 1.95rem);
                line-height: 1.08;
                max-width: 11ch;
                margin: 0 auto;
                overflow-wrap: normal;
            }
            .hero-copy p {
                margin-top: 5px;
                font-size: clamp(0.78rem, 3.2vw, 0.92rem);
                line-height: 1.3;
                max-width: 34ch;
                margin-left: auto;
                margin-right: auto;
            }
            .hero-badge {
                font-size: 0.66rem;
                padding: 5px 8px;
            }
            .panel-card,
            .player-card,
            .grevscore-card,
            .stats-card {
                padding: 9px;
                border-radius: 12px;
            }
            .player-main {
                grid-template-columns: 1fr;
            }
            .portrait-shell,
            .portrait-shell img.player-headshot {
                min-height: 190px;
            }
            .profile-name { font-size: clamp(1.52rem, 6.2vw, 1.95rem); }
            .quick-profile-grid,
            .grevscore-meta {
                grid-template-columns: 1fr;
            }
            .achievement-row {
                gap: 6px;
            }
            .achievement-premium {
                width: 88px;
                height: 118px;
                flex-basis: 88px;
            }
            .achievement-top-row {
                top: 5px;
                left: 6px;
                right: 6px;
                min-height: 18px;
                gap: 4px;
            }
            .achievement-premium .achievement-image-wrap {
                padding: 17px 6px 4px;
            }
            .achievement-season {
                font-size: 0.44rem;
            }
            .achievement-position {
                height: 18px;
                min-height: 18px;
                min-width: 28px;
                max-width: 56px;
                font-size: 0.46rem;
                padding: 0 5px;
            }
            .achievement-tier-badge {
                width: 18px;
                height: 18px;
                min-width: 18px;
                min-height: 18px;
            }
            .achievement-tier-badge__text {
                font-size: 0.52rem;
            }
            .achievement-footer {
                min-height: 32px;
                gap: 1px;
                padding: 4px 6px 6px;
            }
            .stats-tile-grid { gap: 7px; }
            .stats-tile { min-height: 82px; }
            .stats-tile .value { font-size: 1.36rem; }
            .grevscore-gauge svg { height: 172px; }
            .pv-hero-grid { grid-template-columns: 1fr; }
            .pv-portrait { min-height: 188px; }
            .pv-portrait img.player-headshot { min-height: 188px; }
            .pv-side-stack { grid-template-columns: 1fr; }
            .tb-wash-grid { grid-template-columns: 1fr; }
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
        f'<img src="{_image_to_data_uri(MEDISPORTS_LOGO)}" alt="Medicart logo" style="max-width:170px;">'
        if MEDISPORTS_LOGO.exists()
        else '<span style="color:#c7d5f1;font-size:0.8rem;">Medicart logo missing</span>'
    )
    cpl_logo_html = (
        f'<img src="{_image_to_data_uri(CPL_LOGO)}" alt="CPL logo" style="max-width:54px;">'
        if CPL_LOGO.exists()
        else '<span style="color:#c7d5f1;font-size:0.8rem;">CPL logo missing</span>'
    )
    st.markdown(
        f"""
        <section class="cpl-hero">
            <div class="hero-logo">{medicart_logo_html}</div>
            <div class="hero-copy">
                <h1>Grev's CPL Dashboard</h1>
                <p>Medicart analytics, player profiles, tactics, and event breakdowns.</p>
                <div class="hero-badge">S10 ACTIVE</div>
            </div>
            <div class="hero-side-logo">{cpl_logo_html}</div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    nav_labels = {
        "front_page": "🧭 Front Page",
        "profiles": "👤 HLTV CPL Profile Viewer",
        "tactics": "📊 Teams Tactical Breakdown",
        "medisports_vs": "⚔️ Medisports Vs Breakdown",
        "tournament_summary": "🏆 Tournament Summary",
        "opponent_review": "🕵️ Opponent Review",
        "tactical_set": "🧠 Tactical Set Recommendations",
    }
    selected_nav = st.radio(
        "Dashboard View",
        options=list(nav_labels.keys()),
        index=list(nav_labels.keys()).index(active_page) if active_page in nav_labels else 0,
        format_func=lambda k: nav_labels[k],
        horizontal=True,
        label_visibility="collapsed",
        key=f"hero_nav_radio_{active_page}",
    )
    if selected_nav != active_page:
        st.session_state["page"] = selected_nav
        st.rerun()


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


SMALLCAPS_MAP = str.maketrans(
    {
        "ᴍ": "m",
        "ᴀ": "a",
        "ʙ": "b",
        "ᴄ": "c",
        "ᴅ": "d",
        "ᴇ": "e",
        "ꜰ": "f",
        "ɢ": "g",
        "ʜ": "h",
        "ɪ": "i",
        "ᴊ": "j",
        "ᴋ": "k",
        "ʟ": "l",
        "ᴍ": "m",
        "ɴ": "n",
        "ᴏ": "o",
        "ᴘ": "p",
        "ǫ": "q",
        "ʀ": "r",
        "s": "s",
        "ᴛ": "t",
        "ᴜ": "u",
        "ᴠ": "v",
        "ᴡ": "w",
        "x": "x",
        "ʏ": "y",
        "ᴢ": "z",
    }
)


def normalize_logo_key(name: str) -> str:
    text = str(name or "").strip().lower()
    text = text.translate(SMALLCAPS_MAP)
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^a-z0-9\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_competition_logo_filename(name: str) -> str | None:
    key = normalize_logo_key(name)

    alias_map = {
        "madmen": "madmen.png",
        "madmen invitational": "madmen.png",
        "madmen inhouse cup": "madmen.png",
        "madmen castle bootcamp": "madmen.png",
    }

    if key in alias_map:
        return alias_map[key]

    if "madmen" in key:
        return "madmen.png"

    competition_logo_overrides = {
        "nova": "nova-prime.png",
        "cyberathletes": "cyberathletes.png",
        "diamond": "diamond.png",
    }
    for needle, filename in competition_logo_overrides.items():
        if needle in key:
            return filename

    return None


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
        if image_type == "competition":
            indexed_competitions = sorted((key, value.name) for key, value in entries.items())
            print("[logo_resolver:index] competition_keys=%r" % indexed_competitions)
    return image_index


def _find_image(image_index: dict[str, dict[str, Path]], image_type: str, value: str | None) -> Path | None:
    if not value:
        return None

    normalized_key = normalize_logo_key(value)
    normalized = _normalize_key(normalized_key)
    entries = image_index.get(image_type, {})
    resolved_filename: str | None = None
    resolved_logo: Path | None = None
    resolved_logo_exists = False

    if image_type == "competition":
        resolved_filename = resolve_competition_logo_filename(value)
        if resolved_filename:
            resolved_logo = APP_ROOT / IMAGE_FOLDERS["competition"] / resolved_filename
            resolved_logo_exists = resolved_logo.exists()
            if resolved_logo_exists:
                final_path = resolved_logo
                fallback_found = entries.get(normalized) is not None
                print(
                    "[logo_resolver] raw=%s repr=%r normalized_key=%s resolved_filename=%r resolved_path=%r resolved_exists=%s fallback_key=%s fallback_found=%s final_return=%r"
                    % (
                        str(value),
                        value,
                        normalized_key,
                        resolved_filename,
                        str(resolved_logo),
                        resolved_logo_exists,
                        normalized,
                        fallback_found,
                        str(final_path),
                    )
                )
                return final_path

    fallback_logo = entries.get(normalized)
    if image_type == "competition":
        final_path = fallback_logo
        print(
            "[logo_resolver] raw=%s repr=%r normalized_key=%s resolved_filename=%r resolved_path=%r resolved_exists=%s fallback_key=%s fallback_found=%s final_return=%r"
            % (
                str(value),
                value,
                normalized_key,
                resolved_filename,
                str(resolved_logo) if resolved_logo else None,
                resolved_logo_exists,
                normalized,
                fallback_logo is not None,
                str(final_path) if final_path else None,
            )
        )
    return fallback_logo


def _competition_logo_uri(image_index: dict[str, dict[str, Path]], competition: str | None) -> str:
    competition_logo = _find_image(image_index, "competition", competition)
    fallback_logo = CPL_LOGO if CPL_LOGO.exists() else None
    chosen_logo = competition_logo or fallback_logo
    if chosen_logo is None:
        return ""
    return _image_to_data_uri(chosen_logo)


def normalize_position_label(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip().casefold()


def extract_position_number(value: object) -> int | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().casefold()
    if not text:
        return None
    match = re.search(r"\b(\d+)(?:st|nd|rd|th)?\b", text)
    return int(match.group(1)) if match else None


def _parse_placement_to_int(value: object) -> int | None:
    # Backward-compatible alias for older call sites.
    return extract_position_number(value)


ACHIEVEMENT_REQUIRED_COLUMNS = ["player", "achievement_name", "achievement_link", "achievement_tier", "season_name", "position"]
ACHIEVEMENT_ALLOWED_FILENAMES = {
    "cpl_gold.png",
    "cpl_silver.png",
    "cpl_bronze.png",
    "4-10th_Ladder.png",
    "31-40th_Ladder.png",
    "league-emerald-gold.png",
    "league-emerald-silver.png",
    "cpl_4th-10th.png",
}
ACHIEVEMENT_FILENAME_ALIASES = {"30-40th_ladder.png": "31-40th_Ladder.png"}


def _achievement_asset_path(filename: str | None) -> Path | None:
    if not filename:
        return None
    assets_dirs = (
        APP_ROOT / IMAGE_FOLDERS["achievement"],
        APP_ROOT / "achievement_png",
    )
    alias = ACHIEVEMENT_FILENAME_ALIASES.get(filename.casefold(), filename)
    if alias not in ACHIEVEMENT_ALLOWED_FILENAMES:
        return None
    for assets_dir in assets_dirs:
        direct = assets_dir / alias
        if direct.exists() and direct.is_file():
            return direct
        if alias == "31-40th_Ladder.png":
            legacy = assets_dir / "30-40th_Ladder.png"
            if legacy.exists() and legacy.is_file():
                return legacy
    return None


def _normalize_achievement_text(value: object) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = normalize_logo_key(str(value))
    text = text.replace("world ladder", "ladder").replace("global ladder", "ladder")
    text = re.sub(r"\bseason\s+\d+\b", "", text)
    return re.sub(r"\s+", " ", text).strip()


@st.cache_data(show_spinner=False)
def load_achievements_data(achievements_csv: Path) -> pd.DataFrame:
    achievements = pd.read_csv(achievements_csv, sep="|")
    achievements.columns = achievements.columns.astype(str).str.strip()
    achievements = achievements.apply(lambda s: s.str.strip() if s.dtype == object else s)
    for col in ACHIEVEMENT_REQUIRED_COLUMNS:
        if col not in achievements.columns:
            achievements[col] = ""
    achievements = achievements[ACHIEVEMENT_REQUIRED_COLUMNS].copy()
    achievements["player_core"] = achievements["player"].astype(str).apply(extract_core_player_name)
    achievements["season_label_norm"] = achievements["season_name"].apply(normalize_season_label)
    achievements["season_num"] = achievements["season_name"].apply(extract_season_number)
    achievements["season_num"] = achievements["season_num"].astype("Int64")
    achievements["position_label_norm"] = achievements["position"].apply(normalize_position_label)
    achievements["position_num"] = achievements["position"].apply(extract_position_number).astype("Int64")
    required_output_columns = [
        "player",
        "achievement_name",
        "achievement_link",
        "achievement_tier",
        "season_name",
        "position",
        "player_core",
        "season_label_norm",
        "season_num",
        "position_label_norm",
        "position_num",
    ]
    for col in required_output_columns:
        if col not in achievements.columns:
            achievements[col] = pd.NA
    return achievements[required_output_columns].copy()


def extract_core_player_name(name: str) -> str:
    text = str(name or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = " ".join(text.split())
    if "|" in text:
        text = text.split("|")[-1].strip()
    return text


def normalize_season_label(name: object) -> str:
    if name is None or pd.isna(name):
        return ""
    text = str(name).strip()
    if not text:
        return ""
    text = re.sub(r"\s+", " ", text)
    return text.casefold()


def resolve_achievement_image_details(
    image_index: dict[str, dict[str, Path]],
    achievement_row: pd.Series,
) -> tuple[Path | None, str, str]:
    achievement_name = str(achievement_row.get("achievement_name", "")).strip()
    position_text = str(achievement_row.get("position", "")).strip()
    position_num = _parse_placement_to_int(position_text)
    normalized_name = _normalize_achievement_text(achievement_name)
    link_basename = Path(str(achievement_row.get("achievement_link", "") or "")).name
    normalized_link = ACHIEVEMENT_FILENAME_ALIASES.get(link_basename.casefold(), link_basename)

    if normalized_name == "league emerald":
        filename = "league-emerald-silver.png"
        if position_text.casefold() == "1st":
            filename = "league-emerald-gold.png"
        resolved_path = _achievement_asset_path(filename)
        return resolved_path, filename, "mapped:league_emerald"

    if "cpl ladder season" in achievement_name.casefold():
        filename = None
        if position_num == 1:
            filename = "cpl_gold.png"
        elif position_num == 2:
            filename = "cpl_silver.png"
        elif position_num == 3:
            filename = "cpl_bronze.png"
        elif position_num is not None and 4 <= position_num <= 10:
            filename = "4-10th_Ladder.png"
        elif position_num is not None and 31 <= position_num <= 40:
            filename = "31-40th_Ladder.png"
        resolved_path = _achievement_asset_path(filename)
        return resolved_path, filename or "", "mapped:cpl_ladder"

    if normalized_link:
        resolved_path = _achievement_asset_path(normalized_link)
        if resolved_path:
            return resolved_path, normalized_link, "link_basename"

    for key in (
        achievement_name,
        f"{achievement_name} {achievement_row.get('season_name', '')}",
        f"{achievement_name} {position_text}",
    ):
        found = _find_image(image_index, "achievement", key)
        if found:
            return found, found.name, f"index_lookup:{key}"

    return None, "", "no_image_match"


PLAYER_PHOTO_ALIAS_MAP = {
    "8eer": "ⓜ | 8eeR.png",
}


def _player_name_variants(player_name: str) -> list[str]:
    raw = str(player_name or "").strip()
    if not raw:
        return []
    parts = [raw]
    if "|" in raw:
        parts.extend([chunk.strip() for chunk in raw.split("|") if chunk.strip()])
        parts.append(raw.split("|")[-1].strip())
    normalized_ascii = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode("ascii").strip()
    if normalized_ascii:
        parts.append(normalized_ascii)
    for chunk in list(parts):
        if chunk.startswith("ⓜ"):
            parts.append(chunk.replace("ⓜ", "").strip(" |"))
    dedup: list[str] = []
    for candidate in parts:
        if candidate and candidate not in dedup:
            dedup.append(candidate)
    return dedup


def resolve_player_photo(image_index: dict[str, dict[str, Path]], player_name: str) -> Path | None:
    variants = _player_name_variants(player_name)
    if not variants:
        return None
    player_dir = APP_ROOT / IMAGE_FOLDERS["player"]
    indexed_paths = image_index.get("player", {})
    normalized_keys = [_normalize_key(normalize_logo_key(name)) for name in variants]

    # a) explicit alias map
    for key in normalized_keys:
        alias_name = PLAYER_PHOTO_ALIAS_MAP.get(key)
        if not alias_name:
            continue
        alias_path = player_dir / alias_name
        if alias_path.exists() and alias_path.is_file():
            return alias_path

    # b) exact player-name filename (supports special chars like "ⓜ | 8eeR.png")
    for candidate in variants:
        exact_no_ext = player_dir / candidate
        if exact_no_ext.exists() and exact_no_ext.is_file():
            return exact_no_ext
        if Path(candidate).suffix.lower() in IMAGE_EXTENSIONS:
            exact_with_ext = player_dir / Path(candidate).name
            if exact_with_ext.exists() and exact_with_ext.is_file():
                return exact_with_ext

    # c) cleaned / normalized player-name filename
    for key in normalized_keys:
        hit = indexed_paths.get(key)
        if hit is not None:
            return hit

    # d) common image extensions
    for candidate in variants:
        for ext in sorted(IMAGE_EXTENSIONS):
            exact = player_dir / f"{candidate}{ext}"
            if exact.exists() and exact.is_file():
                return exact
    return None


def _normalize_match_id_column(df: pd.DataFrame) -> pd.DataFrame:
    if "match_id" in df.columns:
        df["match_id"] = df["match_id"].astype(str).str.strip()
    return df


def normalize_competition_name(competition: str | None) -> str | None:
    if competition is None or (isinstance(competition, float) and pd.isna(competition)):
        return competition
    return re.sub(r"\b(S\d+)\.\d+\b", r"\1", str(competition))


AWAY_STATUS_SMALLCAP_MAP = str.maketrans(
    {
        "ᴀ": "a",
        "ʙ": "b",
        "ᴄ": "c",
        "ᴅ": "d",
        "ᴇ": "e",
        "ꜰ": "f",
        "ɢ": "g",
        "ʜ": "h",
        "ɪ": "i",
        "ᴊ": "j",
        "ᴋ": "k",
        "ʟ": "l",
        "ᴍ": "m",
        "ɴ": "n",
        "ᴏ": "o",
        "ᴘ": "p",
        "ǫ": "q",
        "ʀ": "r",
        "ꜱ": "s",
        "ᴛ": "t",
        "ᴜ": "u",
        "ᴠ": "v",
        "ᴡ": "w",
        "x": "x",
        "ʏ": "y",
        "ᴢ": "z",
    }
)


def _normalize_away_status_text(value: str) -> str:
    text = unicodedata.normalize("NFKC", str(value))
    text = html.unescape(text).translate(AWAY_STATUS_SMALLCAP_MAP).casefold()
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = text.replace("’", "'").replace("`", "'")
    return re.sub(r"\s+", " ", text).strip()


def strip_away_status_tokens(name: str) -> tuple[str, bool]:
    """Remove obvious AFK/idle status markers from team names."""
    if name is None or (isinstance(name, float) and pd.isna(name)):
        return "", False
    original = str(name).strip()
    if not original:
        return "", False

    text = _normalize_away_status_text(original)
    before = text
    patterns = [
        r"[\[\(]\s*(?:afk|idle|idling)\s*[\]\)]",
        r"\bis\s+idling\b",
        r"\bidling\b",
        r"\bidle\b",
        r"\bafk\b",
    ]
    for pattern in patterns:
        text = re.sub(pattern, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" -_.,")
    return text, bool(text and text != before)


def normalize_opponent_name(value: str) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = _normalize_away_status_text(str(value))
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = re.sub(r"[._\-]+", " ", text)
    text = re.sub(r"[^\w\s']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def resolve_canonical_opponent_name(
    value: str,
    *,
    known_clean_names: set[str],
    preferred_label_by_key: dict[str, str] | None = None,
) -> dict[str, object]:
    original = "" if value is None or (isinstance(value, float) and pd.isna(value)) else str(value).strip()
    original_key = normalize_opponent_name(original)
    stripped_name, away_applied = strip_away_status_tokens(original)
    cleaned_key = normalize_opponent_name(stripped_name)

    canonical_key = original_key
    canonical_label = original
    canonicalized = False
    if away_applied and cleaned_key and cleaned_key in known_clean_names and cleaned_key != original_key:
        canonical_key = cleaned_key
        canonicalized = True
        if preferred_label_by_key and cleaned_key in preferred_label_by_key:
            canonical_label = preferred_label_by_key[cleaned_key]
        elif stripped_name:
            canonical_label = stripped_name

    return {
        "opponent_original_raw": original,
        "opponent_cleaned_raw": stripped_name,
        "opponent_original_key": original_key,
        "opponent_cleaned_key": cleaned_key,
        "opponent_away_status_applied": away_applied,
        "opponent_canonicalized": canonicalized,
        "opponent_raw": canonical_label,
        "opponent_key": canonical_key,
    }


def resolve_latest_opponent_tier(df: pd.DataFrame) -> pd.DataFrame:
    """Resolve opponent tier from that opponent's most recent game in the current filtered context."""
    if df.empty or "opponent_key" not in df.columns:
        return pd.DataFrame(columns=["opponent_key", "latest_tier"])
    frame = df.copy()
    if "date" in frame.columns:
        frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    else:
        frame["date"] = pd.NaT
    if "match_id" not in frame.columns:
        frame["match_id"] = ""
    if "tier" not in frame.columns:
        frame["tier"] = pd.NA

    frame["tier_clean"] = frame["tier"].apply(
        lambda value: str(value).strip().upper()[:1]
        if value is not None and not (isinstance(value, float) and pd.isna(value)) and str(value).strip()
        else ""
    )
    frame = frame.sort_values(["opponent_key", "date", "match_id"], ascending=[True, False, False])
    latest = frame.groupby("opponent_key", as_index=False).first()
    latest["latest_tier"] = latest["tier_clean"].replace("", pd.NA)
    return latest[["opponent_key", "latest_tier"]]


def normalize_competition_label(value: str) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = unicodedata.normalize("NFKC", str(value))
    text = html.unescape(text).strip().lower()
    text = re.sub(r"\b(s\d+)\.\d+\b", r"\1", text, flags=re.IGNORECASE)
    text = re.sub(r"[\u200b-\u200d\ufeff]", "", text)
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"[^\w\s#']", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract_season_number(name: object) -> int | None:
    if name is None or pd.isna(name):
        return None
    text = str(name).strip()
    if not text:
        return None
    match = re.search(r"(?i)\b(?:season|s)\s*[-_.]?\s*(\d+)\b", text)
    if match:
        return int(match.group(1))
    match = re.fullmatch(r"\s*(\d+)\s*", text)
    if match:
        return int(match.group(1))
    return None


def detect_latest_season(df: pd.DataFrame, competition_col: str = "competition") -> int | None:
    if df.empty or competition_col not in df.columns:
        return None
    seasons = df[competition_col].apply(extract_season_number).dropna()
    if seasons.empty:
        return None
    return int(seasons.max())


def apply_season_filter(df: pd.DataFrame, selected_season: str, competition_col: str = "competition") -> pd.DataFrame:
    if df.empty or competition_col not in df.columns or selected_season == "Lifetime":
        return df.copy()
    season_match = re.match(r"^S(\d+)$", str(selected_season), flags=re.IGNORECASE)
    if season_match is None:
        return df.copy()
    target_season = int(season_match.group(1))
    filtered_df = df.copy()
    filtered_df["_season_number"] = filtered_df[competition_col].apply(extract_season_number)
    filtered_df = filtered_df[filtered_df["_season_number"] == target_season].drop(columns="_season_number")
    return filtered_df


def _format_season_label(season_number: int | None) -> str | None:
    if season_number is None:
        return None
    return f"S{int(season_number)}"


def resolve_row_season(
    row: pd.Series,
    *,
    competition_col: str = "competition",
    normalized_competition_col: str = "grouped_competition",
    season_lookup_by_match_id: dict[str, str] | None = None,
    season_lookup_by_date: dict[pd.Timestamp, str] | None = None,
    season_date_windows: list[tuple[str, pd.Timestamp, pd.Timestamp | None]] | None = None,
) -> str | None:
    explicit_season_columns = (
        "season",
        "season_code",
        "season_label",
        "match_season",
        "competition_season",
        "event_season",
        "split",
    )
    for col in explicit_season_columns:
        if col not in row.index:
            continue
        season_number = extract_season_number(row.get(col))
        if season_number is not None:
            return _format_season_label(season_number)

    if season_lookup_by_match_id and "match_id" in row.index:
        match_id = str(row.get("match_id", "")).strip()
        if match_id and match_id in season_lookup_by_match_id:
            return season_lookup_by_match_id[match_id]

    if normalized_competition_col in row.index:
        season_number = extract_season_number(row.get(normalized_competition_col))
        if season_number is not None:
            return _format_season_label(season_number)

    season_number = extract_season_number(row.get(competition_col))
    if season_number is not None:
        return _format_season_label(season_number)

    for fallback_col in ("competition_raw", "raw_competition", "competition_name"):
        if fallback_col not in row.index:
            continue
        season_number = extract_season_number(row.get(fallback_col))
        if season_number is not None:
            return _format_season_label(season_number)

    if season_lookup_by_date and "date" in row.index:
        date_value = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.notna(date_value):
            date_key = pd.Timestamp(date_value).normalize()
            if date_key in season_lookup_by_date:
                return season_lookup_by_date[date_key]

    if season_date_windows and "date" in row.index:
        date_value = pd.to_datetime(row.get("date"), errors="coerce")
        if pd.notna(date_value):
            date_key = pd.Timestamp(date_value).normalize()
            for season_label, start_date, end_date in season_date_windows:
                if date_key < start_date:
                    continue
                if end_date is None or date_key < end_date:
                    return season_label

    return None


def build_season_date_windows(df: pd.DataFrame) -> list[tuple[str, pd.Timestamp, pd.Timestamp | None]]:
    if df.empty or "date" not in df.columns:
        return []
    anchor = df.copy()
    anchor["date_key"] = pd.to_datetime(anchor["date"], errors="coerce").dt.normalize()
    if "season_num_resolved" in anchor.columns:
        anchor["anchor_season_num"] = pd.to_numeric(anchor["season_num_resolved"], errors="coerce")
    else:
        anchor["anchor_season_num"] = pd.NA
    if "competition_raw" in anchor.columns:
        parsed_from_comp = anchor["competition_raw"].apply(extract_season_number)
        anchor.loc[anchor["anchor_season_num"].isna(), "anchor_season_num"] = parsed_from_comp
    anchor = anchor.dropna(subset=["anchor_season_num", "date_key"]).copy()
    if anchor.empty:
        return []
    season_starts = (
        anchor.groupby("anchor_season_num", as_index=False)["date_key"]
        .min()
        .sort_values("date_key")
        .reset_index(drop=True)
    )
    windows: list[tuple[str, pd.Timestamp, pd.Timestamp | None]] = []
    for idx, row in season_starts.iterrows():
        season_label = f"S{int(row['anchor_season_num'])}"
        start_date = pd.Timestamp(row["date_key"]).normalize()
        end_date = None
        if idx < len(season_starts) - 1:
            end_date = pd.Timestamp(season_starts.iloc[idx + 1]["date_key"]).normalize()
        windows.append((season_label, start_date, end_date))
    return windows


def _preferred_label(series: pd.Series, fallback: str = "Unknown") -> str:
    clean = series.dropna().astype(str).str.strip()
    clean = clean[clean != ""]
    if clean.empty:
        return fallback
    mode = clean.mode()
    return str(mode.iloc[0]) if not mode.empty else str(clean.iloc[0])


def build_medisports_vs_base_df(tactics_df: pd.DataFrame, competition_source_col: str) -> pd.DataFrame:
    base = _build_match_level_results(tactics_df, competition_source_col)
    if base.empty:
        return base
    base_df = base.copy()
    base_df["competition_raw"] = base_df["competition"].apply(
        lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
    )
    base_df["competition_grouped"] = base_df["competition_raw"].apply(normalize_competition_name)
    base_df["competition_key"] = base_df["competition_grouped"].apply(normalize_competition_label)
    base_df["opponent_original_raw"] = base_df["opponent_team"].apply(
        lambda v: "" if v is None or (isinstance(v, float) and pd.isna(v)) else str(v).strip()
    )
    base_df["opponent_original_key"] = base_df["opponent_original_raw"].apply(normalize_opponent_name)
    away_strip = base_df["opponent_original_raw"].apply(strip_away_status_tokens)
    base_df["opponent_cleaned_raw"] = away_strip.apply(lambda item: item[0])
    base_df["opponent_away_status_applied"] = away_strip.apply(lambda item: bool(item[1]))
    base_df["opponent_cleaned_key"] = base_df["opponent_cleaned_raw"].apply(normalize_opponent_name)
    clean_source = base_df[~base_df["opponent_away_status_applied"] & (base_df["opponent_original_key"] != "")]
    preferred_label_by_key = (
        clean_source.groupby("opponent_original_key")["opponent_original_raw"]
        .agg(lambda s: _preferred_label(s, fallback=""))
        .to_dict()
    )
    known_clean_names = set(preferred_label_by_key.keys())
    canonical_rows = base_df["opponent_original_raw"].apply(
        lambda value: resolve_canonical_opponent_name(
            value,
            known_clean_names=known_clean_names,
            preferred_label_by_key=preferred_label_by_key,
        )
    )
    canonical_df = pd.DataFrame(canonical_rows.tolist(), index=base_df.index)
    for col in canonical_df.columns:
        base_df[col] = canonical_df[col]
    base_df["opponent_raw"] = base_df["opponent_raw"].astype(str).str.strip()
    base_df["opponent_key"] = base_df["opponent_key"].astype(str).str.strip()
    base_df["season_resolved"] = pd.NA
    base_df["season_num_resolved"] = pd.NA

    explicit_season_cols = [
        col for col in ("season", "season_code", "season_label", "match_season", "competition_season", "event_season", "split")
        if col in base_df.columns
    ]
    seed = base_df.copy()
    if explicit_season_cols:
        seed["_explicit_season"] = seed[explicit_season_cols].bfill(axis=1).iloc[:, 0]
    else:
        seed["_explicit_season"] = pd.NA
    seed["_seed_season_num"] = seed["_explicit_season"].apply(extract_season_number)
    seed.loc[seed["_seed_season_num"].isna(), "_seed_season_num"] = seed["competition_grouped"].apply(extract_season_number)
    seed = seed.dropna(subset=["_seed_season_num"]).copy()
    seed["_seed_season"] = seed["_seed_season_num"].astype(int).apply(lambda n: f"S{n}")

    season_lookup_by_match_id = (
        seed.dropna(subset=["match_id"])
        .assign(match_id=lambda d: d["match_id"].astype(str).str.strip())
        .drop_duplicates(subset=["match_id"])
        .set_index("match_id")["_seed_season"]
        .astype(str)
        .to_dict()
    )
    season_lookup_by_date = (
        seed.dropna(subset=["date"])
        .assign(_date_key=lambda d: pd.to_datetime(d["date"], errors="coerce").dt.normalize())
        .dropna(subset=["_date_key"])
        .groupby("_date_key")["_seed_season"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
        .to_dict()
    )

    base_df["season_resolved"] = base_df.apply(
        lambda row: resolve_row_season(
            row,
            competition_col="competition_raw",
            normalized_competition_col="competition_grouped",
            season_lookup_by_match_id=season_lookup_by_match_id,
            season_lookup_by_date=season_lookup_by_date,
            season_date_windows=None,
        ),
        axis=1,
    )
    base_df["season_num_resolved"] = base_df["season_resolved"].apply(extract_season_number).astype("Int64")
    season_windows = build_season_date_windows(base_df)
    unresolved_mask = base_df["season_resolved"].isna()
    if unresolved_mask.any() and season_windows:
        base_df.loc[unresolved_mask, "season_resolved"] = base_df.loc[unresolved_mask].apply(
            lambda row: resolve_row_season(
                row,
                competition_col="competition_raw",
                normalized_competition_col="competition_grouped",
                season_lookup_by_match_id=season_lookup_by_match_id,
                season_lookup_by_date=season_lookup_by_date,
                season_date_windows=season_windows,
            ),
            axis=1,
        )
    base_df["season_num_resolved"] = base_df["season_resolved"].apply(extract_season_number).astype("Int64")
    return base_df


def _sanitize_competition_value(value: object) -> object:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return value

    text = str(value).strip()
    if not text:
        return text

    # Normalize common escaped payload variants first.
    text = html.unescape(text)
    text = text.replace('\\"', '"').replace("\\'", "'")

    if "<" in text and ">" in text:
        rank_names = re.findall(r'class=["\']rank-name["\']>([^<]+)<', text, flags=re.IGNORECASE)
        if rank_names:
            text = rank_names[0].strip()
        else:
            text = re.sub(r"data:image/[^\"']+", "", text, flags=re.IGNORECASE)
            text = re.sub(r"<[^>]+>", " ", text)
            text = " ".join(html.unescape(text).split())

    return text


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

    achievements = load_achievements_data(ACHIEVEMENTS_CSV)

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
    if "competition" in players.columns:
        players["competition"] = players["competition"].apply(_sanitize_competition_value)
    if "competition" in tactics.columns:
        tactics["competition"] = tactics["competition"].apply(_sanitize_competition_value)
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


@st.cache_data(show_spinner=False)
def _load_play_csv_profiles() -> pd.DataFrame:
    """Load profile identity rows from play.csv (or case variants) as source-of-truth."""
    play_path = next(
        (path for path in (DATA_DIR / "play.csv", DATA_DIR / "Play.csv", DATA_DIR / "players.csv", DATA_DIR / "Player.csv") if path.exists()),
        None,
    )
    if play_path is None:
        return pd.DataFrame()

    def _from_structured_csv(path: Path) -> pd.DataFrame:
        try:
            parsed = pd.read_csv(path, sep=None, engine="python", on_bad_lines="skip")
        except Exception:
            return pd.DataFrame()
        if parsed.empty or len(parsed.columns) <= 1:
            return pd.DataFrame()
        parsed.columns = parsed.columns.astype(str).str.strip()
        parsed = parsed.apply(lambda col: col.str.strip() if col.dtype == object else col)
        aliases = {"name": "player", "country": "nation", "nationality": "nation"}
        parsed = parsed.rename(columns={col: aliases.get(col.strip().casefold(), col) for col in parsed.columns})
        player_col = next((col for col in parsed.columns if col.strip().casefold() == "player"), None)
        if player_col is None:
            return pd.DataFrame()
        parsed = parsed.rename(columns={player_col: "player"})
        return parsed

    profiles = _from_structured_csv(play_path)
    if profiles.empty:
        raw_lines = [line.strip() for line in play_path.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
        if len(raw_lines) <= 1:
            return pd.DataFrame()
        role_tokens = ("igl", "entry", "lurker", "awp", "support", "coach", "flex", "rifler")
        country_tokens = sorted(COUNTRY_TO_ALPHA2.keys(), key=len, reverse=True)
        parsed_rows: list[dict[str, str]] = []
        for raw in raw_lines[1:]:
            compact = raw.strip()
            compact = re.sub(r"^\d+", "", compact).strip()
            compact = re.sub(r"\d+$", "", compact).strip()
            role_match = next((role for role in role_tokens if compact.casefold().endswith(role)), "")
            role = role_match.upper() if role_match else ""
            if role_match:
                compact = compact[: -len(role_match)].strip()
            country_match = next((country for country in country_tokens if compact.casefold().endswith(country)), "")
            nation = country_match.title() if country_match else ""
            if country_match:
                player = compact[: -len(country_match)].strip()
            else:
                player = compact.strip()
            if player:
                parsed_rows.append({"player": player, "nation": nation, "role": role})
        profiles = pd.DataFrame(parsed_rows)

    if profiles.empty:
        return profiles
    if "team" not in profiles.columns:
        profiles["team"] = "ᴍᴇᴅɪꜱᴘᴏʀᴛꜱ ⓜ"
    profiles["player_lookup"] = profiles["player"].astype(str).str.strip().str.casefold()
    profiles = profiles.drop_duplicates(subset=["player_lookup"], keep="first")
    return profiles


def get_player_profile_from_play_csv(selected_player: str) -> dict[str, str]:
    """Resolve player profile identity from play.csv before any match-row fallback."""
    profiles = _load_play_csv_profiles()
    default_profile = {
        "player": str(selected_player).strip() or "-",
        "team": "ᴍᴇᴅɪꜱᴘᴏʀᴛꜱ ⓜ",
        "role": "Fragger",
        "nation": "",
    }
    if profiles.empty or "player_lookup" not in profiles.columns:
        return default_profile

    lookup = str(selected_player).strip().casefold()
    row = profiles[profiles["player_lookup"] == lookup]
    if row.empty:
        return default_profile
    row_data = row.iloc[0]
    profile = default_profile.copy()
    for key in ("player", "team", "role", "nation"):
        value = str(row_data.get(key, "")).strip()
        if value:
            profile[key] = value
    return profile


def _resolve_country_alpha2(value: str | None) -> str:
    nation = str(value or "").strip()
    if not nation:
        return ""

    normalized = unicodedata.normalize("NFKD", nation)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    normalized = re.sub(r"[^A-Za-z ]+", " ", normalized).strip().casefold()
    normalized = re.sub(r"\s+", " ", normalized)

    if len(nation) == 2 and nation.isalpha():
        return nation.upper()
    if len(normalized) == 2 and normalized.isalpha():
        return normalized.upper()
    return COUNTRY_TO_ALPHA2.get(normalized, "")


def _nation_flag_emoji(value: str | None, fallback: str = "🌍") -> str:
    alpha2 = _resolve_country_alpha2(value)
    if len(alpha2) != 2 or not alpha2.isalpha():
        return fallback
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


def extract_route_tags(tactic_name: str) -> set[str]:
    text = str(tactic_name or "").lower()
    tag_map = {
        "mid": [" mid", "middle", "connector", "con "],
        "ivy": ["ivy"],
        "a": [" a ", " a-", " a>", " main", " halls"],
        "b": [" b ", " b-", " b>", " apps", " ap ", " aps"],
        "fast": ["fast", "rush", "explode"],
        "slow": ["default", "wait", "hold", "lurk", "slow"],
    }
    found: set[str] = set()
    text_padded = f" {text} "
    for tag, needles in tag_map.items():
        if any(needle in text_padded for needle in needles):
            found.add(tag)
    return found


def classify_recommendation_bucket(tactic_name: str) -> str:
    name = str(tactic_name or "")
    upper = name.upper()
    tags = re.findall(r"[\(\[\{<]([^)\]}>]+)[\)\]\}>]", upper)
    flat_tags = "".join(tags)
    routes = extract_route_tags(name)

    if "MID" in upper or "mid" in routes:
        return "Mid"
    if "IVY" in upper or "ivy" in routes:
        return "Ivy"

    prefix = re.sub(r"^\s*(?:[\(\[\{<][^)\]}>]+[\)\]\}>]\s*)+", "", upper).strip()
    prefix_letter = prefix[:1]

    is_pistol = "P" in flat_tags or prefix_letter == "P"
    is_eco = "E" in flat_tags or prefix_letter == "E"

    has_a = bool(re.search(r"(?:^|\W)A(?:$|\W)", upper))
    has_b = bool(re.search(r"(?:^|\W)B(?:$|\W)", upper))
    has_ab = "A/B" in upper or ("a" in routes and "b" in routes)

    if is_pistol:
        return "Pistol"
    if is_eco:
        return "Eco"
    return "Standard"


def compute_category_relative_score(row: pd.Series, category_baselines: dict[str, dict[str, float]]) -> float:
    bucket = str(row.get("bucket", "Standard"))
    base = category_baselines.get(bucket, {})
    baseline_wr = float(base.get("baseline_win_pct", float(row.get("context_baseline_win_pct", 50.0))))
    baseline_uses = float(base.get("avg_uses", float(row.get("times_used", 1.0))))
    baseline_delta = float(base.get("avg_delta", 0.0))

    wr_edge = float(row.get("win_pct", 0.0)) - baseline_wr
    use_ratio = float(row.get("times_used", 0.0)) / max(baseline_uses, 1.0)
    delta_edge = float(row.get("delta_vs_baseline", 0.0)) - baseline_delta

    score = 50.0
    score += max(min(wr_edge * 1.8, 18), -18)
    score += max(min(delta_edge * 1.2, 12), -12)
    score += max(min((use_ratio - 1.0) * 10, 8), -6)
    return round(score, 1)


def compute_tier_strength_weight(tier: str | None) -> float:
    tier_key = str(tier or "").strip().upper()
    return {"S": 2.7, "A": 1.6, "B": 1.08, "C": 0.9}.get(tier_key, 1.0)


def _compute_tier_expected_win_pct(tier: str | None) -> float:
    tier_key = str(tier or "").strip().upper()
    return {"S": 42.0, "A": 48.0, "B": 52.0, "C": 56.0}.get(tier_key, 50.0)


def _compute_tier_negative_penalty_scale(tier: str | None) -> float:
    tier_key = str(tier or "").strip().upper()
    return {"S": 0.52, "A": 0.8, "B": 1.0, "C": 1.2}.get(tier_key, 1.0)


def compute_tier_adjusted_tactic_score(
    *,
    tier: str | None,
    win_pct: float,
    wins: float,
    losses: float,
) -> float:
    expected_win_pct = _compute_tier_expected_win_pct(tier)
    delta_vs_expected = float(win_pct) - expected_win_pct
    strength_weight = compute_tier_strength_weight(tier)
    neg_scale = _compute_tier_negative_penalty_scale(tier)
    signed_delta_weight = strength_weight if delta_vs_expected >= 0 else strength_weight * neg_scale
    uses = max(float(wins) + float(losses), 1.0)
    round_diff_per_100 = ((float(wins) - float(losses)) / uses) * 100.0
    evidence_factor = np.sqrt(uses) / (np.sqrt(uses) + 2.4)
    adjusted = 50.0 + ((delta_vs_expected * signed_delta_weight * 0.48) + (round_diff_per_100 * signed_delta_weight * 0.12)) * evidence_factor
    return round(_clamp(adjusted, 5.0, 95.0), 2)


def compute_quality_of_results_component(
    tier_rows: pd.DataFrame,
    *,
    total_uses: float,
) -> tuple[float, str]:
    if tier_rows.empty:
        return 0.0, ""

    total_uses = max(float(total_uses), 1.0)
    component = 0.0
    elite_positive = 0.0
    elite_resilience = 0.0
    c_positive = 0.0
    c_negative = 0.0
    c_share = 0.0
    elite_share = 0.0
    for row in tier_rows.itertuples(index=False):
        tier = str(getattr(row, "tier", "")).upper().strip()
        if tier not in {"S", "A", "B", "C"}:
            continue
        wins = float(getattr(row, "wins", 0.0))
        losses = float(getattr(row, "losses", 0.0))
        uses = max(wins + losses, 1.0)
        share = uses / total_uses
        adjusted_score = compute_tier_adjusted_tactic_score(
            tier=tier,
            win_pct=(wins / uses) * 100.0,
            wins=wins,
            losses=losses,
        )
        centered = adjusted_score - 50.0
        tier_strength = compute_tier_strength_weight(tier)
        evidence = np.sqrt(uses) / (np.sqrt(uses) + 2.0)
        component += centered * share * evidence * (0.75 + (tier_strength - 1.0) * 0.25)
        if tier == "S":
            elite_share += share
            elite_positive += max(centered, 0.0) * evidence
            elite_resilience += min(centered, 0.0) * evidence
        if tier == "C":
            c_share += share
            c_positive += max(centered, 0.0) * evidence
            c_negative += abs(min(centered, 0.0)) * evidence

    sample_stabilizer = np.sqrt(total_uses) / (np.sqrt(total_uses) + 3.5)
    component *= sample_stabilizer
    component = _clamp(component, -14.0, 22.0)

    note = ""
    if elite_positive >= 3.4 and elite_share >= 0.24:
        note = "Boosted by strong returns against S-tier opposition."
    elif elite_positive >= 1.4 and elite_share >= 0.2:
        note = "Trusted more because results held up against elite teams."
    elif elite_resilience <= -1.35 and elite_share >= 0.25 and component >= -1.5:
        note = "Profile remains respectable despite tough S-tier opposition."
    elif c_positive >= 2.4 and c_share >= 0.52 and elite_positive < 1.1:
        note = "Slightly discounted because most success came against volatile C-tier opposition."
    elif c_negative >= 1.9 and c_share >= 0.35:
        note = "Results are less convincing because C-tier matches underperformed."
    return round(component, 2), note


def build_recommendation_reason(row: pd.Series, *, include_base: bool = True) -> str:
    priority_label = str(row.get("keep_priority_label", "Useful keep")).lower()
    reason_parts: list[str] = []
    if include_base:
        reason_parts.append(
            f"Selected because it rates as {priority_label} in this exact map + side pool, with score-led value and stable context fit."
        )
    tier_reason = str(row.get("tier_weighting_note", "")).strip()
    if tier_reason:
        reason_parts.append(tier_reason)
    eco_fallback_note = str(row.get("eco_fallback_note", "")).strip()
    if eco_fallback_note:
        reason_parts.append(eco_fallback_note)
    return " ".join(reason_parts).strip()


def build_set_explanation(selected_df: pd.DataFrame) -> tuple[str, str] | None:
    if selected_df.empty or "tier_weighting_note" not in selected_df.columns:
        return None
    notes = selected_df["tier_weighting_note"].astype(str).str.strip()
    if notes.empty:
        return None
    elite_count = int(notes.str.contains("S-tier|elite|tough S-tier", case=False, na=False).sum())
    c_discount_count = int(notes.str.contains("C-tier|volatile C-tier", case=False, na=False).sum())
    if elite_count >= 2:
        return ("This set is trusted partly because several tactics held up against elite opposition.", "good")
    if c_discount_count >= 2:
        return ("Some recommendations are slightly de-risked because evidence is concentrated in C-tier matchups.", "warn")
    return None


def compute_tactical_recommendation_score(
    row: pd.Series,
    *,
    prefer_coverage: bool,
    prefer_proven: bool,
) -> float:
    score = 50.0
    score += (float(row.get("category_relative_score", 50.0)) - 50.0) * 1.05
    score += float(row.get("delta_vs_baseline", 0.0)) * 0.8
    score += max(min((float(row.get("times_used", 0.0)) - 3) * 1.2, 24), -6)
    score += (float(row.get("last_10_usage_win_pct", row.get("win_pct", 0.0))) - 50) * 0.25
    score += max(min((float(row.get("trend_delta", 0.0))) * 0.45, 8), -8)
    score += max(min((float(row.get("usage_pct", 0.0)) - float(row.get("context_usage_avg", 0.0))) * -0.25, 4), -5)
    bucket = str(row.get("bucket", "Standard"))
    category_delta = float(row.get("delta_vs_category_baseline", 0.0))
    if bucket == "Eco":
        score += max(min(category_delta * 1.8, 12), -8)
    elif bucket == "Pistol":
        score += max(min(category_delta * 1.4, 10), -8)
    else:
        score += max(min(category_delta * 1.6, 12), -9)

    confidence = str(row.get("confidence", "Neutral / unproven"))
    confidence_bonus = {
        "Proven good": 10,
        "Early positive signal": 5,
        "Neutral / unproven": 0,
        "Early negative signal": -6,
        "Proven poor": -12,
    }
    score += confidence_bonus.get(confidence, 0)

    if str(row.get("recommended_action", "")) == "Use More":
        score += 5
    if str(row.get("recommended_action", "")) == "Drop":
        score -= 10

    route_tags = row.get("route_tags", set())
    if prefer_coverage and isinstance(route_tags, set):
        score += min(len(route_tags), 3) * 1.4
    if prefer_proven:
        score += min(float(row.get("times_used", 0.0)) / 2.8, 8)
    action = str(row.get("recommended_action", "Keep"))
    if action == "Rework":
        score -= 5
    score += float(row.get("route_bonus", 0.0))
    score += float(row.get("quality_of_results_component", 0.0))
    score += float(row.get("tier_adjusted_score_component", 0.0))
    return round(score, 1)


def build_recent_tactic_window(
    context_df: pd.DataFrame,
    *,
    lookback_days: int = 5,
) -> tuple[pd.DataFrame, pd.Timestamp | None, pd.Timestamp | None]:
    if context_df.empty or "date" not in context_df.columns:
        return pd.DataFrame(), None, None
    dated = context_df[context_df["date"].notna()].copy()
    if dated.empty:
        return pd.DataFrame(), None, None
    latest_date = pd.to_datetime(dated["date"], errors="coerce").max()
    if pd.isna(latest_date):
        return pd.DataFrame(), None, None
    window_start = latest_date - pd.Timedelta(days=max(int(lookback_days) - 1, 0))
    window_df = dated[pd.to_datetime(dated["date"], errors="coerce") >= window_start].copy()
    return window_df, pd.Timestamp(window_start), pd.Timestamp(latest_date)


def classify_recent_tactic_status(
    *,
    tactic_name: str,
    window_df: pd.DataFrame,
    full_context_df: pd.DataFrame,
) -> str:
    recent_rows = window_df[window_df["tactic_name"] == tactic_name].copy()
    if recent_rows.empty:
        return "Recently active"
    historic = full_context_df[full_context_df["tactic_name"] == tactic_name].copy()
    first_recent = pd.to_datetime(recent_rows["date"], errors="coerce").min()
    uses_window = int(recent_rows["wins"].fillna(0).sum() + recent_rows["losses"].fillna(0).sum())
    uses_before = 0
    if not historic.empty and pd.notna(first_recent):
        historic_dates = pd.to_datetime(historic["date"], errors="coerce")
        prior_rows = historic[historic_dates < first_recent]
        uses_before = int(prior_rows["wins"].fillna(0).sum() + prior_rows["losses"].fillna(0).sum())
    gap_days = 0
    if uses_before > 0 and pd.notna(first_recent):
        prior_dates = pd.to_datetime(historic["date"], errors="coerce")
        prior_max = prior_dates[prior_dates < first_recent].max()
        if pd.notna(prior_max):
            gap_days = int((first_recent - prior_max).days)
    if uses_before == 0:
        return "New"
    if uses_window >= 10:
        return "Heavily tested"
    if gap_days >= 14:
        return "Reintroduced"
    return "Recently active"


def compute_recent_signal_label(uses: int, delta_vs_baseline: float) -> str:
    if uses <= 2:
        return "Very early signal"
    if uses <= 4:
        return "Low sample"
    if delta_vs_baseline >= 5:
        return "Encouraging early return"
    if delta_vs_baseline <= -5:
        return "Recently underperforming"
    return "Needs more testing"


def build_recent_tactic_note(row: pd.Series) -> str:
    status = str(row.get("recent_status", "Recently active"))
    uses = int(row.get("uses_last_5d", 0))
    delta = float(row.get("delta_vs_baseline_recent", 0.0))
    trend = float(row.get("trend_delta_recent", 0.0))
    if status == "New":
        return "Newly introduced in this map-side pool. Keep testing before locking it in."
    if status == "Reintroduced":
        return "Recently revived after a break; watch whether this return holds."
    if status == "Heavily tested" and delta < 0:
        return "Heavily tested lately but value is slipping; likely needs rework or dropping."
    if status == "Heavily tested" and delta >= 0:
        return "Heavily tested and still positive; looks worth keeping in active prep."
    if uses <= 4:
        return "Too early to trust fully; add reps before making a hard keep/drop call."
    if trend >= 5:
        return "Recent trend is improving; encouraging short-term return."
    if trend <= -5:
        return "Recent dip detected; monitor closely before committing."
    return "Recently active with mixed signal; keep under review."


def classify_keep_priority(score: float) -> tuple[str, str]:
    score_value = float(score)
    if score_value >= 80:
        return "Core pick", "core"
    if score_value >= 70:
        return "Strong keep", "strong"
    if score_value >= 60:
        return "Useful keep", "useful"
    if score_value >= 50:
        return "Situational", "situational"
    return "Tentative", "tentative"


def keep_priority_color_token(priority_tier: str) -> dict[str, str]:
    tokens = {
        "core": {"accent": "#1fd27d", "bg": "rgba(34, 182, 118, 0.14)", "text": "#d8ffe9"},
        "strong": {"accent": "#1fbca4", "bg": "rgba(42, 181, 170, 0.14)", "text": "#d8fffb"},
        "useful": {"accent": "#4e97ff", "bg": "rgba(83, 150, 255, 0.14)", "text": "#dce9ff"},
        "situational": {"accent": "#e4b44d", "bg": "rgba(232, 177, 74, 0.14)", "text": "#ffefd2"},
        "tentative": {"accent": "#ef6d4e", "bg": "rgba(239, 109, 78, 0.14)", "text": "#ffe0d7"},
    }
    return tokens.get(priority_tier, tokens["useful"])


def compute_tactic_vs_tier_summary(
    context_df: pd.DataFrame,
    *,
    min_tier_sample: int = 2,
) -> pd.DataFrame:
    if context_df.empty or "tier" not in context_df.columns:
        return pd.DataFrame(columns=["tactic_name", "map", "side", "vs_s_text", "vs_a_text", "vs_b_text", "vs_c_text"])

    tier_perf = (
        context_df.groupby(["tactic_name", "map", "side", "tier"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            tier_uses=lambda d: d["wins"] + d["losses"],
            tier_win_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
        )
    )
    if tier_perf.empty:
        return pd.DataFrame(columns=["tactic_name", "map", "side", "vs_s_text", "vs_a_text", "vs_b_text", "vs_c_text"])

    tier_perf["tier"] = tier_perf["tier"].astype(str).str.upper().str.strip()
    tier_perf = tier_perf[tier_perf["tier"].isin(["S", "A", "B", "C"])].copy()
    if tier_perf.empty:
        return pd.DataFrame(columns=["tactic_name", "map", "side", "vs_s_text", "vs_a_text", "vs_b_text", "vs_c_text"])

    tiers = ["S", "A", "B", "C"]
    records: list[dict[str, str]] = []
    for (tactic_name, map_name, side_name), group in tier_perf.groupby(["tactic_name", "map", "side"], as_index=False):
        row = {"tactic_name": tactic_name, "map": map_name, "side": side_name}
        tier_lookup = {str(r["tier"]): r for _, r in group.iterrows()}
        for tier in tiers:
            tier_row = tier_lookup.get(tier)
            if tier_row is None or int(tier_row["tier_uses"]) < min_tier_sample:
                row[f"vs_{tier.lower()}_text"] = "n/a"
            else:
                row[f"vs_{tier.lower()}_text"] = f"{float(tier_row['tier_win_pct']):.1f}%"
        records.append(row)
    return pd.DataFrame(records)


def _tactic_overlap_key(tactic_name: str) -> str:
    stripped = re.sub(r"\([^)]*\)", " ", str(tactic_name or "").lower())
    stripped = re.sub(r"[^a-z0-9\s]+", " ", stripped)
    tokens = [tok for tok in stripped.split() if tok not in {"a", "b", "mid", "ivy", "eco", "standard", "pistol"}]
    return " ".join(tokens[:5]).strip()


def _tactics_are_near_duplicate(
    tactic_a: str,
    tactic_b: str,
    tags_a: set[str] | None = None,
    tags_b: set[str] | None = None,
) -> bool:
    if not tactic_a or not tactic_b:
        return False
    key_a = _tactic_overlap_key(tactic_a)
    key_b = _tactic_overlap_key(tactic_b)
    if not key_a or not key_b:
        return False
    token_a = set(key_a.split())
    token_b = set(key_b.split())
    if not token_a or not token_b:
        return False
    jaccard = len(token_a & token_b) / len(token_a | token_b)
    tags_a = tags_a or set()
    tags_b = tags_b or set()
    same_tempo = ("fast" in tags_a and "fast" in tags_b) or ("slow" in tags_a and "slow" in tags_b)
    same_routes = ({k for k in tags_a if k in {"a", "b", "mid", "ivy"}} == {k for k in tags_b if k in {"a", "b", "mid", "ivy"}})
    return jaccard >= 0.72 and same_tempo and same_routes


def _match_record_from_tactics(filtered_tactics: pd.DataFrame) -> dict[str, float]:
    if filtered_tactics.empty or "match_id" not in filtered_tactics.columns:
        return {"matches": 0.0, "wins": 0.0, "losses": 0.0, "draws": 0.0}
    per_match = (
        filtered_tactics.groupby("match_id", as_index=False)[["wins", "losses"]]
        .sum()
        .rename(columns={"wins": "team_score", "losses": "opp_score"})
    )
    if per_match.empty:
        return {"matches": 0.0, "wins": 0.0, "losses": 0.0, "draws": 0.0}
    wins = float((per_match["team_score"] > per_match["opp_score"]).sum())
    losses = float((per_match["team_score"] < per_match["opp_score"]).sum())
    draws = float((per_match["team_score"] == per_match["opp_score"]).sum())
    return {"matches": float(len(per_match)), "wins": wins, "losses": losses, "draws": draws}


def _clamp(value: float, lower: float, upper: float) -> float:
    return float(max(lower, min(value, upper)))


def _safe_ratio(value: float, baseline: float, *, min_baseline: float = 1e-6) -> float:
    if baseline is None or pd.isna(baseline):
        baseline = min_baseline
    return float(value / max(float(baseline), min_baseline))


def _ratio_to_index(ratio: float, *, center: float = 50.0, swing: float = 40.0, cap_low: float = 0.7, cap_high: float = 1.3) -> float:
    bounded = _clamp(ratio, cap_low, cap_high)
    normalized = (bounded - 1.0) / (cap_high - 1.0)
    return _clamp(center + normalized * swing, 0.0, 100.0)


def _build_metric_baseline(pool_rows: pd.DataFrame) -> dict[str, float]:
    if pool_rows.empty:
        return {
            "kd": 1.0,
            "kpr": 0.65,
            "dpr": 135.0,
            "acc": 55.0,
            "hs": 32.0,
            "mvp_per_match": 0.7,
            "death_rate": 0.65,
            "consistency": 0.65,
            "kpd": 1.0,
            "kills_per_match": 18.0,
            "impact": 50.0,
            "form": 58.0,
            "grevscore": 1.0,
        }

    rounds = pool_rows["rounds_played"].replace(0, pd.NA)
    death_rate = float((pool_rows["deaths"] / rounds).dropna().mean()) if "deaths" in pool_rows.columns else 0.65
    mvp_by_match = (
        pool_rows.groupby("match_id", as_index=False)["mvps"].sum()["mvps"].mean()
        if {"match_id", "mvps"}.issubset(pool_rows.columns)
        else 0.7
    )
    consistency = 0.65
    if "kpd" in pool_rows.columns and len(pool_rows) > 1:
        consistency = _clamp(1.0 - (float(pool_rows["kpd"].std(ddof=0)) / 1.2), 0.15, 1.0)
    match_count = max(pool_rows["match_id"].nunique(), 1) if "match_id" in pool_rows.columns else 1
    return {
        "kd": float((pool_rows["kills"].sum() / max(pool_rows["deaths"].sum(), 1.0))) if {"kills", "deaths"}.issubset(pool_rows.columns) else 1.0,
        "kpr": float((pool_rows["kills"].sum() / max(pool_rows["rounds_played"].sum(), 1.0))) if {"kills", "rounds_played"}.issubset(pool_rows.columns) else 0.65,
        "dpr": float((pool_rows["damage"].sum() / max(pool_rows["rounds_played"].sum(), 1.0))) if {"damage", "rounds_played"}.issubset(pool_rows.columns) else 135.0,
        "acc": float(pool_rows["accuracy_pct"].mean()) if "accuracy_pct" in pool_rows.columns else 55.0,
        "hs": float(pool_rows["hs_pct"].mean()) if "hs_pct" in pool_rows.columns else 32.0,
        "mvp_per_match": float(mvp_by_match),
        "death_rate": float(death_rate) if death_rate == death_rate else 0.65,
        "consistency": float(consistency),
        "kpd": float(pool_rows["kpd"].mean()) if "kpd" in pool_rows.columns else 1.0,
        "kills_per_match": float(pool_rows["kills"].sum() / max(match_count, 1)) if "kills" in pool_rows.columns else 18.0,
        "impact": 50.0,
        "form": 58.0,
        "grevscore": 1.0,
    }


def compute_impact_components(player_stats: dict[str, float], baseline: dict[str, float]) -> dict[str, float]:
    kill_pressure_ratio = _safe_ratio(player_stats["kpr"], baseline["kpr"])
    damage_pressure_ratio = _safe_ratio(player_stats["dpr"], baseline["dpr"])
    efficiency_ratio = _safe_ratio(player_stats["kd"], baseline["kd"])
    mvp_ratio = _safe_ratio(player_stats["mvp_per_match"], baseline["mvp_per_match"])
    survival_ratio = _safe_ratio(baseline["death_rate"], player_stats["death_rate"])

    return {
        "kill_pressure": _ratio_to_index(kill_pressure_ratio, swing=38.0, cap_low=0.68, cap_high=1.32),
        "damage_pressure": _ratio_to_index(damage_pressure_ratio, swing=36.0, cap_low=0.7, cap_high=1.3),
        "efficiency": _ratio_to_index(efficiency_ratio, swing=35.0, cap_low=0.7, cap_high=1.3),
        "mvp_conversion": _ratio_to_index(mvp_ratio, swing=28.0, cap_low=0.65, cap_high=1.35),
        "survival": _ratio_to_index(survival_ratio, swing=24.0, cap_low=0.72, cap_high=1.28),
    }


def compute_impact_value(components: dict[str, float], *, matches: int) -> float:
    base = (
        (components["kill_pressure"] * 0.31)
        + (components["damage_pressure"] * 0.28)
        + (components["efficiency"] * 0.2)
        + (components["mvp_conversion"] * 0.12)
        + (components["survival"] * 0.09)
    )
    reliability = _clamp(matches / 12.0, 0.35, 1.0)
    stabilized = (base * reliability) + (50.0 * (1.0 - reliability))
    return _clamp(stabilized, 10.0, 95.0)


def classify_impact_tier(impact: float) -> str:
    if impact >= 85:
        return "Elite"
    if impact >= 70:
        return "Strong"
    if impact >= 50:
        return "Average"
    if impact >= 40:
        return "Weak"
    return "Low Influence"


def compute_grevscore_components(
    player_stats: dict[str, float],
    baseline: dict[str, float],
    *,
    impact_value: float,
    form_ratio: float = 1.0,
) -> dict[str, float]:
    fragging_ratio = _clamp((_safe_ratio(player_stats["kd"], baseline["kd"]) * 0.55) + (_safe_ratio(player_stats["kpr"], baseline["kpr"]) * 0.45), 0.7, 1.35)
    damage_ratio = _clamp(_safe_ratio(player_stats["dpr"], baseline["dpr"]), 0.72, 1.33)
    efficiency_ratio = _clamp((_safe_ratio(player_stats["acc"], baseline["acc"]) * 0.55) + (_safe_ratio(player_stats["hs"], baseline["hs"]) * 0.45), 0.78, 1.24)
    influence_ratio = _clamp(impact_value / 50.0, 0.72, 1.35)
    consistency_ratio = _clamp(_safe_ratio(player_stats["consistency"], baseline["consistency"]), 0.7, 1.25)
    output_ratio = _clamp(_safe_ratio(player_stats["kills_per_match"], baseline["kills_per_match"]), 0.75, 1.25)
    momentum_ratio = _clamp(form_ratio, 0.72, 1.26)
    return {
        "fragging": fragging_ratio,
        "damage": damage_ratio,
        "efficiency": efficiency_ratio,
        "influence": influence_ratio,
        "consistency": consistency_ratio,
        "output": output_ratio,
        "momentum": momentum_ratio,
    }


def compute_grevscore_value(components: dict[str, float], *, matches: int) -> float:
    core_score = (
        (components["fragging"] * 0.26)
        + (components["damage"] * 0.18)
        + (components["efficiency"] * 0.14)
        + (components["influence"] * 0.2)
        + (components["consistency"] * 0.12)
        + (components["output"] * 0.1)
    )
    blended = (core_score * 0.76) + (components["momentum"] * 0.24)
    reliability = _clamp(matches / 12.0, 0.35, 1.0)
    stabilized = (blended * reliability) + (1.0 * (1.0 - reliability))
    return _clamp(stabilized, 0.62, 1.62)


def classify_grevscore_tier(score: float) -> str:
    if score >= 1.34:
        return "Elite"
    if score >= 1.15:
        return "Strong"
    if score >= 0.95:
        return "Average"
    if score >= 0.82:
        return "Poor"
    return "Very Poor"


def _calc_player_card_metrics(
    filtered_players: pd.DataFrame,
    filtered_tactics: pd.DataFrame,
    *,
    baseline_profile: dict[str, float] | None = None,
    recent_form_score: float | None = None,
) -> dict[str, float]:
    match_record = _match_record_from_tactics(filtered_tactics)
    matches = max(int(match_record["matches"]), 1)
    kills = float(filtered_players["kills"].sum())
    deaths = float(filtered_players["deaths"].sum())
    assists = float(filtered_players["mvps"].sum())
    damage = float(filtered_players["damage"].sum())
    rounds = float(filtered_players["rounds_played"].sum())
    acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0

    kda = (kills + assists) / deaths if deaths else kills + assists
    kd = kills / deaths if deaths else kills
    dpm = damage / matches
    kpr = kills / rounds if rounds else 0.0
    dpr = damage / rounds if rounds else 0.0
    mvp_per_match = assists / matches if matches else 0.0

    total_results = match_record["wins"] + match_record["losses"] + match_record["draws"]
    win_rate = (match_record["wins"] / total_results * 100.0) if total_results else 0.0

    hs = float(filtered_players["hs_pct"].mean()) if "hs_pct" in filtered_players.columns else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if "kpd" in filtered_players.columns else 0.0
    kpd_consistency = 1.0
    if "kpd" in filtered_players.columns and len(filtered_players) > 1:
        kpd_std = float(filtered_players["kpd"].std(ddof=0))
        kpd_consistency = max(0.0, min(1.0, 1.0 - (kpd_std / 1.25)))

    baseline = baseline_profile or _build_metric_baseline(filtered_players)
    player_stats = {
        "kd": kd,
        "kpr": kpr,
        "dpr": dpr,
        "acc": acc,
        "hs": hs,
        "mvp_per_match": mvp_per_match,
        "death_rate": (deaths / rounds) if rounds else 0.65,
        "consistency": kpd_consistency,
        "kills_per_match": (kills / matches) if matches else 0.0,
    }
    impact_components = compute_impact_components(player_stats, baseline)
    impact = compute_impact_value(impact_components, matches=matches)
    impact_tier = classify_impact_tier(impact)

    form_reference = baseline.get("form", 58.0)
    recent_form = recent_form_score if recent_form_score is not None else form_reference
    form_ratio = _safe_ratio(recent_form, form_reference)
    grev_components = compute_grevscore_components(player_stats, baseline, impact_value=impact, form_ratio=form_ratio)
    grevscore = compute_grevscore_value(grev_components, matches=matches)
    grevscore_raw = _clamp(grevscore * 100.0, 0.0, 100.0)

    impact_formula = (
        "Impact Index uses normalized kill pressure, damage pressure, efficiency, MVP conversion, "
        "and death suppression with sample-size stabilization."
    )
    grev_formula = (
        "GrevScore blends fragging, damage, efficiency, influence, consistency, and output (76%) "
        "with recent form momentum (24%), centered around 1.00."
    )
    return {
        "matches": float(match_record["matches"]),
        "wins": float(match_record["wins"]),
        "losses": float(match_record["losses"]),
        "draws": float(match_record["draws"]),
        "kills": kills,
        "deaths": deaths,
        "assists": assists,
        "rounds": rounds,
        "kda": kda,
        "kd": kd,
        "dpm": dpm,
        "dpr": dpr,
        "acc": acc,
        "kpr": kpr,
        "impact": impact,
        "impact_tier": impact_tier,
        "impact_components": impact_components,
        "impact_formula": impact_formula,
        "grevscore_raw": grevscore_raw,
        "grevscore": grevscore,
        "grevscore_tier": classify_grevscore_tier(grevscore),
        "grevscore_components": grev_components,
        "grevscore_formula": grev_formula,
        "form_baseline": form_reference,
    }


def _score_tier_label(score: float) -> str:
    return classify_grevscore_tier(score)


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


def _achievement_position_class(position_value: object) -> str:
    raw = str(position_value or "").strip()
    if not raw:
        return ""
    position_num = extract_position_number(raw)
    if position_num is None:
        return "pos-ladder"
    if position_num == 1:
        return "pos-gold"
    if position_num == 2:
        return "pos-silver"
    if position_num == 3:
        return "pos-bronze"
    return "pos-ladder"


def _achievement_season_display(ach_row: pd.Series) -> str:
    season_num = ach_row.get("season_num")
    if pd.notna(season_num):
        return f"SEASON {int(season_num)}"
    for key in ("season_name", "season_label_norm", "achievement_name"):
        parsed_num = extract_season_number(ach_row.get(key))
        if parsed_num is not None:
            return f"SEASON {parsed_num}"
    return "SEASON"


def build_player_achievements(
    achievements_df: pd.DataFrame,
    image_index: dict[str, dict[str, Path]],
    selected_player: str,
    selected_season: str,
) -> pd.DataFrame:
    if achievements_df.empty:
        return pd.DataFrame()

    achievements_df = achievements_df.copy()
    required_defaults = {
        "player_core": "",
        "season_label_norm": "",
        "season_num": pd.NA,
        "position_label_norm": "",
        "position_num": pd.NA,
    }
    for col, default in required_defaults.items():
        if col not in achievements_df.columns:
            achievements_df[col] = default
    if "season_num" in achievements_df.columns:
        achievements_df["season_num"] = pd.to_numeric(achievements_df["season_num"], errors="coerce").astype("Int64")
    if "position_num" in achievements_df.columns:
        achievements_df["position_num"] = pd.to_numeric(achievements_df["position_num"], errors="coerce").astype("Int64")
    if "position_label_norm" in achievements_df.columns:
        achievements_df["position_label_norm"] = achievements_df["position_label_norm"].apply(normalize_position_label)

    selected_player_core = extract_core_player_name(selected_player)
    matched = achievements_df[achievements_df["player_core"] == selected_player_core].copy()
    if matched.empty:
        return pd.DataFrame()

    if selected_season != "Lifetime":
        season_match = re.match(r"^S(\d+)$", str(selected_season), flags=re.IGNORECASE)
        if season_match:
            target_season = int(season_match.group(1))
            season_matched = matched[matched["season_num"] == target_season].copy()
            # Fail-open for reliability: keep the player's achievements if a season parse mismatch would otherwise wipe all medals.
            if not season_matched.empty:
                matched = season_matched

    matched["achievement_title"] = matched["achievement_name"].apply(
        lambda value: (_normalize_achievement_text(value) or "unnamed achievement").upper()
    )
    resolved_details = matched.apply(lambda row: resolve_achievement_image_details(image_index, row), axis=1)
    matched["achievement_image"] = resolved_details.apply(lambda details: details[0])
    matched["resolved_filename"] = resolved_details.apply(lambda details: details[1])
    matched["image_resolution_source"] = resolved_details.apply(lambda details: details[2])
    matched["image_missing"] = matched["achievement_image"].isna()
    matched["season_display"] = matched.apply(_achievement_season_display, axis=1)
    matched["top_badge"] = matched["achievement_tier"].astype(str).str.strip().str.upper().str[:1]
    matched.loc[~matched["top_badge"].isin(["S", "A", "B", "C"]), "top_badge"] = "—"
    tier_weight = {"S": 4, "A": 3, "B": 2, "C": 1}
    matched["_tier_score"] = matched["achievement_tier"].astype(str).str.strip().str.upper().map(tier_weight).fillna(0)
    matched["_position_score"] = matched["position_num"].fillna(999)
    matched = matched.sort_values(["_tier_score", "_position_score", "season_num"], ascending=[False, True, False])
    return matched.drop(columns=["_tier_score", "_position_score"])


def _form_scores_from_rows(player_rows: pd.DataFrame, tactics_df: pd.DataFrame) -> pd.DataFrame:
    if player_rows.empty:
        return pd.DataFrame()

    scoped = player_rows.copy()
    match_ids = scoped["match_id"].dropna().unique().tolist()
    tactics_matches = tactics_df[tactics_df["match_id"].isin(match_ids)].copy()
    tactics_summary = (
        tactics_matches.groupby("match_id", as_index=False)[["wins", "losses"]].sum()
        if not tactics_matches.empty
        else pd.DataFrame(columns=["match_id", "wins", "losses"])
    )
    scoped = scoped.merge(tactics_summary, on="match_id", how="left")
    scoped[["wins", "losses"]] = scoped[["wins", "losses"]].fillna(0)
    scoped["kda"] = (scoped["kills"] + scoped["mvps"]) / scoped["deaths"].replace(0, 1)
    scoped["result_points"] = (scoped["wins"] > scoped["losses"]).astype(float)
    scoped["kpr"] = scoped["kills"] / scoped["rounds_played"].replace(0, 1)
    scoped["dpr"] = scoped["damage"] / scoped["rounds_played"].replace(0, 1)

    scoped["match_form_score"] = (
        (scoped["kpd"] / 1.2).clip(0.45, 1.35) * 32
        + (scoped["kpr"] / 0.72).clip(0.45, 1.35) * 22
        + (scoped["dpr"] / 145.0).clip(0.45, 1.35) * 20
        + (scoped["accuracy_pct"] / 58.0).clip(0.45, 1.28) * 10
        + (scoped["hs_pct"] / 35.0).clip(0.45, 1.28) * 6
        + scoped["result_points"] * 10
    ).clip(lower=15, upper=100)
    return scoped


def _calculate_form_section(player_rows: pd.DataFrame, tactics_df: pd.DataFrame) -> tuple[float, pd.DataFrame]:
    scored = _form_scores_from_rows(player_rows.sort_values("date", ascending=False).head(10), tactics_df)
    form_score = float(scored["match_form_score"].mean()) if not scored.empty else 0.0
    return form_score, scored


def compute_recent_window_metrics(
    player_rows: pd.DataFrame,
    tactics_df: pd.DataFrame,
    *,
    long_term_grevscore: float,
    long_term_form: float,
    baseline_profile: dict[str, float],
    min_matches: int = 4,
) -> dict[str, object]:
    if player_rows.empty:
        return {
            "window_rows": pd.DataFrame(),
            "window_start": None,
            "window_end": None,
            "matches": 0,
            "low_sample": True,
            "grevscore_14d": None,
            "form_14d": None,
            "grev_delta": 0.0,
            "form_delta": 0.0,
            "trend": "Stable",
            "sparkline": [],
        }

    window_end = pd.to_datetime(player_rows["date"].max())
    window_start = window_end - pd.Timedelta(days=13)
    window_rows = player_rows[player_rows["date"].between(window_start, window_end, inclusive="both")].copy()
    matches = int(window_rows["match_id"].nunique()) if "match_id" in window_rows.columns else len(window_rows)
    low_sample = matches < min_matches

    scored_rows = _form_scores_from_rows(window_rows, tactics_df)
    form_14d = float(scored_rows["match_form_score"].mean()) if not scored_rows.empty else None

    if not low_sample and not window_rows.empty:
        recent_metrics = _calc_player_card_metrics(
            window_rows,
            tactics_df[tactics_df["match_id"].isin(window_rows["match_id"].unique())],
            baseline_profile=baseline_profile,
            recent_form_score=form_14d,
        )
        grev_14d = float(recent_metrics["grevscore"])
    else:
        grev_14d = None

    trend = "Stable"
    if len(scored_rows) >= 6:
        ordered = scored_rows.sort_values("date")
        half = len(ordered) // 2
        early = float(ordered["match_form_score"].head(half).mean())
        late = float(ordered["match_form_score"].tail(half).mean())
        delta = late - early
        if delta > 2.5:
            trend = "Rising"
        elif delta < -2.5:
            trend = "Dropping"

    sparkline = scored_rows.sort_values("date")["match_form_score"].tail(14).round(1).tolist() if not scored_rows.empty else []
    return {
        "window_rows": scored_rows,
        "window_start": window_start,
        "window_end": window_end,
        "matches": matches,
        "low_sample": low_sample,
        "grevscore_14d": grev_14d,
        "form_14d": form_14d,
        "grev_delta": (grev_14d - long_term_grevscore) if grev_14d is not None else 0.0,
        "form_delta": (form_14d - long_term_form) if form_14d is not None else 0.0,
        "trend": trend,
        "sparkline": sparkline,
    }


def compute_14d_grevscore(recent_metrics: dict[str, object]) -> float | None:
    return recent_metrics.get("grevscore_14d")  # type: ignore[return-value]


def compute_14d_form(recent_metrics: dict[str, object]) -> float | None:
    return recent_metrics.get("form_14d")  # type: ignore[return-value]


def _metric_state(value: float, low: float, high: float) -> tuple[str, str]:
    if high <= low:
        return "Average", "tier-average"
    ratio = (value - low) / (high - low)
    if ratio >= 1.0:
        return "Excellent", "tier-excellent"
    if ratio >= 0.55:
        return "Good", "tier-good"
    if ratio >= 0.2:
        return "Average", "tier-average"
    if ratio >= -0.2:
        return "Poor", "tier-poor"
    return "Very poor", "tier-very-poor"


def _metric_group(label: str) -> str:
    fragging = {"kills", "k/d", "kpr", "dpm"}
    accuracy = {"accuracy%", "hs%"}
    form = {"rating", "grevscore", "form"}
    utility = {"impact"}
    norm = label.strip().casefold()
    if norm in fragging:
        return "group-fragging"
    if norm in accuracy:
        return "group-accuracy"
    if norm in form:
        return "group-form"
    if norm in utility:
        return "group-utility"
    return "group-form"


def _metric_card_html(
    label: str,
    value_text: str,
    value: float,
    low: float,
    high: float,
    *,
    priority: bool = False,
    delta_note: str = "",
) -> str:
    state, tier_class = _metric_state(value, low, high)
    metric_group = _metric_group(label)
    priority_cls = " priority" if priority else ""
    delta_html = f"<div class='metric-delta'>{html.escape(delta_note)}</div>" if delta_note else ""
    return (
        f"<div class='metric-card {metric_group} {tier_class}{priority_cls}'>"
        f"<div class='metric-title'>{html.escape(label)}</div>"
        f"<div class='metric-value'>{html.escape(value_text)}</div>"
        f"<div class='metric-state'>{state}</div>"
        f"{delta_html}"
        "</div>"
    )


def _headline_stat_card_html(label: str, value: str, subtext: str, metric_class: str = "metric-rating") -> str:
    return (
        f"<div class='headline-card {metric_class}'>"
        f"<div class='headline-label'>{html.escape(label)}</div>"
        f"<div class='headline-value'>{html.escape(value)}</div>"
        f"<div class='headline-sub'>{html.escape(subtext)}</div>"
        "</div>"
    )


def _achievement_premium_card_html(ach_row: pd.Series) -> str:
    ach_tier = str(ach_row.get("achievement_tier", "")).strip().upper()[:1] or "?"
    tier_class = _achievement_tier_class(ach_tier).replace("tier-", "")
    position_class = _achievement_position_class(ach_row.get("position"))
    ach_image = ach_row.get("achievement_image")
    season = html.escape(str(ach_row.get("season_display", ach_row.get("season_name", "SEASON ?"))))
    label = html.escape(str(ach_row.get("achievement_title", ach_row.get("achievement_name", "-"))))
    finish = html.escape(str(ach_row.get("position", "")).strip())
    top_badge = html.escape(str(ach_row.get("top_badge", ach_tier))) or "—"
    image_html = "<div class='achievement-missing'>Achievement image missing</div>"
    if isinstance(ach_image, Path) and ach_image.exists():
        image_html = f'<img src="{_image_to_data_uri(ach_image)}" alt="{label}">'
    position_badge_html = f"<span class='achievement-position {position_class}'>{finish}</span>" if finish else ""
    position_or_placeholder = position_badge_html or "<span class='achievement-position'>—</span>"
    return (
        f"<div class='achievement-premium glow-{tier_class}'>"
        "<div class='achievement-image-wrap'>"
        "<div class='achievement-top-row'>"
        "<div class='achievement-top-right achievement-badge-stack achievement-header-cluster'>"
        f"{position_or_placeholder}"
        f"<span class='achievement-tier-badge tier-{tier_class}' aria-label='Tier {top_badge}'><span class='achievement-tier-badge__text'>{top_badge}</span></span>"
        "</div>"
        "</div>"
        f"{image_html}"
        "</div>"
        "<div class='achievement-footer'>"
        f"<div class='achievement-inline-name'>{label}</div>"
        f"<div class='achievement-season achievement-season-badge'>{season}</div>"
        "</div>"
        "</div>"
    )


def render_player_achievements_inline(player_achievements: pd.DataFrame) -> str:
    """Render a compact inline achievements cabinet for the profile hero left card."""
    if player_achievements.empty:
        return (
            "<div class='achievement-inline-empty'>"
            "<div class='achievement-empty-title'>Achievement Cabinet</div>"
            "<div class='achievement-empty-sub'>No achievements found for the current player/filter context.</div>"
            "</div>"
        )
    cards = "".join(_achievement_premium_card_html(row) for _, row in player_achievements.iterrows())
    return f"<div class='achievement-row achievement-inline-cabinet'>{cards}</div>"


def _trend_icon_and_class(trend_direction: str) -> tuple[str, str]:
    if str(trend_direction).strip().lower() == "rising":
        return "↗", "up"
    return "↘", "down"


def _build_performance_summary(metrics: dict[str, float], trend_direction: str, form_score: float) -> str:
    fragger_state = "elite fragger" if metrics["kpr"] >= 0.74 else ("stable fragger" if metrics["kpr"] >= 0.62 else "below-average fragger")
    utility_state = "high utility impact" if metrics["impact"] >= 76 else ("solid utility impact" if metrics["impact"] >= 66 else "light utility impact")
    form_state = "form currently rising" if trend_direction == "Rising" and form_score >= 65 else (
        "form unstable recently" if trend_direction == "Rising" else "form currently dropping"
    )
    return f"{fragger_state}, {utility_state}, {form_state}"


def build_player_profile_descriptor(metrics: dict[str, float], *, avg_acc: float, avg_hs: float, form_score: float) -> str:
    kpr = float(metrics.get("kpr", 0.0))
    impact = float(metrics.get("impact", 0.0))
    if kpr < 0.58 and impact < 63:
        lead = "Support-leaning profile with weak kill conversion"
    elif kpr < 0.62 and avg_acc >= 56:
        lead = "Low-output fragger with decent accuracy"
    elif kpr < 0.62 and impact >= 67:
        lead = "Fragging below average, but efficiency is holding"
    elif avg_acc >= 58 and impact < 66:
        lead = "Solid accuracy profile, but low pressure output"
    elif kpr >= 0.71 and impact >= 74:
        lead = "Aggressive impact profile with strong conversion"
    else:
        lead = "Balanced profile with moderate conversion pressure"

    if form_score < 55:
        tail = "Recent form unstable, impact remains low"
    elif form_score >= 70 and impact >= 72:
        tail = "Recent form is stable with dependable impact"
    else:
        tail = "Recent form is mixed across this filter window"
    return f"{lead}. {tail}"


def build_player_stat_insight(metrics: dict[str, float], *, avg_acc: float, avg_hs: float, recent10_delta: float) -> str:
    kpr = float(metrics.get("kpr", 0.0))
    if recent10_delta <= -0.07:
        return "Output has cooled over the last 10 matches; prioritize cleaner conversion setups."
    if avg_acc >= 57 and kpr < 0.62:
        return "Aim fundamentals are stable, but final-frag conversion is trailing."
    if avg_hs >= 37 and float(metrics.get("impact", 0.0)) < 66:
        return "High headshot share is present, but round impact is not converting consistently."
    if recent10_delta >= 0.08:
        return "Recent trend is positive; keep current role responsibilities and tempo balance."
    return "Profile is steady with no major single-stat outlier in this context."


def _home() -> None:
    _inject_styles()
    _render_top_hero(
        active_page="front_page",
        subtitle="Team roster intelligence, player analytics, tactical breakdowns, and matchup insights.",
    )


def _front_page(player_df: pd.DataFrame, tactics_df: pd.DataFrame, competition_source_col: str) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="front_page",
        subtitle="Visual roster board: current ability, recent form, and player-by-player comparison.",
    )
    st.markdown("<div class='tb-section-title'>Front Page</div>", unsafe_allow_html=True)
    st.caption("Team roster overview with premium profile cards and quick sorting controls.")

    team_players = sorted(player_df[player_df["player"].astype(str).str.contains("ⓜ", regex=False, na=False)]["player"].dropna().unique().tolist())
    if not team_players:
        st.warning("No Medisports players found.")
        return

    all_seasons = sorted(player_df[competition_source_col].apply(extract_season_number).dropna().astype(int).unique().tolist(), reverse=True)
    season_options = ["Lifetime"] + [f"S{season}" for season in all_seasons]
    selected_season = st.selectbox("Season", season_options, index=0, key="front_page_season")
    map_options = sorted(player_df["map"].dropna().astype(str).unique().tolist()) if "map" in player_df.columns else []
    sort_metric = st.selectbox("Sort by", ["GrevScore", "Rating", "Impact", "Form", "K/D"], key="front_page_sort")
    selected_maps = st.multiselect("Map filter", map_options, default=[], key="front_page_map_filter")
    current_only = st.toggle("Current roster only", value=True, key="front_page_current_only")

    scoped_players = apply_season_filter(player_df.copy(), selected_season, competition_source_col)
    if selected_maps:
        scoped_players = scoped_players[scoped_players["map"].isin(selected_maps)].copy()

    profiles = _load_play_csv_profiles()
    if current_only and not profiles.empty and "player" in profiles.columns:
        current_roster = set(profiles["player"].astype(str).str.strip())
        scoped_players = scoped_players[scoped_players["player"].isin(current_roster)].copy()
    else:
        scoped_players = scoped_players[scoped_players["player"].isin(team_players)].copy()

    if scoped_players.empty:
        st.info("No rows match the Front Page filters.")
        return

    baseline = _build_metric_baseline(player_df[player_df["match_id"].isin(scoped_players["match_id"].unique())].copy())
    image_index = _build_image_index()
    cards: list[dict[str, object]] = []
    for player_name, rows in scoped_players.groupby("player"):
        player_tactics = tactics_df[tactics_df["match_id"].isin(rows["match_id"].unique())].copy()
        form_score, recent_form = _calculate_form_section(rows, player_tactics)
        metrics = _calc_player_card_metrics(rows, player_tactics, baseline_profile=baseline, recent_form_score=form_score)
        trend_direction = "Stable"
        if len(recent_form) >= 8:
            first_half = float(recent_form.head(len(recent_form) // 2)["kpd"].mean())
            second_half = float(recent_form.tail(len(recent_form) // 2)["kpd"].mean())
            if second_half > first_half + 0.03:
                trend_direction = "Rising"
            elif second_half < first_half - 0.03:
                trend_direction = "Dropping"
        role = get_player_profile_from_play_csv(player_name).get("role", "Fragger")
        nation = get_player_profile_from_play_csv(player_name).get("nation", "")
        best_map = rows.groupby("map")["kpd"].mean().sort_values(ascending=False).index[0] if "map" in rows.columns and not rows["map"].dropna().empty else "—"
        cards.append(
            {
                "player": player_name,
                "role": role,
                "nation": nation,
                "flag": _nation_flag_emoji(nation),
                "grevscore": float(metrics["grevscore"]),
                "rating": float(rows["kpd"].mean()) if "kpd" in rows.columns else 0.0,
                "impact": float(metrics["impact"]),
                "form": float(form_score),
                "kd": float(metrics["kd"]),
                "matches": int(metrics["matches"]),
                "trend": trend_direction,
                "best_map": str(best_map),
                "insight": build_player_profile_descriptor(metrics, avg_acc=float(rows["accuracy_pct"].mean()), avg_hs=float(rows["hs_pct"].mean()), form_score=form_score),
                "photo": resolve_player_photo(image_index, player_name),
            }
        )

    cards_df = pd.DataFrame(cards)
    if cards_df.empty:
        st.info("No card data available.")
        return
    sort_map = {"GrevScore": "grevscore", "Rating": "rating", "Impact": "impact", "Form": "form", "K/D": "kd"}
    cards_df = cards_df.sort_values(sort_map[sort_metric], ascending=False).reset_index(drop=True)
    strongest = cards_df.iloc[0]["player"]
    hottest = cards_df.sort_values("form", ascending=False).iloc[0]["player"]
    weakest = cards_df.sort_values("form", ascending=True).iloc[0]["player"]

    summary_html = "".join(
        [
            f"<div class='kpi-card'><div class='kpi-label'>Total players shown</div><div class='kpi-value'>{len(cards_df)}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Average GrevScore</div><div class='kpi-value'>{cards_df['grevscore'].mean():.2f}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Average Rating</div><div class='kpi-value'>{cards_df['rating'].mean():.2f}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Average Impact</div><div class='kpi-value'>{cards_df['impact'].mean():.1f}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Strongest current player</div><div class='kpi-value'>{html.escape(str(strongest))}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Hottest recent form</div><div class='kpi-value'>{html.escape(str(hottest))}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Weakest current form</div><div class='kpi-value'>{html.escape(str(weakest))}</div></div>",
        ]
    )
    st.markdown(f"<div class='panel-card'><div class='kpi-grid'>{summary_html}</div></div>", unsafe_allow_html=True)

    selected_profile = st.selectbox("Quick profile drilldown", cards_df["player"].tolist(), index=0, key="front_page_profile_select")
    if st.button("View profile", key="front_page_open_profile"):
        st.session_state["profile_player_override"] = selected_profile
        st.session_state["page"] = "profiles"
        st.rerun()

    card_html = []
    for _, row in cards_df.iterrows():
        trend = str(row["trend"])
        trend_icon = "📈" if trend == "Rising" else ("📉" if trend == "Dropping" else "➖")
        badge = "Low sample" if int(row["matches"]) < 5 else ("Rising" if trend == "Rising" else ("Dropping" if trend == "Dropping" else "Stable"))
        photo_html = (
            f"<img class='roster-photo' src='{_image_to_data_uri(row['photo'])}' alt='player photo'>"
            if isinstance(row["photo"], Path) and row["photo"]
            else "<div class='roster-photo' style='display:flex;align-items:center;justify-content:center;color:#9da7bd;'>N/A</div>"
        )
        card_html.append(
            f"""
            <article class='roster-card'>
                <div class='roster-head'>
                    {photo_html}
                    <div>
                        <div class='roster-name'>{html.escape(str(row["player"]))}</div>
                        <div class='roster-meta'>{html.escape(str(row["flag"]))} {html.escape(str(row["nation"] or "Unknown"))} • {html.escape(str(row["role"]))}</div>
                        <div class='roster-meta'>{trend_icon} {html.escape(trend)} • {html.escape(str(badge))}</div>
                    </div>
                </div>
                <div class='roster-kpis'>
                    <div class='roster-kpi'><div class='k'>GrevScore</div><div class='v'>{float(row["grevscore"]):.2f}</div></div>
                    <div class='roster-kpi'><div class='k'>Rating</div><div class='v'>{float(row["rating"]):.2f}</div></div>
                    <div class='roster-kpi'><div class='k'>Impact</div><div class='v'>{float(row["impact"]):.1f}</div></div>
                    <div class='roster-kpi'><div class='k'>Form</div><div class='v'>{float(row["form"]):.1f}</div></div>
                    <div class='roster-kpi'><div class='k'>K/D</div><div class='v'>{float(row["kd"]):.2f}</div></div>
                    <div class='roster-kpi'><div class='k'>Best map</div><div class='v'>{html.escape(str(row["best_map"]))}</div></div>
                </div>
                <div class='mini-note'>{html.escape(str(row["insight"]))}</div>
            </article>
            """
        )
    st.markdown(f"<section class='roster-grid'>{''.join(card_html)}</section>", unsafe_allow_html=True)


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
    latest_season = detect_latest_season(filtered_players, competition_source_col)

    min_date = filtered_players["date"].min().date()
    max_date = filtered_players["date"].max().date()

    st.markdown('<p class="compact-filter-header">Player Filters</p>', unsafe_allow_html=True)
    filter_cols = st.columns(6)
    season_options = ["Lifetime"]
    if latest_season is not None:
        season_options = [f"S{latest_season}", "Lifetime"]
    with filter_cols[0]:
        selected_season = st.selectbox("Season", options=season_options, index=0, key="profile_season")
    tier_options = sorted(filtered_players["tier"].dropna().unique().tolist())
    with filter_cols[1]:
        selected_tiers = _multiselect_filter("Tier of Team", tier_options, key="profile_tier")

    event_options = sorted(filtered_players[competition_source_col].dropna().unique().tolist())
    with filter_cols[2]:
        selected_events = _multiselect_filter("Event", event_options, key="profile_event")

    opp_options = sorted(filtered_players["opponent_team"].dropna().unique().tolist())
    with filter_cols[3]:
        selected_opp = _multiselect_filter("Opponent", opp_options, key="profile_opp")

    side_options = sorted(tactics_df["side"].dropna().unique().tolist()) if "side" in tactics_df else []
    with filter_cols[4]:
        selected_sides = _multiselect_filter("Side (Red/Blue)", side_options, key="profile_side")

    date_range = filter_cols[5].date_input(
        "Date Range",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

    if len(date_range) == 2:
        start_date, end_date = pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1])
    else:
        start_date = end_date = pd.to_datetime(date_range[0])

    filtered_players = apply_season_filter(filtered_players, selected_season, competition_source_col)
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

    default_player = st.session_state.pop("profile_player_override", players[0] if players else None)
    default_index = players.index(default_player) if default_player in players else 0
    selected_player = st.selectbox('Pick a player (names containing "ⓜ")', players, index=default_index)

    with st.expander("Profile Filters", expanded=False):
        filtered_players, filtered_tactics = _apply_shared_filters(
            player_df,
            tactics_df,
            selected_player,
            competition_source_col,
        )

    if filtered_players.empty:
        st.warning("No player rows match the current filters.")
        return

    image_index = _build_image_index()
    profile_data = get_player_profile_from_play_csv(selected_player)

    player_image = resolve_player_photo(image_index, selected_player)
    team_logo = _find_image(image_index, "team", profile_data.get("team"))
    team_logo_html = f'<img style="width:30px;height:30px;border-radius:7px;object-fit:contain;border:1px solid rgba(151,166,195,0.25);" src="{_image_to_data_uri(team_logo)}">' if team_logo else ""

    context_pool = player_df[player_df["match_id"].isin(filtered_players["match_id"].unique())].copy()
    baseline_profile = _build_metric_baseline(context_pool)
    form_score, recent_form = _calculate_form_section(filtered_players, tactics_df)
    metrics = _calc_player_card_metrics(
        filtered_players,
        filtered_tactics,
        baseline_profile=baseline_profile,
        recent_form_score=form_score,
    )
    team_scope = player_df[player_df["player"].astype(str).str.contains("ⓜ", regex=False, na=False)]
    rank_scope = []
    for player_name, rows in team_scope.groupby("player"):
        p_metrics = _calc_player_card_metrics(rows, tactics_df[tactics_df["match_id"].isin(rows["match_id"].unique())])
        rank_scope.append({"player": player_name, "score": p_metrics["grevscore"]})
    rank_df = pd.DataFrame(rank_scope).sort_values("score", ascending=False).reset_index(drop=True)
    team_rank = int(rank_df.index[rank_df["player"] == selected_player][0] + 1) if not rank_df.empty else 1
    rank_total = max(int(len(rank_df)), 1)
    percentile = ((rank_total - team_rank) / rank_total) * 100.0
    score_tier = _score_tier_label(metrics["grevscore"])
    avg_acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0
    avg_hs = float(filtered_players["hs_pct"].mean()) if not filtered_players.empty else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if not filtered_players.empty else 0.0
    player_role = profile_data.get("role", "Fragger")

    side_split = "-"
    side_chart_data = pd.DataFrame(columns=["side", "rating"])
    if not filtered_tactics.empty and "side" in filtered_tactics.columns:
        side_summary = filtered_tactics.groupby("side", as_index=False)[["wins", "losses"]].sum().sort_values("wins", ascending=False)
        if not side_summary.empty:
            s = side_summary.iloc[0]
            side_split = f'{s["side"]}: {int(s["wins"])}W-{int(s["losses"])}L'
    if "side" in filtered_players.columns:
        side_chart_data = filtered_players.dropna(subset=["side"]).groupby("side", as_index=False)["kpd"].mean().rename(columns={"kpd": "rating"}).sort_values("rating", ascending=False)

    best_map = filtered_players.groupby("map")["kills"].sum().sort_values(ascending=False).index[0] if "map" in filtered_players.columns and not filtered_players.empty else "-"
    record_text = f"{int(metrics['wins'])}W-{int(metrics['losses'])}L"
    nation_value = str(profile_data.get("nation", "")).strip()
    nation_flag = _nation_flag_emoji(nation_value, fallback="🌍")
    nation_badge = f"{nation_flag} {nation_value}" if nation_value else nation_flag

    player_ach = build_player_achievements(
        achievements_df=achievements_df,
        image_index=image_index,
        selected_player=selected_player,
        selected_season=st.session_state.get("profile_season", "Lifetime"),
    )
    achievements_inline_html = render_player_achievements_inline(player_ach)

    recent10 = recent_form.sort_values("date").tail(10).copy() if not recent_form.empty else pd.DataFrame()
    recent20 = filtered_players.sort_values("date", ascending=False).head(20).sort_values("date").copy()
    trend_direction = "Rising"
    if len(recent20) >= 6:
        first = recent20["kpd"].head(len(recent20) // 2).mean()
        second = recent20["kpd"].tail(len(recent20) // 2).mean()
        trend_direction = "Rising" if second >= first else "Dropping"
    streak = 0
    if not recent20.empty and {"wins", "losses"}.issubset(recent20.columns):
        results = (recent20.sort_values("date", ascending=False)["wins"].fillna(0) > recent20.sort_values("date", ascending=False)["losses"].fillna(0)).tolist()
        if results:
            current = results[0]
            streak = sum(1 for r in results if r == current)
        streak = streak if results and results[0] else -streak
    recent10_delta = 0.0
    if len(recent10) >= 10:
        first5 = float(recent10["kpd"].head(5).mean())
        last5 = float(recent10["kpd"].tail(5).mean())
        recent10_delta = last5 - first5
    recent_window = compute_recent_window_metrics(
        filtered_players,
        filtered_tactics,
        long_term_grevscore=metrics["grevscore"],
        long_term_form=form_score,
        baseline_profile=baseline_profile,
    )
    grev_14d = compute_14d_grevscore(recent_window)
    form_14d = compute_14d_form(recent_window)

    profile_name = html.escape(profile_data.get("player", selected_player))
    fallback_initial = html.escape(profile_data.get("player", selected_player).strip()[:1].upper() or "P")
    player_img_html = (
        f"<img class='player-headshot' src='{_image_to_data_uri(player_image)}'>"
        if player_image
        else (
            "<div class='portrait-fallback'>"
            f"<div class='portrait-fallback-badge'>{fallback_initial}</div>"
            "<div>Player Portrait</div>"
            "<strong style='color:#eff4ff;'>Visual Profile Card</strong>"
            "</div>"
        )
    )

    trend_icon, trend_class = _trend_icon_and_class(trend_direction)
    performance_summary = _build_performance_summary(metrics, trend_direction, form_score)
    profile_descriptor = build_player_profile_descriptor(metrics, avg_acc=avg_acc, avg_hs=avg_hs, form_score=form_score)
    stat_insight = build_player_stat_insight(metrics, avg_acc=avg_acc, avg_hs=avg_hs, recent10_delta=recent10_delta)
    streak_value_class = "up" if streak > 0 else ("down" if streak < 0 else "flat")
    delta_value_class = "up" if recent10_delta > 0 else ("down" if recent10_delta < 0 else "flat")
    stats_tiles = [
        _headline_stat_card_html("Rating", f"{metrics['grevscore']:.2f}", f"Tier: {score_tier}", metric_class="metric-rating"),
        _headline_stat_card_html("Impact", f"{metrics['impact']:.1f}", f"{percentile:.0f}th percentile · Weighted", metric_class="metric-impact"),
        _headline_stat_card_html("Form", f"{form_score:.1f}", f"{trend_icon} {trend_direction}", metric_class="metric-form"),
        _headline_stat_card_html("Matches", f"{int(metrics['matches'])}", record_text, metric_class="metric-matches"),
    ]
    grev_meter_pct = max(0.0, min((metrics["grevscore"] - 0.65) / (1.28 - 0.65), 1.0)) * 100
    grev_band_class = "good" if metrics["grevscore"] >= 1.02 else ("mid" if metrics["grevscore"] >= 0.85 else "bad")
    if metrics["grevscore"] < 0.85:
        grev_tier_class = "tier-very-poor"
    elif metrics["grevscore"] < 1.0:
        grev_tier_class = "tier-poor"
    elif metrics["grevscore"] < 1.2:
        grev_tier_class = "tier-average"
    elif metrics["grevscore"] < 1.45:
        grev_tier_class = "tier-good"
    else:
        grev_tier_class = "tier-elite"

    priority_cards = [
        _metric_card_html("Grevscore", f"{metrics['grevscore']:.2f}", metrics["grevscore"], 0.95, 1.18, priority=True, delta_note=f"Team #{team_rank}/{rank_total}"),
        _metric_card_html("Impact", f"{metrics['impact']:.1f}", metrics["impact"], 62, 78, priority=True, delta_note="Weighted impact index"),
        _metric_card_html("Form", f"{form_score:.1f}", form_score, 55, 74, priority=True, delta_note=f"{trend_icon} {trend_direction}"),
        _metric_card_html("Rating", f"{avg_kpd:.2f}", avg_kpd, 0.9, 1.18, priority=True, delta_note=f"Last 10 Δ {recent10_delta:+.2f}"),
    ]
    support_cards = [
        _metric_card_html("K/D", f"{metrics['kd']:.2f}", metrics["kd"], 0.9, 1.2, delta_note=f"{int(metrics['kills'])}K / {int(metrics['deaths'])}D"),
        _metric_card_html("KPR", f"{metrics['kpr']:.2f}", metrics["kpr"], 0.58, 0.76, delta_note=f"{int(metrics['kills'])} / {int(metrics['rounds'])} rounds"),
        _metric_card_html("DPM", f"{metrics['dpm']:.0f}", metrics["dpm"], 2200, 2800, delta_note=f"DPR {metrics['dpr']:.1f}"),
        _metric_card_html("HS%", f"{avg_hs:.1f}%", avg_hs, 27, 39),
        _metric_card_html("Accuracy%", f"{avg_acc:.1f}%", avg_acc, 50, 66),
        _metric_card_html("Kills", f"{int(metrics['kills'])}", float(metrics["kills"]), 120, 220),
    ]
    core_cards = priority_cards + support_cards

    # Verification: old st.columns hero was removed from this view and replaced by custom HTML/CSS in `_render_top_hero`.
    # Verification: old st.columns first-row layout was removed from this view and replaced by custom HTML/CSS `.cpl-top-grid` below.
    # Verification: both sections now render as explicit custom HTML/CSS containers (hero + first row), not Streamlit columns.
    st.markdown(
        f"""
        <section class="pv-shell">
            <article class="pv-hero">
                <div class="pv-hero-grid">
                    <div class="pv-portrait">{player_img_html}</div>
                    <div class="pv-main-copy">
                        <div class="pv-context-pill">Season Context · {html.escape(st.session_state.get("profile_season", "Lifetime"))}</div>
                        <h2 class="pv-name">{profile_name}</h2>
                        <div class="pv-teamline">{team_logo_html}<strong>{html.escape(str(profile_data.get('team', '-')))}</strong></div>
                        <div class="pv-meta-row">
                            <span class="pv-meta-chip role">🎯 {html.escape(player_role)}</span>
                            <span class="pv-meta-chip nation">{html.escape(nation_badge)}</span>
                            <span class="pv-meta-chip map">🗺️ Best map: {html.escape(str(best_map))}</span>
                            <span class="pv-meta-chip side">🧭 Best side: {html.escape(side_split)}</span>
                        </div>
                        <div class="pv-summary">"{html.escape(performance_summary)}"</div>
                        <div class="pv-summary" style="margin-top:6px;opacity:0.95;">{html.escape(profile_descriptor)}</div>
                    </div>
                    <div class="pv-side-stack">
                        <div class="pv-side-tile rank"><div class="k">Team Rank</div><div class="v">#{team_rank}/{rank_total}</div></div>
                        <div class="pv-side-tile record"><div class="k">Record</div><div class="v">{record_text}</div></div>
                        <div class="pv-side-tile streak"><div class="k">Current Streak</div><div class="v {streak_value_class}">{streak:+d}</div></div>
                        <div class="pv-side-tile delta"><div class="k">Last 10 Δ</div><div class="v {delta_value_class}">{recent10_delta:+.2f}</div></div>
                    </div>
                </div>
            </article>
            <article class="pv-achievement-ribbon">
                <div class="pv-achievement-title">🏆 Achievement Ribbon</div>
                <div class="pv-achievement-scroll">{achievements_inline_html}</div>
            </article>
            <section class="pv-score-grid">
                <article class="grevscore-card {grev_tier_class}">
                    <div class="grevscore-wrap">
                        <div class="grevscore-label">Signature Stat · GREVSCORE</div>
                        <div class="grevscore-value">{metrics['grevscore']:.2f}</div>
                        <div class="grevscore-band {grev_band_class}">{score_tier}</div>
                        <div class="grevscore-status"><span class="accent">{percentile:.0f}th percentile</span> in current filter set · Impact <span class="accent">{metrics['impact']:.1f}</span></div>
                        <div class="grevscore-meter">
                            <div class="grevscore-meter-track">
                                <div class="grevscore-meter-fill" style="width:{grev_meter_pct:.1f}%;"></div>
                            </div>
                            <div class="grevscore-meter-labels"><span>Weak</span><span>Average</span><span>Elite</span></div>
                        </div>
                        <div class="grevscore-meta">
                            <span>Rank #{team_rank}/{rank_total}</span>
                            <span>Trend {trend_icon} {trend_direction}</span>
                            <span>Last 10: {recent10_delta:+.2f}</span>
                        </div>
                    </div>
                </article>
                <article class="stats-card">
                    <div class="headline-header">
                        <div class="section-label">Headline Stats</div>
                        <div class="headline-header-sub">Live profile snapshot · rating, impact, form, and volume</div>
                    </div>
                    <div class="stats-tile-grid">{''.join(stats_tiles)}</div>
                </article>
            </section>
        </section>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("<div class='section-block-title'>Core Performance</div>", unsafe_allow_html=True)
    st.caption(f"Profile insight: {stat_insight}")
    st.markdown(
        f"<div class='core-grid'><div class='performance-grid'>{''.join(core_cards)}</div></div>",
        unsafe_allow_html=True,
    )
    trend_chart = None
    if not recent20.empty and go is not None:
        recent20["match_index"] = range(1, len(recent20) + 1)
        trend_chart = go.Figure()
        trend_chart.add_trace(go.Scatter(
            x=recent20["match_index"], y=recent20["kpd"], mode="lines+markers",
            line=dict(color="#6cc0ff", width=3.1), marker=dict(size=6, color="#68d2a5"),
            hovertemplate="Match %{x}<br>Rating: %{y:.2f}<extra></extra>", showlegend=False,
        ))
        trend_chart.update_layout(title="Recent Form Trend · Last 20 Matches")
        trend_chart.update_xaxes(title_text="Recent matches")
        trend_chart.update_yaxes(title_text="Rating")
        _apply_plotly_dark_style(trend_chart, height=360, hovermode="x unified")

    form_avg_5 = float(recent20["kpd"].tail(5).mean()) if not recent20.empty else 0.0
    form_avg_10 = float(recent20["kpd"].tail(10).mean()) if not recent20.empty else 0.0

    impact_chart = None
    impact_rows: list[dict[str, float | str]] = []
    if "map" in filtered_players.columns:
        for map_name, map_rows in filtered_players.groupby("map"):
            map_tactics = filtered_tactics[filtered_tactics["match_id"].isin(map_rows["match_id"].unique())]
            map_metrics = _calc_player_card_metrics(map_rows, map_tactics)
            impact_rows.append({"map": map_name, "impact": map_metrics["impact"]})
    impact_map = pd.DataFrame(impact_rows).sort_values("impact", ascending=False) if impact_rows else pd.DataFrame(columns=["map", "impact"])
    if not impact_map.empty and go is not None:
        impact_chart = go.Figure(go.Bar(x=impact_map["impact"], y=impact_map["map"], orientation="h", marker=dict(color="#f0be4f"), showlegend=False))
        impact_chart.update_layout(title="Impact by Map")
        impact_chart.update_xaxes(title_text="Impact index")
        impact_chart.update_yaxes(title_text=None, autorange="reversed")
        _apply_plotly_dark_style(impact_chart, height=290)

    map_chart = None
    map_perf = filtered_players.groupby("map", as_index=False)["kpd"].mean().rename(columns={"kpd": "rating"}).sort_values("rating", ascending=False)
    if not map_perf.empty and go is not None:
        map_chart = go.Figure(go.Bar(x=map_perf["rating"], y=map_perf["map"], orientation="h", marker=dict(color="#5ea9ff"), showlegend=False))
        map_chart.update_layout(title="Map Performance")
        map_chart.update_xaxes(title_text="Rating")
        map_chart.update_yaxes(title_text=None, autorange="reversed")
        _apply_plotly_dark_style(map_chart, height=290)

    team_scope_filtered = team_scope[team_scope["match_id"].isin(filtered_players["match_id"].unique())].copy()
    team_scope_metrics = _calc_player_card_metrics(
        team_scope_filtered,
        tactics_df[tactics_df["match_id"].isin(team_scope_filtered["match_id"].unique())],
    )
    comparison_metrics = pd.DataFrame([
        {"metric": "Rating", "player": metrics["grevscore"], "team_avg": team_scope_metrics["grevscore"]},
        {"metric": "K/D", "player": metrics["kd"], "team_avg": team_scope_metrics["kd"]},
        {"metric": "Impact", "player": metrics["impact"], "team_avg": team_scope_metrics["impact"]},
        {"metric": "HS%", "player": avg_hs, "team_avg": _safe_mean(team_scope_filtered, "hs_pct")},
    ]).melt("metric", var_name="group", value_name="value")
    comparison_metrics["group"] = comparison_metrics["group"].map({"player": selected_player, "team_avg": "Team Avg"})

    comparison_chart = None
    if go is not None:
        comparison_chart = go.Figure()
        for group_name, color in [(selected_player, "#31d17b"), ("Team Avg", "#9da7bd")]:
            gdf = comparison_metrics[comparison_metrics["group"] == group_name]
            comparison_chart.add_trace(go.Bar(x=gdf["value"], y=gdf["metric"], orientation="h", marker=dict(color=color), name=group_name))
        comparison_chart.update_layout(title="Player vs Team Average", barmode="group")
        comparison_chart.update_xaxes(title_text="Value")
        comparison_chart.update_yaxes(title_text=None, categoryorder="array", categoryarray=list(reversed(comparison_metrics["metric"].drop_duplicates().tolist())))
        _apply_plotly_dark_style(comparison_chart, height=290)

    side_chart = None
    if not side_chart_data.empty and go is not None:
        side_chart = go.Figure(go.Bar(x=side_chart_data["side"], y=side_chart_data["rating"], marker=dict(color="#f48966"), showlegend=False))
        side_chart.update_layout(title="Side Split Comparison")
        side_chart.update_xaxes(title_text="Side")
        side_chart.update_yaxes(title_text="Avg K/D")
        _apply_plotly_dark_style(side_chart, height=290)

    recent_trend = str(recent_window["trend"])
    form_delta_text = "—" if form_14d is None else f"{(form_14d - form_score):+,.1f}"
    grev_delta_text = "—" if grev_14d is None else f"{(grev_14d - metrics['grevscore']):+,.2f}"
    sample_text = f"{recent_window['matches']} matches in 14D window"
    bar_5 = _clamp((form_avg_5 - 0.75) / 0.55, 0.0, 1.0) * 100
    bar_10 = _clamp((form_avg_10 - 0.75) / 0.55, 0.0, 1.0) * 100
    trend_word = "Improving" if recent_trend == "Rising" else ("Cooling" if recent_trend == "Dropping" else "Stable")

    team_impact = team_scope_metrics["impact"]
    impact_delta = metrics["impact"] - team_impact
    impact_14d = None
    if not recent_window["low_sample"] and not recent_window["window_rows"].empty:
        impact_14d_metrics = _calc_player_card_metrics(
            recent_window["window_rows"],
            filtered_tactics[filtered_tactics["match_id"].isin(recent_window["window_rows"]["match_id"].unique())],
            baseline_profile=baseline_profile,
            recent_form_score=form_14d,
        )
        impact_14d = float(impact_14d_metrics["impact"])

    if metrics["impact_components"]["damage_pressure"] >= metrics["impact_components"]["mvp_conversion"] + 8:
        impact_profile_note = "High damage pressure with lower conversion — strong chip pressure but fewer closing rounds."
    elif metrics["impact_components"]["survival"] >= 56 and metrics["impact_components"]["kill_pressure"] < 52:
        impact_profile_note = "Efficient low-death support impact — stable survivability with moderate frag load."
    elif metrics["impact_components"]["kill_pressure"] >= 60:
        impact_profile_note = "Frag-driven impact profile with above-average direct pressure."
    else:
        impact_profile_note = "Low influence period — pressure indicators are currently below the context average."

    if recent_window["low_sample"]:
        snapshot_insight = f"{sample_text}; read direction as early signal rather than settled form."
    elif recent_trend == "Rising" and impact_14d is not None and impact_14d >= metrics["impact"]:
        snapshot_insight = "Low-to-moderate baseline, but 14-day form and impact are both moving in a positive direction."
    elif recent_trend == "Dropping":
        snapshot_insight = "Output has cooled in the recent window; efficiency is holding better than fragging pressure."
    elif form_avg_5 >= form_avg_10:
        snapshot_insight = "Recent matches are tracking slightly above the broader 10-match form baseline."
    else:
        snapshot_insight = "Performance is steady overall, with no strong short-term acceleration in the latest matches."

    if recent_window["low_sample"]:
        form_summary = f"Small sample ({sample_text}) so direction can swing quickly."
    elif recent_trend == "Rising" and form_avg_5 >= form_avg_10:
        form_summary = "Recent output has improved in the 14-day window, and the last 5 sits above the 10-match trend."
    elif recent_trend == "Dropping":
        form_summary = "Form is drifting downward, with recent match output below earlier window levels."
    else:
        form_summary = "Form is mostly stable, with minor variation between short and medium recent windows."

    grev_component_rows = "".join(
        (
            "<div class='component-row'>"
            f"<div class='name'>{html.escape(k.title())}</div>"
            f"<div class='track'><span style='width:{_clamp((float(v) - 0.6) / 0.95, 0.0, 1.0) * 100:.1f}%;'></span></div>"
            f"<div class='val'>{float(v):.2f}</div>"
            "</div>"
        )
        for k, v in metrics["grevscore_components"].items()
    )
    impact_component_rows = "".join(
        (
            "<div class='component-row'>"
            f"<div class='name'>{html.escape(k.replace('_', ' ').title())}</div>"
            f"<div class='track'><span style='width:{_clamp(float(v) / 100.0, 0.0, 1.0) * 100:.1f}%;'></span></div>"
            f"<div class='val'>{float(v):.1f}</div>"
            "</div>"
        )
        for k, v in metrics["impact_components"].items()
    )

    st.markdown("<div class='section-block-title'>Performance Snapshot</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='insight-shell'>
            <div class='analysis-module'>
                <div class='analysis-head'>
                    <div>
                        <h4>Performance Snapshot</h4>
                        <p>Headline profile view for current context and 14-day movement.</p>
                    </div>
                    <div class='analysis-chip'>{html.escape(score_tier)}</div>
                </div>
                <div class='snapshot-grid'>
                    <div class='snapshot-card feature'>
                        <div class='label'>GrevScore</div>
                        <div class='value'>{metrics['grevscore']:.2f}</div>
                        <div class='meta'>{percentile:.0f}th percentile · Rank #{team_rank}/{rank_total}</div>
                    </div>
                    <div class='snapshot-card feature impact'>
                        <div class='label'>Impact</div>
                        <div class='value'>{metrics['impact']:.1f}</div>
                        <div class='meta'>{impact_delta:+.1f} vs team average</div>
                    </div>
                    <div class='snapshot-card'>
                        <div class='label'>Form (14D)</div>
                        <div class='value'>{("—" if form_14d is None else f"{form_14d:.1f}")}</div>
                        <div class='meta'>Δ {form_delta_text}</div>
                    </div>
                    <div class='snapshot-card'>
                        <div class='label'>GrevScore (14D)</div>
                        <div class='value'>{("—" if grev_14d is None else f"{grev_14d:.2f}")}</div>
                        <div class='meta'>Δ {grev_delta_text}</div>
                    </div>
                </div>
                <div class='snapshot-insight-strip'>{html.escape(snapshot_insight)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-block-title'>Recent Form</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='insight-shell'>
            <div class='analysis-module recent-form-shell'>
                <div class='analysis-head'>
                    <div>
                        <h4>Recent Form Trend</h4>
                        <p>Last 20 matches with 14-day movement context.</p>
                    </div>
                    <div class='analysis-chip'>{sample_text}</div>
                </div>
        """,
        unsafe_allow_html=True,
    )
    if trend_chart is not None:
        st.plotly_chart(trend_chart, use_container_width=True)
    elif go is None:
        _render_plotly_unavailable()
    st.markdown(
        f"""
                <div class='recent-form-meta'>
                    <div class='form-stat-chip'><div class='k'>Last 5</div><div class='v'>{form_avg_5:.2f}</div><div class='s'>Current run</div></div>
                    <div class='form-stat-chip'><div class='k'>Last 10</div><div class='v'>{form_avg_10:.2f}</div><div class='s'>Reference band</div></div>
                    <div class='form-stat-chip'><div class='k'>Streak</div><div class='v'>{streak:+d}</div><div class='s'>Result run</div></div>
                    <div class='form-stat-chip'><div class='k'>Direction</div><div class='v'>{trend_word}</div><div class='s'>{trend_icon} {recent_trend}</div></div>
                </div>
                <div class='momentum-row'>
                    <div class='momentum-track'><div class='name'>Last 5 momentum</div><div class='bar'><span style='width:{bar_5:.1f}%;'></span></div><div class='num'>{form_avg_5:.2f}</div></div>
                    <div class='momentum-track'><div class='name'>Last 10 momentum</div><div class='bar'><span style='width:{bar_10:.1f}%;'></span></div><div class='num'>{form_avg_10:.2f}</div></div>
                </div>
                <div class='analysis-note'>{html.escape(form_summary)}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-block-title'>Metric Breakdown</div>", unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class='insight-shell'>
            <div class='analysis-module compact-breakdown'>
                <div class='analysis-head'>
                    <div>
                        <h4>How It’s Built</h4>
                        <p>Transparent component view, compact by default.</p>
                    </div>
                    <div class='analysis-chip'>Model Details</div>
                </div>
                <details>
                    <summary><span>Expand component breakdown</span><span>GrevScore + Impact drivers</span></summary>
                    <div class='breakdown-body'>
                        <div class='component-group'>
                            <div class='component-title'>GrevScore components</div>
                            {grev_component_rows}
                            <div class='analysis-note'>{html.escape(metrics['grevscore_formula'])}</div>
                        </div>
                        <div class='component-group'>
                            <div class='component-title'>Impact components</div>
                            {impact_component_rows}
                            <div class='analysis-note'>{html.escape(metrics['impact_formula'])}</div>
                            <div class='analysis-note'>{html.escape(impact_profile_note)}</div>
                        </div>
                    </div>
                </details>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='section-block-title'>Visual Analytics</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='analysis-module chart-panel'><div class='analysis-head'><div><h4>Visual Analytics Panels</h4><p>Map performance, team comparison, side split and impact decomposition.</p></div><div class='analysis-chip'>Premium View</div></div></div>",
        unsafe_allow_html=True,
    )
    chart_entries = [(map_chart, "No map data available."), (comparison_chart, "Comparison chart unavailable."), (side_chart, "No side split data available."), (impact_chart, "No impact-by-map data available.")]
    cols = st.columns(2)
    for idx, (chart_obj, empty_msg) in enumerate(chart_entries):
        with cols[idx % 2]:
            if chart_obj is not None:
                st.plotly_chart(chart_obj, use_container_width=True)
            elif go is None:
                _render_plotly_unavailable()
            else:
                pass

    st.markdown("<div class='section-block-title'>Tactical Context</div>", unsafe_allow_html=True)
    if filtered_tactics.empty:
        st.info("No tactic data after side/date filters.")
    else:
        top_tactics = filtered_tactics.groupby("tactic_name", as_index=False)[["wins", "losses"]].sum().assign(win_rate=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1)).sort_values(["wins", "win_rate"], ascending=False).head(10)
        st.dataframe(top_tactics, use_container_width=True, hide_index=True)

    with st.expander("Debug / Validation", expanded=False):
        selected_filters = {
            "season": st.session_state.get("profile_season", "Lifetime"),
            "tiers": st.session_state.get("profile_tier", []),
            "events": st.session_state.get("profile_event", []),
            "opponents": st.session_state.get("profile_opp", []),
            "sides": st.session_state.get("profile_side", []),
        }
        debug_payload = {
            "selected_player": selected_player,
            "selected_filters": selected_filters,
            "total_matches": int(metrics["matches"]),
            "wins": int(metrics["wins"]),
            "losses": int(metrics["losses"]),
            "total_kills": int(metrics["kills"]),
            "total_rounds": int(metrics["rounds"]),
            "computed_kpr": round(float(metrics["kpr"]), 4),
            "computed_impact": round(float(metrics["impact"]), 4),
        }
        st.json(debug_payload)

    st.markdown("<div class='section-block-title'>Full Player Match Stats</div>", unsafe_allow_html=True)
    show_cols = ["date", competition_source_col, "map", "opponent_team", "tier", "kills", "deaths", "kpd", "accuracy_pct", "hs_pct", "mvps", "damage", "rounds_played"]
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

    latest_season = detect_latest_season(df, competition_source_col)
    all_seasons = sorted(
        df[competition_source_col].apply(extract_season_number).dropna().astype(int).unique().tolist(),
        reverse=True,
    )
    default_season = f"S{latest_season}" if latest_season is not None else "Lifetime"

    st.markdown(
        """
        <section class="tb-console">
            <div class="tb-console-head">
                <div class="tb-section-title">Tactical Decision Console</div>
                <div class="tb-note">Filters and sample controls for map + side specific analysis (no cross-context transfer).</div>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )
    with st.expander("Filters", expanded=False):
        filter_cols = st.columns(6)
        season_options = ["Lifetime"] + [f"S{season}" for season in all_seasons]
        with filter_cols[0]:
            selected_season = st.selectbox(
                "Season",
                season_options,
                index=season_options.index(default_season) if default_season in season_options else 0,
                key="tactic_season",
            )
        map_opts = sorted(df["map"].dropna().unique().tolist())
        with filter_cols[1]:
            maps = st.multiselect("Map", map_opts, default=[], key="tactic_map", placeholder="All")
        side_opts = sorted(df["side"].dropna().unique().tolist())
        with filter_cols[2]:
            sides = st.multiselect("Side", side_opts, default=[], key="tactic_side", placeholder="All")
        tier_opts = sorted(df["tier"].dropna().unique().tolist())
        with filter_cols[3]:
            tiers = st.multiselect("Tier", tier_opts, default=[], key="tactic_tier", placeholder="All")
        comp_opts = sorted(df[competition_source_col].dropna().unique().tolist())
        with filter_cols[4]:
            comps = st.multiselect("Event", comp_opts, default=[], key="tactic_event", placeholder="All")
        opp_opts = sorted(df["opponent_team"].dropna().unique().tolist())
        with filter_cols[5]:
            opps = st.multiselect("Opponent", opp_opts, default=[], key="tactic_opp", placeholder="All")
        round_type_opts = ["Pistol", "Eco", "Standard"]
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

    df = apply_season_filter(df, selected_season, competition_source_col)
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
        .assign(
            total_map_side_rounds=lambda d: d["wins"] + d["losses"],
            context_baseline_win_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
        )
    )
    tactic_perf = (
        df.groupby(["tactic_name", "map", "side"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            times_used=lambda d: d["wins"] + d["losses"],
            win_pct=lambda d: (d["wins"] / d["times_used"].clip(lower=1) * 100).round(1),
            net_rounds=lambda d: d["wins"] - d["losses"],
        )
        .merge(
            map_side_totals[["map", "side", "total_map_side_rounds", "context_baseline_win_pct"]],
            on=["map", "side"],
            how="left",
        )
    )
    if tactic_perf.empty:
        st.warning("No tactics found for selected filters.")
        return

    min_sample = int(st.slider("Minimum sample (uses)", 1, max(int(tactic_perf["times_used"].max()), 1), 1, key="tactic_min_sample"))
    st.markdown(
        f"<div class='tb-slider-note'>Minimum sample active: <strong>{min_sample}</strong> uses per tactic in the current map+side context.</div>",
        unsafe_allow_html=True,
    )
    tactic_perf = tactic_perf[tactic_perf["times_used"] >= min_sample].copy()
    if tactic_perf.empty:
        st.warning("No tactics meet the minimum sample threshold.")
        return

    tactic_perf["usage_pct"] = (tactic_perf["times_used"] / tactic_perf["total_map_side_rounds"].clip(lower=1) * 100).round(1)
    tactic_perf["delta_vs_baseline"] = (tactic_perf["win_pct"] - tactic_perf["context_baseline_win_pct"]).round(1)
    tactic_perf["context_usage_avg"] = tactic_perf.groupby(["map", "side"])["usage_pct"].transform("mean").round(1)
    tactic_perf["context_total_uses"] = tactic_perf.groupby(["map", "side"])["times_used"].transform("sum")
    tactic_perf["context_tactic_count"] = tactic_perf.groupby(["map", "side"])["tactic_name"].transform("count")
    tactic_perf["insufficient_context_sample"] = (
        (tactic_perf["context_total_uses"] < 10) | (tactic_perf["context_tactic_count"] < 2)
    )

    tier_perf = (
        df.groupby(["tactic_name", "map", "side", "tier"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            tier_uses=lambda d: d["wins"] + d["losses"],
            tier_win_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
        )
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
    tactic_perf["recent_form_5"] = tactic_perf["recent_form_5"].fillna("n/a")
    tactic_perf["recent_form_10"] = tactic_perf["recent_form_10"].fillna("n/a")

    def _confidence_label(row: pd.Series) -> str:
        uses = int(row["times_used"])
        delta = float(row["delta_vs_baseline"])
        if bool(row["insufficient_context_sample"]):
            return "Neutral / unproven"
        if uses >= 14 and delta >= 5:
            return "Proven good"
        if uses >= 14 and delta <= -5:
            return "Proven poor"
        if uses < 6 and delta >= 4:
            return "Early positive signal"
        if uses < 6 and delta <= -4:
            return "Early negative signal"
        return "Neutral / unproven"

    tactic_perf["confidence"] = tactic_perf.apply(_confidence_label, axis=1)
    confidence_badges = {
        "Proven good": "🟢 Proven good",
        "Early positive signal": "🟩 Early positive signal",
        "Neutral / unproven": "⚪ Neutral / unproven",
        "Early negative signal": "🟧 Early negative signal",
        "Proven poor": "🔴 Proven poor",
    }
    tactic_perf["confidence_badge"] = tactic_perf["confidence"].map(confidence_badges)

    def _action_label(row: pd.Series) -> str:
        uses = int(row["times_used"])
        delta = float(row["delta_vs_baseline"])
        recent = float(row["last_10_usage_win_pct"])
        usage = float(row["usage_pct"])
        context_usage_avg = float(row["context_usage_avg"])
        confidence = str(row["confidence"])
        if bool(row["insufficient_context_sample"]):
            return "Monitor"

        if confidence == "Proven poor" and uses >= 12:
            return "Drop"
        if (delta <= -4 and usage >= context_usage_avg) or (uses >= 10 and recent <= 40):
            return "Rework"
        if confidence == "Proven good" and recent >= 50:
            return "Keep"
        if delta >= 4 and usage <= context_usage_avg * 0.75:
            return "Use More"
        return "Monitor"

    tactic_perf["recommended_action"] = tactic_perf.apply(_action_label, axis=1)

    def _reason_label(row: pd.Series) -> str:
        map_name = row["map"]
        side_name = row["side"]
        delta = float(row["delta_vs_baseline"])
        confidence = str(row["confidence"])
        if bool(row["insufficient_context_sample"]):
            return f"Insufficient sample inside {map_name} {side_name} pool"
        if row["recommended_action"] == "Keep":
            return f"Above {map_name} {side_name} baseline with strong sample"
        if row["recommended_action"] == "Use More":
            return f"Underused strong tactic in {map_name} {side_name}"
        if row["recommended_action"] == "Rework":
            return f"Poor recent form and below {map_name} {side_name} baseline"
        if row["recommended_action"] == "Drop":
            return f"Consistently below {map_name} {side_name} baseline in heavy sample"
        if confidence in {"Early positive signal", "Early negative signal"}:
            return f"Low sample in {map_name} {side_name}, signal not proven yet"
        if abs(delta) <= 2:
            return f"Near {map_name} {side_name} baseline, monitor trend"
        return f"Mixed signal in {map_name} {side_name}; keep monitoring"

    tactic_perf["reason"] = tactic_perf.apply(_reason_label, axis=1)
    tactic_perf["action_badge"] = tactic_perf["recommended_action"].map(
        {
            "Keep": "🟢 Keep",
            "Use More": "🔵 Use More",
            "Monitor": "🟡 Monitor",
            "Rework": "🟠 Rework",
            "Drop": "🔴 Drop",
        }
    )

    summary_keys = tactic_perf.apply(lambda r: f'{r["map"]} | {r["side"]} | {r["tactic_name"]}', axis=1)
    summary_key_df = tactic_perf.assign(summary_key=summary_keys)

    summary_options = summary_key_df["summary_key"].drop_duplicates().tolist()
    if not summary_options:
        st.warning("No tactic summaries available.")
        return

    st.markdown("<div class='tb-section-title'>Tactical Action Board</div>", unsafe_allow_html=True)
    map_options = ["All Maps"] + sorted(tactic_perf["map"].dropna().astype(str).unique().tolist())
    side_options = ["Both Sides", "Red", "Blue"]
    filter_map_col, filter_side_col = st.columns(2)
    with filter_map_col:
        selected_board_map = st.selectbox(
            "Map",
            map_options,
            key="tactical_action_board_map_filter",
            help="Limit the Tactical Action Board to one map context, or keep all maps.",
        )
    with filter_side_col:
        selected_board_side = st.selectbox(
            "Side",
            side_options,
            key="tactical_action_board_side_filter",
            help="Limit the Tactical Action Board to one side context, or keep both sides.",
        )

    filtered_tactic_perf = tactic_perf.copy()
    if selected_board_map != "All Maps":
        filtered_tactic_perf = filtered_tactic_perf[filtered_tactic_perf["map"] == selected_board_map]
    if selected_board_side != "Both Sides":
        filtered_tactic_perf = filtered_tactic_perf[filtered_tactic_perf["side"] == selected_board_side]

    st.markdown(
        f"<div class='tb-note'><strong>Showing:</strong> {selected_board_map} • {selected_board_side}</div>",
        unsafe_allow_html=True,
    )

    action_counts = filtered_tactic_perf["recommended_action"].value_counts().to_dict()
    kpi_items = [
        ("Total tactics", len(filtered_tactic_perf)),
        ("High-confidence good", int((filtered_tactic_perf["confidence"] == "Proven good").sum())),
        ("High-confidence poor", int((filtered_tactic_perf["confidence"] == "Proven poor").sum())),
        ("Underused opportunities", int((filtered_tactic_perf["recommended_action"] == "Use More").sum())),
    ]
    kpi_strip_html = "".join(
        f"<div class='tb-kpi'><div class='k'>{label}</div><div class='v'>{int(value)}</div></div>"
        for label, value in kpi_items
    )
    st.markdown(f"<div class='tb-kpi-strip'>{kpi_strip_html}</div>", unsafe_allow_html=True)

    action_order = ["Keep", "Use More", "Monitor", "Rework", "Drop"]
    action_class = {
        "Keep": ("keep", "#3fd18b"),
        "Use More": ("use-more", "#5eb6ff"),
        "Monitor": ("monitor", "#f0be4f"),
        "Rework": ("rework", "#f39b54"),
        "Drop": ("drop", "#f16c80"),
    }

    if filtered_tactic_perf.empty:
        st.markdown(
            "<div class='tb-empty'>No tactics match this map + side selection yet. Try <strong>All Maps</strong> or <strong>Both Sides</strong> to widen the context.</div>",
            unsafe_allow_html=True,
        )
    else:
        board_cols = st.columns(len(action_order))
        for i, action_name in enumerate(action_order):
            with board_cols[i]:
                cls_name, accent = action_class[action_name]
                action_cards_html: list[str] = []
                action_df = filtered_tactic_perf[filtered_tactic_perf["recommended_action"] == action_name].sort_values(
                    ["delta_vs_baseline", "times_used"],
                    ascending=[False, False],
                )
                if action_df.empty:
                    action_cards_html.append("<div class='tb-empty'>No tactics in this bucket.</div>")
                else:
                    for _, row in action_df.head(6).iterrows():
                        action_cards_html.append(
                            f"""
                            <div class="tb-decision-card" style="--accent:{accent};">
                                <div class="tb-card-title">{row["tactic_name"]}</div>
                                <div class="tb-card-sub">{row["map"]} • {row["side"]}</div>
                                <div class="tb-card-meta">{row["confidence_badge"]} • Δ {row["delta_vs_baseline"]:+.1f}pp • WR {row["win_pct"]:.1f}%</div>
                                <div class="tb-card-reason">{row["reason"]}</div>
                            </div>
                            """,
                        )
                st.markdown(
                    f"""
                    <div class="tb-action-col {cls_name}">
                        <div class="tb-action-head">
                            <span>{action_name}</span>
                            <span class="tb-action-pill" style="color:{accent};">{action_counts.get(action_name, 0)}</span>
                        </div>
                        {''.join(action_cards_html)}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("<div class='tb-section-title'>Main tactic table</div>", unsafe_allow_html=True)
    perf_table = tactic_perf.rename(
        columns={
            "tactic_name": "Tactic",
            "map": "Map",
            "side": "Side",
            "times_used": "Uses",
            "win_pct": "Win %",
            "last_10_usage_win_pct": "Last 10",
            "usage_pct": "Usage %",
            "confidence_badge": "Confidence",
            "action_badge": "Action",
            "reason": "Reason",
        }
    )
    perf_table["Confidence"] = perf_table["Confidence"].fillna("⚪ Neutral / unproven")
    perf_table["Action"] = perf_table["Action"].fillna("🟡 Monitor")
    perf_cols = ["Tactic", "Map", "Side", "Uses", "Win %", "Last 10", "Usage %", "Confidence", "Action", "Reason"]
    st.dataframe(
        perf_table[perf_cols].sort_values(["Action", "Win %", "Uses"], ascending=[True, False, False]),
        use_container_width=True,
        hide_index=True,
    )
    st.caption("Detailed table retains full tactical logic. Chips and actions are map + side specific only.")

    with st.expander("Secondary columns", expanded=False):
        secondary_cols = [
            "Tactic",
            "Map",
            "Side",
            "Uses",
            "Win %",
            "Last 10",
            "Usage %",
            "Confidence",
            "Action",
            "Reason",
        ]
        extended = perf_table.copy()
        extended["Net rounds"] = tactic_perf["net_rounds"]
        extended["Delta vs map+side baseline"] = tactic_perf["delta_vs_baseline"]
        extended["Map+side baseline"] = tactic_perf["context_baseline_win_pct"]
        extended["vs S"] = tactic_perf["vs S tier win %"]
        extended["vs A"] = tactic_perf["vs A tier win %"]
        extended["vs B"] = tactic_perf["vs B tier win %"]
        extended["vs C"] = tactic_perf["vs C tier win %"]
        st.dataframe(
            extended[secondary_cols + ["Net rounds", "Delta vs map+side baseline", "Map+side baseline", "vs S", "vs A", "vs B", "vs C"]],
            use_container_width=True,
            hide_index=True,
        )

    st.markdown("<div class='tb-section-title'>Selected tactic summary panel</div>", unsafe_allow_html=True)
    selected_key = st.selectbox("Selected tactic summary", summary_options, key="selected_tactic_summary")
    selected_row = summary_key_df[summary_key_df["summary_key"] == selected_key].iloc[0]
    verdict = selected_row["recommended_action"]
    coach_summary_map = {
        "Keep": f"Keep: strong return across a reliable sample in {selected_row['map']} {selected_row['side']}",
        "Rework": f"Rework: heavily used in {selected_row['map']} {selected_row['side']} but underperforming local baseline",
        "Use More": f"Use More: underused but efficient within {selected_row['map']} {selected_row['side']}",
        "Monitor": f"Monitor: mixed signal in {selected_row['map']} {selected_row['side']} needs more tracking",
        "Drop": f"Drop: sustained underperformance in {selected_row['map']} {selected_row['side']}",
    }
    st.markdown(
        f"""
        <div class="tb-feature">
            <div class="panel-muted">Featured tactic insight</div>
            <div class="panel-title">{selected_row["tactic_name"]}</div>
            <div class="tb-badge-row">
                <span class="tb-chip">{selected_row["map"]}</span>
                <span class="tb-chip">{selected_row["side"]}</span>
                <span class="tb-chip">{selected_row["action_badge"]}</span>
                <span class="tb-chip">{selected_row["confidence_badge"]}</span>
            </div>
            <div style="margin-top:8px;color:#d4deef;font-size:0.88rem;"><strong>Why flagged:</strong> {selected_row.get("reason", "Monitor trend")}</div>
            <div style="margin-top:6px;color:#edf4ff;font-size:0.9rem;"><strong>Coach summary:</strong> {coach_summary_map.get(verdict, "Monitor tactical performance in this context")}</div>
            <div class="stats-grid">
                <div class="stat-chip"><div class="stat-label">Uses</div><div class="stat-value">{int(selected_row["times_used"])}</div></div>
                <div class="stat-chip"><div class="stat-label">Overall WR</div><div class="stat-value">{selected_row["win_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Net rounds</div><div class="stat-value">{int(selected_row["net_rounds"])}</div></div>
                <div class="stat-chip"><div class="stat-label">Usage share</div><div class="stat-value">{selected_row["usage_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Last 5</div><div class="stat-value">{selected_row.get("recent_form_5", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">Last 10</div><div class="stat-value">{selected_row.get("recent_form_10", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">vs S</div><div class="stat-value">{selected_row.get("vs S tier win %", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">vs C</div><div class="stat-value">{selected_row.get("vs C tier win %", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">Map+side baseline</div><div class="stat-value">{selected_row["context_baseline_win_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Delta vs local baseline</div><div class="stat-value">{selected_row["delta_vs_baseline"]:+.1f}pp</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='tb-section-title'>Opportunity swaps</div>", unsafe_allow_html=True)
    st.caption("Strict rule: only alternatives from the exact same map + side context are considered.")
    if bool(selected_row["insufficient_context_sample"]):
        st.info("Insufficient sample in this exact map+side pool to recommend alternatives.")
    else:
        same_context_pool = tactic_perf[
            (tactic_perf["map"] == selected_row["map"])
            & (tactic_perf["side"] == selected_row["side"])
            & (tactic_perf["tactic_name"] != selected_row["tactic_name"])
            & (~tactic_perf["insufficient_context_sample"])
        ].copy()
        if same_context_pool.empty:
            st.info("No alternatives available in this exact map+side context.")
        else:
            better_alts = same_context_pool[
                (same_context_pool["delta_vs_baseline"] > selected_row["delta_vs_baseline"])
                & (same_context_pool["usage_pct"] < selected_row["usage_pct"] + 2)
            ].sort_values(["delta_vs_baseline", "usage_pct"], ascending=[False, True])
            if better_alts.empty:
                st.info("No clearly better underused alternatives in this exact map+side context.")
            else:
                top_alts = better_alts.head(3)
                alt_cols = st.columns(len(top_alts))
                for idx, (_, alt_row) in enumerate(top_alts.iterrows()):
                    with alt_cols[idx]:
                        st.markdown(
                            f"""
                            <div class="tb-family-card">
                                <div class="panel-title">{alt_row["tactic_name"]}</div>
                                <div class="panel-muted">{alt_row["map"]} • {alt_row["side"]}</div>
                                <div class="tb-note">Δ baseline {alt_row["delta_vs_baseline"]:+.1f}pp • Usage {alt_row["usage_pct"]:.1f}%</div>
                                <div class="tb-note">WR {alt_row["win_pct"]:.1f}% • Uses {int(alt_row["times_used"])}</div>
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                st.dataframe(
                    better_alts[
                        ["tactic_name", "map", "side", "times_used", "win_pct", "usage_pct", "delta_vs_baseline", "recommended_action", "reason"]
                    ].rename(
                        columns={
                            "tactic_name": "Tactic",
                            "map": "Map",
                            "side": "Side",
                            "times_used": "Uses",
                            "win_pct": "Win %",
                            "usage_pct": "Usage %",
                            "delta_vs_baseline": "Delta vs local baseline",
                            "recommended_action": "Action",
                            "reason": "Reason",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

    st.markdown("<div class='tb-section-title'>Trend over time</div>", unsafe_allow_html=True)
    selected_rounds = rounds_long[
        (rounds_long["tactic_name"] == selected_row["tactic_name"])
        & (rounds_long["map"] == selected_row["map"])
        & (rounds_long["side"] == selected_row["side"])
    ].sort_values(["date", "match_id"])
    if selected_rounds.empty:
        st.markdown(
            "<div class='tb-empty'>Insufficient trend sample for this exact map + side tactic context.</div>",
            unsafe_allow_html=True,
        )
    else:
        selected_rounds = selected_rounds.assign(
            use_idx=range(1, len(selected_rounds) + 1),
            rolling_5=lambda d: (d["round_result"].gt(0).rolling(5, min_periods=1).mean() * 100).round(1),
            rolling_10=lambda d: (d["round_result"].gt(0).rolling(10, min_periods=1).mean() * 100).round(1),
        )
        insight_label = "too little sample" if len(selected_rounds) < 8 else (
            "improving" if selected_rounds["rolling_5"].iloc[-1] > selected_rounds["rolling_10"].iloc[-1] + 4 else
            "unstable" if selected_rounds["rolling_5"].std() > 18 else
            "flat"
        )
        st.caption(f"Trend insight: **{insight_label}** for this exact {selected_row['map']} {selected_row['side']} context.")
        if len(selected_rounds) < 5:
            st.markdown(
                "<div class='tb-empty'>Not enough points for a reliable trend chart yet. Continue collecting rounds in this same map + side context.</div>",
                unsafe_allow_html=True,
            )
            selected_rounds = pd.DataFrame()
        if selected_rounds.empty:
            pass
        elif go is None or make_subplots is None:
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

    st.markdown("<div class='tb-section-title'>Map + side split heatmap</div>", unsafe_allow_html=True)
    st.caption("Tabs preserve strict map context; side split is rendered independently within each map.")
    heatmap_data = tactic_perf.copy()
    if heatmap_data.empty:
        st.info("No heatmap data for current filters.")
    
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

    st.markdown("<div class='tb-section-title'>Round share vs success</div>", unsafe_allow_html=True)
    if go is None:
        _render_plotly_unavailable()
    else:
        confidence_colors = {
            "Proven good": "#31d17b",
            "Early positive signal": "#60a5fa",
            "Neutral / unproven": "#f0be4f",
            "Early negative signal": "#f59e0b",
            "Proven poor": "#ff6c7a",
        }
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
        scatter_fig.update_layout(title="Round share vs success", legend_title_text="Confidence tier")
        scatter_fig.update_xaxes(title_text="Usage rate / round share %")
        scatter_fig.update_yaxes(title_text="Win rate %")
        _apply_plotly_dark_style(scatter_fig, height=400)
        st.plotly_chart(scatter_fig, use_container_width=True)

    st.markdown("<div class='tb-section-title'>By enemy tier</div>", unsafe_allow_html=True)
    sel_tier = tier_perf[
        (tier_perf["tactic_name"] == selected_row["tactic_name"])
        & (tier_perf["map"] == selected_row["map"])
        & (tier_perf["side"] == selected_row["side"])
    ].copy()
    if sel_tier.empty:
        st.info("No tier-split data for selected tactic.")
    elif len(sel_tier) < 2:
        tier_cols = st.columns(len(sel_tier))
        for idx, (_, row) in enumerate(sel_tier.iterrows()):
            with tier_cols[idx]:
                st.markdown(
                    f"""
                    <div class="tb-family-card">
                        <div class="panel-title">Tier {row["tier"]}</div>
                        <div class="tb-note">WR {row["tier_win_pct"]:.1f}%</div>
                        <div class="tb-note">Record {int(row["wins"])}-{int(row["losses"])}</div>
                        <div class="tb-note">Uses {int(row["tier_uses"])}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    else:
        sel_tier["tier_adjusted_score"] = sel_tier.apply(
            lambda r: compute_tier_adjusted_tactic_score(
                tier=r.get("tier"),
                win_pct=float(r.get("tier_win_pct", 0.0)),
                wins=float(r.get("wins", 0.0)),
                losses=float(r.get("losses", 0.0)),
            ),
            axis=1,
        )
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
                    hovertemplate="Tier: %{x}<br>Wins: %{customdata[0]}<br>Losses: %{customdata[1]}<br>Win %: %{y:.1f}<br>Tier-adjusted score: %{customdata[2]:.1f}<extra></extra>",
                    showlegend=False,
                )
            )
            tier_chart.update_layout(title="By enemy tier")
            tier_chart.update_xaxes(title_text="Tier", categoryorder="array", categoryarray=["S", "A", "B", "C"])
            tier_chart.update_yaxes(title_text="Win rate %")
            _apply_plotly_dark_style(tier_chart, height=320)
            st.plotly_chart(tier_chart, use_container_width=True)
        _, tier_context_note = compute_quality_of_results_component(sel_tier, total_uses=float(sel_tier["tier_uses"].sum()))
        if tier_context_note:
            st.caption(tier_context_note)

    st.markdown("<div class='tb-section-title'>Family/category summaries</div>", unsafe_allow_html=True)
    family_summary = (
        tactic_perf.groupby(["family", "map", "side"], as_index=False)
        .agg(
            total_rounds_played=("times_used", "sum"),
            total_wins=("wins", "sum"),
            total_losses=("losses", "sum"),
            most_used_tactic=("tactic_name", lambda s: s.value_counts().index[0] if not s.empty else None),
        )
        .assign(total_win_pct=lambda d: (d["total_wins"] / (d["total_wins"] + d["total_losses"]).clip(lower=1) * 100).round(1))
    )
    max_cards = min(len(family_summary), 4)
    family_cards = st.columns(max(max_cards, 1))
    for idx, fam_row in family_summary.head(max_cards).iterrows():
        with family_cards[idx % max_cards]:
            family_class = str(fam_row["family"]).strip().lower()
            if family_class not in {"pistol", "eco", "standard"}:
                family_class = "standard"
            st.markdown(
                f"""
                <div class="tb-family-card {family_class}">
                    <div class="panel-title">{fam_row["family"]}</div>
                    <div class="panel-muted">{fam_row["map"]} • {fam_row["side"]}</div>
                    <div class="tb-note">Rounds {int(fam_row["total_rounds_played"])} • WR {float(fam_row["total_win_pct"]):.1f}%</div>
                    <div class="tb-note">Most used: {fam_row["most_used_tactic"]}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    def _render_family_breakdown(section_title: str, family_name: str, rounds_label: str) -> None:
        with st.expander(section_title, expanded=False):
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

            st.caption("Map+side context split (no cross-context fallback).")
            context_summary = (
                family_df.groupby(["map", "side"], as_index=False)
                .agg(rounds=("times_used", "sum"), wins=("wins", "sum"), losses=("losses", "sum"))
                .assign(win_rate=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
            )
            st.dataframe(context_summary, use_container_width=True, hide_index=True)

            st.dataframe(
                family_df[["tactic_name", "map", "side", "times_used", "win_pct", "usage_pct", "recommended_action", "reason"]]
                .sort_values(["map", "side", "win_pct"], ascending=[True, True, False]),
                use_container_width=True,
                hide_index=True,
            )

    _render_family_breakdown("Pistol breakdown", "Pistol", "Pistol rounds")
    _render_family_breakdown("Eco breakdown", "Eco", "Eco rounds")
    _render_family_breakdown("Standard rounds section", "Standard", "Standard rounds")

    st.markdown("<div class='tb-section-title'>Match context drilldown</div>", unsafe_allow_html=True)
    drilldown = df[
        (df["tactic_name"] == selected_row["tactic_name"])
        & (df["map"] == selected_row["map"])
        & (df["side"] == selected_row["side"])
    ].copy()
    drill_cols = ["match_id", "opponent_team", "tier", "map", "side", "wins", "losses", competition_source_col, "date"]
    drill_df = drilldown[drill_cols].rename(columns={competition_source_col: "competition"})
    st.dataframe(drill_df.sort_values("date", ascending=False), use_container_width=True, hide_index=True)


def safe_select_columns(
    df: pd.DataFrame,
    desired_columns: list[str],
    fill_defaults: dict[str, object] | None = None,
) -> pd.DataFrame:
    """Return a safe column subset without raising when columns are missing."""
    safe_df = df.copy()
    defaults = fill_defaults or {}
    for column, default_value in defaults.items():
        if column not in safe_df.columns:
            safe_df[column] = default_value
    existing_columns = [column for column in desired_columns if column in safe_df.columns]
    return safe_df[existing_columns]


def resolve_match_opponent_tier(row: pd.Series, latest_tier_lookup: dict[str, str | None]) -> str:
    raw_tier = row.get("tier", pd.NA)
    if raw_tier is not None and not pd.isna(raw_tier):
        clean = str(raw_tier).strip().upper()[:1]
        if clean in {"S", "A", "B", "C"}:
            return clean
    fallback = latest_tier_lookup.get(str(row.get("opponent_key", "")), None)
    if fallback is not None and str(fallback).strip():
        return str(fallback).strip().upper()[:1]
    return "—"


def get_previous_matchups_for_row(history_df: pd.DataFrame, row: pd.Series) -> pd.DataFrame:
    if history_df.empty:
        return history_df.copy()
    opponent_key = str(row.get("opponent_key", "")).strip()
    match_id = str(row.get("match_id", "")).strip()
    row_date = pd.to_datetime(row.get("date"), errors="coerce")
    previous = history_df[history_df["opponent_key"] == opponent_key].copy()
    previous = previous[previous["match_id"].astype(str) != match_id]
    if pd.notna(row_date):
        previous = previous[pd.to_datetime(previous["date"], errors="coerce") < row_date]
    return previous.sort_values("date", ascending=False)


def build_matchup_comparison_note(current_row: pd.Series, previous_matchups: pd.DataFrame) -> str:
    if previous_matchups.empty:
        return "First meeting"
    prev_wins = int((previous_matchups["match_result"] == "Win").sum())
    prev_losses = int((previous_matchups["match_result"] == "Loss").sum())
    meetings = int(previous_matchups["match_id"].nunique())
    current_rd = int(current_row.get("round_diff", 0))
    latest_prev = previous_matchups.sort_values("date", ascending=False).head(1).iloc[0]
    prev_rd = int(latest_prev.get("round_diff", 0))
    current_result = str(current_row.get("match_result", ""))
    prev_result = str(latest_prev.get("match_result", ""))

    if current_result == "Win" and prev_wins == 0:
        return f"First win over this opponent • came in {prev_wins}W-{prev_losses}L"
    if current_result == "Loss" and prev_losses >= 1:
        return f"Previous meetings: {meetings} • came in {prev_wins}W-{prev_losses}L"
    if current_result == prev_result and current_result in {"Win", "Loss"}:
        streak_size = 1
        for _, prev in previous_matchups.sort_values("date", ascending=False).iterrows():
            if str(prev.get("match_result", "")) == current_result:
                streak_size += 1
            else:
                break
        if streak_size >= 2:
            return f"{streak_size}{'nd' if streak_size == 2 else 'rd' if streak_size == 3 else 'th'} straight {current_result.lower()} vs this opponent"
    if current_rd > prev_rd:
        return f"Improved from previous meeting ({prev_rd:+d} rounds → {current_rd:+d})"
    if current_rd < prev_rd:
        return f"Worse than previous meeting ({prev_rd:+d} rounds → {current_rd:+d})"
    return f"Previous meetings: {meetings} • came in {prev_wins}W-{prev_losses}L"


def build_opponent_history_summary(current_row: pd.Series, history_df: pd.DataFrame) -> str:
    previous = get_previous_matchups_for_row(history_df, current_row)
    return build_matchup_comparison_note(current_row, previous)


def build_tournament_match_rows(
    filtered_df: pd.DataFrame,
    history_df: pd.DataFrame,
) -> pd.DataFrame:
    if filtered_df.empty:
        return pd.DataFrame()
    latest_tier = resolve_latest_opponent_tier(history_df)
    tier_lookup = latest_tier.set_index("opponent_key")["latest_tier"].to_dict() if not latest_tier.empty else {}

    rows = filtered_df.sort_values(["date", "match_id"]).copy()
    rows["opponent_tier_resolved"] = rows.apply(lambda row: resolve_match_opponent_tier(row, tier_lookup), axis=1)
    rows["comparison_note"] = rows.apply(lambda row: build_opponent_history_summary(row, history_df), axis=1)
    rows["tier_strength"] = rows["opponent_tier_resolved"].map({"S": 4, "A": 3, "B": 2, "C": 1}).fillna(0)
    return rows


def build_tournament_summary_df(match_rows: pd.DataFrame) -> pd.DataFrame:
    if match_rows.empty:
        return pd.DataFrame()
    summary = (
        match_rows.groupby(["competition_key", "competition_display", "season_resolved"], as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            draws=("match_result", lambda s: int((s == "Draw").sum())),
            round_diff=("round_diff", "sum"),
            avg_tier_strength=("tier_strength", "mean"),
            strongest_beaten=("opponent_tier_resolved", lambda s: "S" if "S" in s.values else ("A" if "A" in s.values else ("B" if "B" in s.values else ("C" if "C" in s.values else "—")))),
            lowest_tier_loss=("opponent_tier_resolved", lambda s: "C" if "C" in s.values else ("B" if "B" in s.values else ("A" if "A" in s.values else ("S" if "S" in s.values else "—")))),
            most_common_map=("map", lambda s: s.dropna().astype(str).mode().iloc[0] if not s.dropna().empty else "—"),
            latest_date=("date", "max"),
        )
    )
    summary["win_rate_pct"] = (summary["wins"] / (summary["wins"] + summary["losses"]).clip(lower=1) * 100).round(1)
    summary["record"] = summary["wins"].astype(str) + "-" + summary["losses"].astype(str) + "-" + summary["draws"].astype(str)
    summary["avg_tier_label"] = summary["avg_tier_strength"].apply(
        lambda v: "S/A-heavy" if v >= 3.3 else ("Balanced A/B" if v >= 2.4 else ("Mostly B/C" if v >= 1.5 else "C-heavy"))
    )
    summary["tier_mix"] = summary["competition_key"].map(
        match_rows.groupby("competition_key")["opponent_tier_resolved"]
        .apply(lambda s: " • ".join([f"{tier}:{int((s == tier).sum())}" for tier in ["S", "A", "B", "C"] if int((s == tier).sum()) > 0]) or "No tier data")
        .to_dict()
    )
    summary["insight"] = summary.apply(
        lambda row: (
            "Strong run with positive margins vs quality opposition"
            if float(row["win_rate_pct"]) >= 60 and int(row["round_diff"]) > 0 and float(row["avg_tier_strength"]) >= 2.7
            else "Good record, but narrow round margins"
            if float(row["win_rate_pct"]) >= 60 and int(row["round_diff"]) <= 3
            else "Competitive losses to stronger field"
            if float(row["avg_tier_strength"]) >= 3 and float(row["win_rate_pct"]) < 50
            else "Mixed event with inconsistent conversion"
        ),
        axis=1,
    )
    return summary.sort_values(["latest_date", "wins", "round_diff"], ascending=[False, False, False])


def build_tournament_overview_metrics(summary_df: pd.DataFrame, match_rows: pd.DataFrame) -> dict[str, str]:
    if summary_df.empty or match_rows.empty:
        return {}
    total_wins = int((match_rows["match_result"] == "Win").sum())
    total_losses = int((match_rows["match_result"] == "Loss").sum())
    tier_mix = " • ".join(
        [f"{tier}:{int((match_rows['opponent_tier_resolved'] == tier).sum())}" for tier in ["S", "A", "B", "C"] if int((match_rows["opponent_tier_resolved"] == tier).sum()) > 0]
    ) or "No tier data"
    best_event = summary_df.sort_values(["win_rate_pct", "round_diff", "matches"], ascending=[False, False, False]).head(1)
    toughest = summary_df.sort_values(["avg_tier_strength", "matches"], ascending=[False, False]).head(1)
    return {
        "Tournaments": str(int(summary_df["competition_key"].nunique())),
        "Matches": str(int(match_rows["match_id"].nunique())),
        "Record": f"{total_wins}W-{total_losses}L",
        "Tier mix faced": tier_mix,
        "Best tournament": (
            f"{best_event.iloc[0]['competition_display']} ({best_event.iloc[0]['win_rate_pct']:.1f}% WR)"
            if not best_event.empty
            else "—"
        ),
        "Toughest field": (
            f"{toughest.iloc[0]['competition_display']} ({toughest.iloc[0]['avg_tier_label']})"
            if not toughest.empty
            else "—"
        ),
    }


def render_tournament_summary_page(match_rows: pd.DataFrame, summary_df: pd.DataFrame, image_index: dict[str, dict[str, Path]]) -> None:
    st.markdown("<div class='tb-section-title'>Tournament Summary</div>", unsafe_allow_html=True)
    st.caption("Campaign-by-campaign results, opponent quality, and matchup history.")
    overview = build_tournament_overview_metrics(summary_df, match_rows)
    if not overview:
        st.info("No matches available for this filter setup.")
        return
    overview_html = "".join(
        f"<div class='kpi-card'><div class='kpi-label'>{html.escape(label)}</div><div class='kpi-value'>{html.escape(value)}</div></div>"
        for label, value in overview.items()
    )
    st.markdown(
        f"<div class='panel-card'><div class='panel-muted'>Tournament overview strip</div><div class='kpi-grid'>{overview_html}</div></div>",
        unsafe_allow_html=True,
    )

    for _, tournament in summary_df.iterrows():
        competition_key = tournament["competition_key"]
        block_df = match_rows[match_rows["competition_key"] == competition_key].sort_values("date", ascending=False).copy()
        if block_df.empty:
            continue
        logo_uri = _competition_logo_uri(image_index, tournament["competition_display"])
        logo_html = f"<img class='rank-logo' src='{logo_uri}' alt='competition logo'>" if logo_uri else "<span class='rank-logo'></span>"
        header_html = (
            f"<div class='panel-card'><div class='rank-cell-main'>{logo_html}"
            f"<span class='panel-title'>{html.escape(str(tournament['competition_display']))}</span></div>"
            f"<div class='panel-muted'>{html.escape(str(tournament.get('season_resolved', 'Unknown season')))} • "
            f"Record {html.escape(str(tournament['record']))} • WR {float(tournament['win_rate_pct']):.1f}% • RD {int(tournament['round_diff']):+d}</div>"
            f"<div style='display:flex;flex-wrap:wrap;gap:8px;margin-top:8px;'>"
            f"<span class='vs-pill'>Matches {int(tournament['matches'])}</span>"
            f"<span class='vs-pill'>Tier mix {html.escape(str(tournament['tier_mix']))}</span>"
            f"<span class='vs-pill'>Avg field {html.escape(str(tournament['avg_tier_label']))}</span>"
            f"<span class='vs-pill'>Most common map {html.escape(str(tournament['most_common_map']))}</span>"
            f"</div><div class='tb-note' style='margin-top:8px;'>{html.escape(str(tournament['insight']))}</div></div>"
        )
        _render_html(header_html)
        match_cards = []
        for _, row in block_df.head(8).iterrows():
            result = str(row.get("match_result", "Draw")).lower()
            result_class = "win" if result == "win" else ("loss" if result == "loss" else "draw")
            date_text = pd.to_datetime(row.get("date"), errors="coerce")
            date_label = date_text.strftime("%Y-%m-%d") if pd.notna(date_text) else "Unknown date"
            comparison = str(row.get("comparison_note", ""))
            match_cards.append(
                (
                    f"<article class='match-card {result_class}'>"
                    f"<div class='panel-muted'>{date_label}</div>"
                    f"<div class='panel-title' style='font-size:0.95rem;'>{html.escape(str(row.get('opponent_raw', 'Unknown opponent')))}</div>"
                    "<div style='display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;'>"
                    f"<span class='vs-pill'>Tier {html.escape(str(row.get('opponent_tier_resolved', '—')))}</span>"
                    f"<span class='vs-pill'>Map {html.escape(str(row.get('map', '—')))}</span>"
                    f"<span class='vs-pill {'vs-pill-good' if result == 'win' else 'vs-pill-bad' if result == 'loss' else 'vs-pill-mid'}'>{html.escape(str(row.get('match_result', 'Draw')))} {int(row.get('round_wins', 0))}-{int(row.get('round_losses', 0))}</span>"
                    f"<span class='vs-pill {'vs-pill-good' if int(row.get('round_diff', 0)) >= 0 else 'vs-pill-bad'}'>RD {int(row.get('round_diff', 0)):+d}</span>"
                    "</div>"
                    f"<div class='mini-note'>{html.escape(comparison)}</div>"
                    "</article>"
                )
            )
        _render_html(
            f"<div class='panel-card'><div class='panel-muted'>Recent results</div><section class='match-card-grid'>{''.join(match_cards)}</section></div>"
        )
        with st.expander(f"View full match table: {tournament['competition_display']}", expanded=False):
            table = block_df.copy()
            table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.strftime("%Y-%m-%d")
            table["result"] = table["match_result"].map({"Win": "🟢 Win", "Loss": "🔴 Loss", "Draw": "🟡 Draw"}).fillna("⚪")
            table["tier_badge"] = table["opponent_tier_resolved"].apply(lambda v: f"Tier {v}" if str(v) != "—" else "Tier —")
            st.dataframe(
                table[
                    [
                        "date",
                        "opponent_raw",
                        "tier_badge",
                        "map",
                        "result",
                        "round_wins",
                        "round_losses",
                        "round_diff",
                        "comparison_note",
                    ]
                ].rename(
                    columns={
                        "opponent_raw": "Opponent",
                        "map": "Map",
                        "round_wins": "RW",
                        "round_losses": "RL",
                        "round_diff": "RD",
                        "comparison_note": "Comparison note",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )


def _tournament_summary_page(tactics_df: pd.DataFrame, player_df: pd.DataFrame, competition_source_col: str) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="tournament_summary",
        subtitle="Campaign-by-campaign results, opponent quality, and matchup history.",
    )
    team_df = tactics_df[tactics_df["my_team"].astype(str).str.contains("ⓜ", regex=False, na=False)].copy()
    if team_df.empty:
        st.warning("No Medisports tactics data found.")
        return
    if "tier" not in team_df.columns or team_df["tier"].isna().all():
        tier_lookup = (
            player_df.groupby("match_id", as_index=False)["tier"]
            .agg(lambda s: s.dropna().iloc[0] if not s.dropna().empty else pd.NA)
        )
        team_df = team_df.merge(tier_lookup, on="match_id", how="left")
    base_df = build_medisports_vs_base_df(team_df, competition_source_col)
    if base_df.empty:
        st.warning("No tournament summary data found.")
        return

    all_seasons = sorted(base_df["season_num_resolved"].dropna().astype(int).unique().tolist(), reverse=True)
    latest_season = all_seasons[0] if all_seasons else None
    season_options = ["Lifetime"] + [f"S{season}" for season in all_seasons]
    default_season = f"S{latest_season}" if latest_season is not None else "Lifetime"

    c1, c2, c3, c4, c5, c6 = st.columns([1.0, 1.7, 1.0, 0.9, 0.9, 1.4])
    with c1:
        selected_season = st.selectbox(
            "Season",
            season_options,
            index=season_options.index(default_season) if default_season in season_options else 0,
            key="tournament_summary_season",
        )
    with c2:
        grouped_competitions = st.toggle("Grouped competitions", value=False, key="tournament_summary_grouped")
        comp_col = "competition_grouped" if grouped_competitions else "competition_raw"
        competition_options = sorted(base_df[comp_col].dropna().astype(str).unique().tolist())
        selected_competitions = st.multiselect(
            "Competition / tournament",
            competition_options,
            default=[],
            key="tournament_summary_competitions",
        )
    with c3:
        min_matches = int(st.slider("Minimum matches", 1, 8, 1, key="tournament_summary_min_matches"))
    with c4:
        tier_filter = st.multiselect("Tier filter", ["S", "A", "B", "C"], default=[], key="tournament_summary_tiers")
    with c5:
        tier_mode = st.selectbox("Tier mode", ["Any", "Only selected"], index=0, key="tournament_summary_tier_mode")
    with c6:
        min_date = pd.to_datetime(base_df["date"], errors="coerce").min()
        max_date = pd.to_datetime(base_df["date"], errors="coerce").max()
        date_range = st.date_input(
            "Date range",
            value=(min_date.date(), max_date.date()) if pd.notna(min_date) and pd.notna(max_date) else None,
            min_value=min_date.date() if pd.notna(min_date) else None,
            max_value=max_date.date() if pd.notna(max_date) else None,
            key="tournament_summary_date_range",
        )

    filtered = base_df.copy()
    filtered["competition_display"] = filtered[comp_col]
    if selected_season != "Lifetime":
        filtered = filtered[filtered["season_resolved"] == selected_season].copy()
    if selected_competitions:
        selected_keys = {normalize_competition_label(name) for name in selected_competitions}
        filtered = filtered[filtered["competition_key"].isin(selected_keys)].copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0], errors="coerce")
        end_date = pd.to_datetime(date_range[1], errors="coerce")
        filtered = filtered[pd.to_datetime(filtered["date"], errors="coerce").between(start_date, end_date, inclusive="both")]

    history_df = base_df.copy()
    history_df["competition_display"] = history_df[comp_col]
    match_rows = build_tournament_match_rows(filtered, history_df)
    if tier_filter:
        if tier_mode == "Only selected":
            match_rows = match_rows[match_rows["opponent_tier_resolved"].isin(tier_filter)].copy()
    summary_df = build_tournament_summary_df(match_rows)
    summary_df = summary_df[summary_df["matches"] >= min_matches].copy()
    if summary_df.empty:
        st.info("No tournaments meet the current filters.")
        return
    image_index = _build_image_index()
    render_tournament_summary_page(match_rows, summary_df, image_index)


def _opponent_review_page(tactics_df: pd.DataFrame, player_df: pd.DataFrame, competition_source_col: str) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="opponent_review",
        subtitle="Single-team dossier: history, map split, trendline, and latest known opponent tier.",
    )
    st.markdown("<div class='tb-section-title'>Opponent Review</div>", unsafe_allow_html=True)
    st.caption("Focus one opponent across all meetings and compare trajectory over time.")

    team_df = tactics_df[tactics_df["my_team"].astype(str).str.contains("ⓜ", regex=False, na=False)].copy()
    if team_df.empty:
        st.warning("No Medisports tactics data found.")
        return
    if "tier" not in team_df.columns or team_df["tier"].isna().all():
        tier_lookup = player_df.groupby("match_id", as_index=False)["tier"].agg(lambda s: s.dropna().iloc[0] if not s.dropna().empty else pd.NA)
        team_df = team_df.merge(tier_lookup, on="match_id", how="left")
    base_df = build_medisports_vs_base_df(team_df, competition_source_col)
    if base_df.empty:
        st.info("No opponent review data available.")
        return

    all_seasons = sorted(base_df["season_num_resolved"].dropna().astype(int).unique().tolist(), reverse=True)
    season_options = ["Lifetime"] + [f"S{season}" for season in all_seasons]
    selected_season = st.selectbox("Season", season_options, index=0, key="opponent_review_season")
    grouped = st.toggle("Grouped competitions", value=True, key="opponent_review_grouped")
    comp_col = "competition_grouped" if grouped else "competition_raw"
    opponent_options = sorted(base_df["opponent_raw"].dropna().astype(str).unique().tolist())
    selected_opp = st.selectbox("Opponent/team", opponent_options, index=0, key="opponent_review_team")
    map_filter = st.multiselect("Map filter", sorted(base_df["map"].dropna().astype(str).unique().tolist()), default=[], key="opponent_review_map")

    min_date = pd.to_datetime(base_df["date"], errors="coerce").min()
    max_date = pd.to_datetime(base_df["date"], errors="coerce").max()
    date_range = st.date_input(
        "Date range",
        value=(min_date.date(), max_date.date()) if pd.notna(min_date) and pd.notna(max_date) else None,
        min_value=min_date.date() if pd.notna(min_date) else None,
        max_value=max_date.date() if pd.notna(max_date) else None,
        key="opponent_review_date_range",
    )

    filtered = base_df.copy()
    filtered["competition_display"] = filtered[comp_col]
    if selected_season != "Lifetime":
        filtered = filtered[filtered["season_resolved"] == selected_season].copy()
    filtered = filtered[filtered["opponent_raw"] == selected_opp].copy()
    if map_filter:
        filtered = filtered[filtered["map"].isin(map_filter)].copy()
    if isinstance(date_range, tuple) and len(date_range) == 2:
        start_date = pd.to_datetime(date_range[0], errors="coerce")
        end_date = pd.to_datetime(date_range[1], errors="coerce")
        filtered = filtered[pd.to_datetime(filtered["date"], errors="coerce").between(start_date, end_date, inclusive="both")]

    if filtered.empty:
        st.info("No meetings found for this opponent with the current filters.")
        return

    filtered = build_tournament_match_rows(filtered, base_df).sort_values("date")
    wins = int((filtered["match_result"] == "Win").sum())
    losses = int((filtered["match_result"] == "Loss").sum())
    draws = int((filtered["match_result"] == "Draw").sum())
    latest_tier = str(filtered.sort_values("date", ascending=False)["opponent_tier_resolved"].dropna().astype(str).head(1).iloc[0]) if not filtered["opponent_tier_resolved"].dropna().empty else "—"
    kpi_html = "".join(
        [
            f"<div class='kpi-card'><div class='kpi-label'>Opponent</div><div class='kpi-value'>{html.escape(selected_opp)}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Record vs them</div><div class='kpi-value'>{wins}W-{losses}L-{draws}D</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Meetings</div><div class='kpi-value'>{int(filtered['match_id'].nunique())}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Round differential</div><div class='kpi-value'>{int(filtered['round_diff'].sum()):+d}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Latest known tier</div><div class='kpi-value'>Tier {html.escape(latest_tier)}</div></div>",
            f"<div class='kpi-card'><div class='kpi-label'>Tournaments met</div><div class='kpi-value'>{int(filtered['competition_key'].nunique())}</div></div>",
        ]
    )
    _render_html(f"<div class='panel-card'><div class='kpi-grid'>{kpi_html}</div></div>")

    recent_cards = []
    for _, row in filtered.sort_values("date", ascending=False).head(6).iterrows():
        outcome = str(row["match_result"]).lower()
        row_date = pd.to_datetime(row["date"], errors="coerce")
        recent_cards.append(
            (
                f"<article class='match-card {outcome}'>"
                f"<div class='panel-muted'>{row_date.strftime('%Y-%m-%d') if pd.notna(row_date) else 'Unknown date'}</div>"
                f"<div class='panel-title' style='font-size:0.95rem;'>{html.escape(str(row['competition_display']))}</div>"
                "<div style='display:flex;gap:6px;flex-wrap:wrap;margin-top:6px;'>"
                f"<span class='vs-pill'>Map {html.escape(str(row['map']))}</span>"
                f"<span class='vs-pill {'vs-pill-good' if outcome=='win' else 'vs-pill-bad' if outcome=='loss' else 'vs-pill-mid'}'>{html.escape(str(row['match_result']))} {int(row['round_wins'])}-{int(row['round_losses'])}</span>"
                "</div>"
                f"<div class='mini-note'>{html.escape(str(row.get('comparison_note', '')))}</div>"
                "</article>"
            )
        )
    _render_html(
        f"<div class='panel-card'><div class='panel-muted'>Recent meetings</div><section class='match-card-grid'>{''.join(recent_cards)}</section></div>"
    )

    map_breakdown = (
        filtered.groupby("map", as_index=False)
        .agg(matches=("match_id", "nunique"), wins=("match_result", lambda s: int((s == "Win").sum())), losses=("match_result", lambda s: int((s == "Loss").sum())), round_diff=("round_diff", "sum"))
        .assign(record=lambda d: d["wins"].astype(str) + "-" + d["losses"].astype(str))
        .sort_values(["matches", "round_diff"], ascending=[False, False])
    )
    left_col, right_col = st.columns(2)
    with left_col:
        st.markdown("#### Map breakdown vs selected opponent")
        st.dataframe(map_breakdown.rename(columns={"map": "Map", "matches": "Matches", "record": "Record", "round_diff": "RD"})[["Map", "Matches", "Record", "RD"]], hide_index=True, use_container_width=True)
    with right_col:
        st.markdown("#### Round differential trend")
        trend = filtered.sort_values("date").copy()
        trend["meeting"] = range(1, len(trend) + 1)
        if go is None:
            _render_plotly_unavailable()
        else:
            trend_fig = go.Figure(
                go.Scatter(
                    x=trend["meeting"],
                    y=trend["round_diff"],
                    mode="lines+markers",
                    marker=dict(size=8, color=["#44c06f" if v >= 0 else "#e85c6b" for v in trend["round_diff"]]),
                    text=trend["map"],
                    customdata=trend[["competition_display", "match_result"]],
                    hovertemplate="Meeting %{x}<br>%{customdata[0]}<br>Result %{customdata[1]}<br>RD %{y:+d}<extra></extra>",
                )
            )
            trend_fig.update_xaxes(title_text="Meeting #")
            trend_fig.update_yaxes(title_text="Round differential")
            _apply_plotly_dark_style(trend_fig, height=320, margin=dict(l=64, r=20, t=24, b=48))
            st.plotly_chart(trend_fig, use_container_width=True)

    st.markdown("#### Tournament contexts vs selected opponent")
    t_context = (
        filtered.groupby("competition_display", as_index=False)
        .agg(matches=("match_id", "nunique"), wins=("match_result", lambda s: int((s == "Win").sum())), losses=("match_result", lambda s: int((s == "Loss").sum())), round_diff=("round_diff", "sum"))
        .assign(record=lambda d: d["wins"].astype(str) + "-" + d["losses"].astype(str), win_rate=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
        .sort_values(["matches", "round_diff"], ascending=[False, False])
    )
    st.dataframe(
        t_context.rename(columns={"competition_display": "Tournament", "matches": "Matches", "record": "Record", "win_rate": "WR %", "round_diff": "RD"})[
            ["Tournament", "Matches", "Record", "WR %", "RD"]
        ],
        hide_index=True,
        use_container_width=True,
    )
    with st.expander("View full meeting table", expanded=False):
        table = filtered.sort_values("date", ascending=False).copy()
        table["date"] = pd.to_datetime(table["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        st.dataframe(
            table.rename(columns={"date": "Date", "competition_display": "Tournament", "map": "Map", "match_result": "Result", "round_wins": "RW", "round_losses": "RL", "round_diff": "RD", "comparison_note": "Comparison note"})[
                ["Date", "Tournament", "Map", "Result", "RW", "RL", "RD", "Comparison note"]
            ],
            hide_index=True,
            use_container_width=True,
        )


def _tactical_set_recommendations(tactics_df: pd.DataFrame, player_df: pd.DataFrame, competition_source_col: str) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="tactical_set",
        subtitle="Compact recommendation planner for map + side specific active tactic pools.",
    )

    st.markdown("<div class='tb-section-title'>Tactical Set Recommendations</div>", unsafe_allow_html=True)
    st.caption(
        "Build a compact 5–7 tactic pool for one exact map + side context. No cross-map or cross-side transfers are used."
    )

    tier_lookup = (
        player_df.groupby("match_id", as_index=False)["tier"]
        .agg(lambda s: s.dropna().iloc[0] if not s.dropna().empty else None)
    )
    df = tactics_df.merge(tier_lookup, on="match_id", how="left")
    df = df[df["date"].notna()].copy()
    df = df[(df["wins"].fillna(0) + df["losses"].fillna(0)) > 0]
    if df.empty:
        st.warning("No tactic data available.")
        return

    latest_season = detect_latest_season(df, competition_source_col)
    all_seasons = sorted(df[competition_source_col].apply(extract_season_number).dropna().astype(int).unique().tolist(), reverse=True)
    season_options = ["Lifetime"] + [f"S{season}" for season in all_seasons]
    default_season = f"S{latest_season}" if latest_season is not None else "Lifetime"

    maps = sorted(df["map"].dropna().astype(str).unique().tolist())
    sides = sorted(df["side"].dropna().astype(str).unique().tolist())
    if not maps or not sides:
        st.warning("Missing map/side data needed for tactical set recommendations.")
        return

    filter_cols = st.columns(6)
    with filter_cols[0]:
        selected_season = st.selectbox("Season", season_options, index=season_options.index(default_season) if default_season in season_options else 0, key="tsr_season")
    with filter_cols[1]:
        selected_map = st.selectbox("Map", maps, key="tsr_map")
    with filter_cols[2]:
        selected_side = st.selectbox("Side", sides, key="tsr_side")
    with filter_cols[3]:
        min_sample = st.slider("Minimum sample", 1, 20, 3, key="tsr_min_sample")
    with filter_cols[4]:
        confidence_filter = st.selectbox("Confidence floor", ["Any", "Early positive signal", "Proven good"], key="tsr_conf_floor")
    with filter_cols[5]:
        prefer_coverage = st.toggle("Prefer wider coverage", value=True, key="tsr_coverage")
        prefer_proven = st.toggle("Prefer proven sample", value=True, key="tsr_proven")

    df = apply_season_filter(df, selected_season, competition_source_col)
    context_df = df[(df["map"] == selected_map) & (df["side"] == selected_side)].copy()
    if context_df.empty:
        st.info("No rounds found in this exact map + side context for the selected filters.")
        return

    map_side_totals = (
        context_df.groupby(["map", "side"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            total_map_side_rounds=lambda d: d["wins"] + d["losses"],
            context_baseline_win_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
        )
    )
    tactic_perf = (
        context_df.groupby(["tactic_name", "map", "side"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            times_used=lambda d: d["wins"] + d["losses"],
            win_pct=lambda d: (d["wins"] / d["times_used"].clip(lower=1) * 100).round(1),
            net_rounds=lambda d: d["wins"] - d["losses"],
        )
        .merge(map_side_totals[["map", "side", "total_map_side_rounds", "context_baseline_win_pct"]], on=["map", "side"], how="left")
    )
    tactic_perf["usage_pct"] = (tactic_perf["times_used"] / tactic_perf["total_map_side_rounds"].clip(lower=1) * 100).round(1)
    tactic_perf["delta_vs_baseline"] = (tactic_perf["win_pct"] - tactic_perf["context_baseline_win_pct"]).round(1)
    tactic_perf["context_usage_avg"] = tactic_perf["usage_pct"].mean().round(1)

    tier_perf = (
        context_df.groupby(["tactic_name", "map", "side", "tier"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            tier_uses=lambda d: d["wins"] + d["losses"],
            tier_win_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
        )
    )
    tier_perf["tier"] = tier_perf["tier"].astype(str).str.upper().str.strip()
    tier_perf = tier_perf[tier_perf["tier"].isin(["S", "A", "B", "C"])].copy()

    quality_records: list[dict[str, object]] = []
    if not tier_perf.empty:
        for (tactic_name, map_name, side_name), group in tier_perf.groupby(["tactic_name", "map", "side"], as_index=False):
            total_uses = float(group["tier_uses"].sum())
            quality_component, quality_note = compute_quality_of_results_component(group, total_uses=total_uses)
            weighted_strength = float((group["tier_uses"] * group["tier"].map(compute_tier_strength_weight).fillna(1.0)).sum() / max(total_uses, 1.0))
            s_rows = group[group["tier"] == "S"]
            s_uses = float(s_rows["tier_uses"].sum()) if not s_rows.empty else 0.0
            s_win_pct = float((s_rows["wins"].sum() / max(s_uses, 1.0)) * 100.0) if s_uses > 0 else 0.0
            s_evidence = np.sqrt(s_uses) / (np.sqrt(s_uses) + 2.6) if s_uses > 0 else 0.0
            s_delta = s_win_pct - _compute_tier_expected_win_pct("S") if s_uses > 0 else 0.0
            tier_adjusted_score_component = _clamp(s_delta * 0.16 * s_evidence, -4.5, 7.5)
            quality_records.append(
                {
                    "tactic_name": tactic_name,
                    "map": map_name,
                    "side": side_name,
                    "quality_of_results_component": round(float(quality_component), 2),
                    "tier_adjusted_score_component": round(float(tier_adjusted_score_component), 2),
                    "tier_weighted_strength": round(weighted_strength, 2),
                    "tier_weighting_note": quality_note,
                }
            )
    quality_df = pd.DataFrame(quality_records)
    if not quality_df.empty:
        tactic_perf = tactic_perf.merge(quality_df, on=["tactic_name", "map", "side"], how="left")
    for col, fallback in (
        ("quality_of_results_component", 0.0),
        ("tier_adjusted_score_component", 0.0),
        ("tier_weighted_strength", 1.0),
        ("tier_weighting_note", ""),
    ):
        if col not in tactic_perf.columns:
            tactic_perf[col] = fallback
        tactic_perf[col] = tactic_perf[col].fillna(fallback)

    tier_summary = compute_tactic_vs_tier_summary(context_df, min_tier_sample=max(2, min_sample))
    if not tier_summary.empty:
        tactic_perf = tactic_perf.merge(tier_summary, on=["tactic_name", "map", "side"], how="left")
    for tier_col in ("vs_s_text", "vs_a_text", "vs_b_text", "vs_c_text"):
        if tier_col not in tactic_perf.columns:
            tactic_perf[tier_col] = "n/a"
        tactic_perf[tier_col] = tactic_perf[tier_col].fillna("n/a")

    round_rows: list[dict[str, object]] = []
    for row in context_df.sort_values(["date", "match_id", "tactic_name"]).itertuples(index=False):
        row_dict = row._asdict()
        for _ in range(int(max(row_dict.get("wins", 0), 0))):
            round_rows.append({**row_dict, "round_result": 1})
        for _ in range(int(max(row_dict.get("losses", 0), 0))):
            round_rows.append({**row_dict, "round_result": -1})
    rounds_long = pd.DataFrame(round_rows)
    last10_records = []
    if not rounds_long.empty:
        for _, g in rounds_long.groupby(["tactic_name", "map", "side"], as_index=False):
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
                    "trend_delta": round(((wins_last_5 / max(uses_last_5, 1)) - (wins_last_10 / max(uses_last_10, 1))) * 100, 1),
                }
            )
    last10_df = pd.DataFrame(last10_records)
    tactic_perf = tactic_perf.merge(last10_df, on=["tactic_name", "map", "side"], how="left")
    tactic_perf["last_10_usage_win_pct"] = tactic_perf["last_10_usage_win_pct"].fillna(tactic_perf["win_pct"])
    tactic_perf["trend_delta"] = tactic_perf["trend_delta"].fillna(0.0)

    def _confidence_label(row: pd.Series) -> str:
        uses = int(row["times_used"])
        delta = float(row["delta_vs_baseline"])
        if uses >= 14 and delta >= 5:
            return "Proven good"
        if uses >= 14 and delta <= -5:
            return "Proven poor"
        if uses < 6 and delta >= 4:
            return "Early positive signal"
        if uses < 6 and delta <= -4:
            return "Early negative signal"
        return "Neutral / unproven"

    tactic_perf["confidence"] = tactic_perf.apply(_confidence_label, axis=1)
    tactic_perf["recommended_action"] = tactic_perf.apply(
        lambda row: "Use More" if float(row["delta_vs_baseline"]) >= 4 and float(row["usage_pct"]) <= float(row["context_usage_avg"]) else ("Drop" if float(row["delta_vs_baseline"]) <= -5 and int(row["times_used"]) >= 10 else "Keep"),
        axis=1,
    )
    tactic_perf_all = tactic_perf.copy()

    if confidence_filter != "Any":
        allowed_conf = {"Early positive signal", "Proven good"} if confidence_filter == "Early positive signal" else {"Proven good"}
        tactic_perf = tactic_perf[tactic_perf["confidence"].isin(allowed_conf)].copy()

    tactic_perf = tactic_perf[tactic_perf["times_used"] >= min_sample].copy()
    if tactic_perf.empty:
        st.info("No tactics meet the sample/confidence settings in this exact map + side context.")
        return

    tactic_perf["bucket"] = tactic_perf["tactic_name"].apply(classify_recommendation_bucket)
    tactic_perf["route_tags"] = tactic_perf["tactic_name"].apply(extract_route_tags)
    category_baselines = (
        tactic_perf.groupby("bucket", as_index=False)
        .apply(
            lambda g: pd.Series(
                {
                    "baseline_win_pct": np.average(g["win_pct"], weights=g["times_used"].clip(lower=1)),
                    "avg_uses": g["times_used"].mean(),
                    "avg_delta": g["delta_vs_baseline"].mean(),
                }
            )
        )
        .to_dict(orient="records")
    )
    category_baselines_map = {str(row["bucket"]): row for row in category_baselines}
    tactic_perf["category_baseline_win_pct"] = tactic_perf["bucket"].map(
        lambda b: float(category_baselines_map.get(str(b), {}).get("baseline_win_pct", tactic_perf["context_baseline_win_pct"].mean()))
    )
    tactic_perf["delta_vs_category_baseline"] = (tactic_perf["win_pct"] - tactic_perf["category_baseline_win_pct"]).round(1)
    tactic_perf["category_relative_score"] = tactic_perf.apply(
        lambda row: compute_category_relative_score(row, category_baselines_map),
        axis=1,
    )
    tactic_perf["route_bonus"] = tactic_perf["route_tags"].apply(
        lambda tags: float(("mid" in tags) * 1.6 + ("ivy" in tags) * 1.6 + ("fast" in tags and "slow" in tags) * 1.2)
    )
    tactic_perf["recommendation_score"] = tactic_perf.apply(
        lambda row: compute_tactical_recommendation_score(
            row,
            prefer_coverage=prefer_coverage,
            prefer_proven=prefer_proven,
        ),
        axis=1,
    )
    keep_priority = tactic_perf["recommendation_score"].apply(classify_keep_priority)
    tactic_perf["keep_priority_label"] = keep_priority.apply(lambda x: x[0])
    tactic_perf["keep_priority_tier"] = keep_priority.apply(lambda x: x[1])
    tactic_perf = tactic_perf.sort_values(["recommendation_score", "times_used", "win_pct"], ascending=[False, False, False])

    category_order = ["Pistol", "Eco", "Standard", "Mid", "Ivy"]
    selected_rows: list[pd.Series] = []
    selected_names: set[str] = set()
    eco_fallback_used = False
    eco_exists_in_context = not tactic_perf[tactic_perf["bucket"] == "Eco"].empty
    eco_fallback_reason = "Best available eco option for this map-side; included to preserve eco coverage"

    def _is_duplicate_candidate(candidate: pd.Series) -> bool:
        cand_name = str(candidate["tactic_name"])
        cand_tags = candidate["route_tags"] if isinstance(candidate["route_tags"], set) else set()
        for existing in selected_rows:
            if _tactics_are_near_duplicate(
                cand_name,
                str(existing["tactic_name"]),
                cand_tags,
                existing["route_tags"] if isinstance(existing["route_tags"], set) else set(),
            ):
                return True
        return False

    def _pick_from_bucket(bucket: str, min_count: int, max_count: int, min_score: float) -> None:
        nonlocal selected_rows, selected_names
        current = int(sum(1 for row in selected_rows if str(row["bucket"]) == bucket))
        if current >= max_count:
            return
        pool = tactic_perf[tactic_perf["bucket"] == bucket].copy()
        if pool.empty:
            return
        for _, row in pool.iterrows():
            if len(selected_rows) >= 7:
                break
            if str(row["tactic_name"]) in selected_names:
                continue
            if float(row["recommendation_score"]) < min_score and current >= min_count:
                continue
            if _is_duplicate_candidate(row) and current >= min_count:
                continue
            selected_rows.append(row)
            selected_names.add(str(row["tactic_name"]))
            current += 1
            if current >= max_count:
                break

    _pick_from_bucket("Pistol", min_count=1, max_count=1, min_score=45.0)
    _pick_from_bucket("Eco", min_count=1, max_count=2, min_score=43.0)
    _pick_from_bucket("Standard", min_count=2, max_count=3, min_score=47.0)
    _pick_from_bucket("Mid", min_count=0, max_count=1, min_score=52.0)
    _pick_from_bucket("Ivy", min_count=0, max_count=1, min_score=52.0)

    if len(selected_rows) < 6:
        flex_pool = tactic_perf[~tactic_perf["tactic_name"].isin(selected_names)].copy()
        for _, row in flex_pool.iterrows():
            if len(selected_rows) >= 7:
                break
            if float(row["recommendation_score"]) < 54:
                break
            if _is_duplicate_candidate(row):
                continue
            selected_rows.append(row)
            selected_names.add(str(row["tactic_name"]))

    eco_selected_count = int(sum(1 for row in selected_rows if str(row.get("bucket", "")) == "Eco"))
    if eco_exists_in_context and eco_selected_count == 0:
        eco_pool = tactic_perf[tactic_perf["bucket"] == "Eco"].copy()
        if not eco_pool.empty:
            best_eco = eco_pool.sort_values(["recommendation_score", "category_relative_score", "times_used"], ascending=[False, False, False]).iloc[0].copy()
            best_eco["eco_fallback_note"] = eco_fallback_reason
            if str(best_eco["tactic_name"]) not in selected_names:
                if len(selected_rows) >= 7:
                    drop_index = None
                    weakest_score = float("inf")
                    for idx, existing in enumerate(selected_rows):
                        if str(existing.get("bucket", "")) in {"Pistol", "Eco"}:
                            continue
                        score = float(existing.get("recommendation_score", -9999))
                        if score < weakest_score:
                            weakest_score = score
                            drop_index = idx
                    if drop_index is not None:
                        removed_name = str(selected_rows[drop_index]["tactic_name"])
                        selected_rows.pop(drop_index)
                        selected_names.discard(removed_name)
                if len(selected_rows) < 7:
                    selected_rows.append(best_eco)
                    selected_names.add(str(best_eco["tactic_name"]))
                    eco_fallback_used = True

    if len(selected_rows) > 7:
        selected_rows = selected_rows[:7]

    selected_df = pd.DataFrame(selected_rows).head(7).copy()
    if selected_df.empty:
        st.info("No recommendation set could be built from current filters.")
        return
    if "eco_fallback_note" not in selected_df.columns:
        selected_df["eco_fallback_note"] = ""

    confidence_counts = selected_df["confidence"].value_counts().to_dict()
    coverage_labels = sorted({tag for tags in selected_df["route_tags"] for tag in tags if tag in {"fast", "slow", "mid", "ivy", "a", "b"}})

    st.markdown(
        f"""
        <div class='panel-card' style='margin-top:8px;'>
            <div class="panel-title">Recommended Set Summary</div>
            <div class="panel-muted">{selected_map} • {selected_side}</div>
            <div class="stats-grid overview-grid">
                <div class="stat-chip"><div class="stat-label">Recommended tactics</div><div class="stat-value">{len(selected_df)} / 7</div></div>
                <div class="stat-chip"><div class="stat-label">Category coverage</div><div class="stat-value">{selected_df['bucket'].nunique()} categories</div></div>
                <div class="stat-chip"><div class="stat-label">Confidence mix</div><div class="stat-value">Good {confidence_counts.get('Proven good', 0)} • Early+ {confidence_counts.get('Early positive signal', 0)}</div></div>
                <div class="stat-chip"><div class="stat-label">Coverage tags</div><div class="stat-value">{", ".join(coverage_labels) if coverage_labels else "Core routes only"}</div></div>
            </div>
            <div class="tb-badge-row">
                <span class="tb-chip">{selected_map}</span>
                <span class="tb-chip">{selected_side}</span>
                <span class="tb-chip">Context baseline {float(selected_df["context_baseline_win_pct"].iloc[0]):.1f}%</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="tb-legend-strip">
            <div class="panel-title">Recommendation-strength colour guide</div>
            <div class="panel-muted">Card accents show how strongly each tactic should be kept in your active pool. Category is shown by chip label only.</div>
            <div class="tb-legend-row">
                <span class="tb-legend-item"><span class="tb-legend-swatch" style="color:#1fd27d;background:#1fd27d;"></span>Core pick (green)</span>
                <span class="tb-legend-item"><span class="tb-legend-swatch" style="color:#1fbca4;background:#1fbca4;"></span>Strong keep (teal)</span>
                <span class="tb-legend-item"><span class="tb-legend-swatch" style="color:#4e97ff;background:#4e97ff;"></span>Useful keep (blue)</span>
                <span class="tb-legend-item"><span class="tb-legend-swatch" style="color:#e4b44d;background:#e4b44d;"></span>Situational (amber)</span>
                <span class="tb-legend-item"><span class="tb-legend-swatch" style="color:#ef6d4e;background:#ef6d4e;"></span>Tentative (orange/red)</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("<div class='tb-section-title'>Recommended tactic cards</div>", unsafe_allow_html=True)
    for category in category_order:
        block = selected_df[selected_df["bucket"] == category]
        if block.empty:
            continue
        for _, row in block.iterrows():
            priority_label = str(row["keep_priority_label"])
            priority_tier = str(row["keep_priority_tier"])
            color_tokens = keep_priority_color_token(priority_tier)
            reason = build_recommendation_reason(row)
            st.markdown(
                f"""
                <div class="tb-decision-card" style="--accent:{color_tokens['accent']}; --accent-text:{color_tokens['text']}; border-color:{color_tokens['accent']}66; background:linear-gradient(160deg, {color_tokens['bg']}, rgba(10, 17, 29, 0.92));">
                    <div class="tb-card-head">
                        <div class="tb-card-title">{row["tactic_name"]}</div>
                        <div class="tb-category-pill" style="--accent:#7ea7da;">{category}</div>
                    </div>
                    <div class="tb-card-sub">{row["map"]} • {row["side"]}</div>
                    <div class="tb-card-meta">Score {row["recommendation_score"]:.1f} • WR {row["win_pct"]:.1f}% • Uses {int(row["times_used"])}<br/>Δmap {row["delta_vs_baseline"]:+.1f}pp • Δcat {row["delta_vs_category_baseline"]:+.1f}pp • Trend {row["trend_delta"]:+.1f}pp</div>
                    <div class="tb-card-chips">
                        <span class="tb-priority-pill" style="--accent:{color_tokens['accent']}; --accent-text:{color_tokens['text']};">{priority_label}</span>
                        <span class="tb-chip">{row["confidence"]}</span>
                        <span class="tb-chip">TierQoR {float(row["quality_of_results_component"]):+.1f}</span>
                    </div>
                    <div class="tb-tier-row">
                        <div class="tb-tier-chip"><span class="tier-label">vs S</span>{row["vs_s_text"]}</div>
                        <div class="tb-tier-chip"><span class="tier-label">vs A</span>{row["vs_a_text"]}</div>
                        <div class="tb-tier-chip"><span class="tier-label">vs B</span>{row["vs_b_text"]}</div>
                        <div class="tb-tier-chip"><span class="tier-label">vs C</span>{row["vs_c_text"]}</div>
                    </div>
                    <div class="tb-card-reason">{reason}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    selected_route_tags = [tags if isinstance(tags, set) else set() for tags in selected_df["route_tags"]]
    has_fast = any("fast" in tags for tags in selected_route_tags)
    has_slow = any("slow" in tags for tags in selected_route_tags)
    has_a = any("a" in tags for tags in selected_route_tags)
    has_b = any("b" in tags for tags in selected_route_tags)
    has_mid = "Mid" in selected_df["bucket"].values
    has_ivy = "Ivy" in selected_df["bucket"].values
    eco_depth_thin = int((selected_df["bucket"] == "Eco").sum()) <= 1
    sample_light = int(selected_df["times_used"].sum()) < 30

    balance_score = 40
    balance_score += selected_df["bucket"].nunique() * 9
    balance_score += 8 if has_fast and has_slow else 0
    balance_score += 8 if has_a and has_b else 0
    balance_score += 6 if has_mid else 0
    balance_score += 4 if has_ivy else 0
    balance_score -= 8 if eco_depth_thin else 0
    balance_score -= 8 if sample_light else 0
    balance_score = int(max(8, min(100, balance_score)))

    route_coverage_labels = sorted({tag for tags in selected_route_tags for tag in tags if tag in {"fast", "slow", "mid", "ivy", "a", "b"}})
    route_coverage_markup = "".join(f"<span class='tb-chip'>{label}</span>" for label in route_coverage_labels) or "<span class='tb-chip'>Core routes only</span>"
    category_mix_markup = "".join(
        f"<span class='tb-chip'>{bucket} {int((selected_df['bucket'] == bucket).sum())}</span>"
        for bucket in category_order
        if int((selected_df["bucket"] == bucket).sum()) > 0
    )

    def _alt_reason(row: pd.Series, overlap_with: str | None) -> str:
        if overlap_with:
            return f"Overlap with stronger pick ({overlap_with}) — bench but viable."
        if int(row["times_used"]) <= 3:
            return "Low-confidence alternative due to limited sample."
        if float(row["trend_delta"]) < -4:
            return "Coverage option, but recent trend is weaker."
        if row["confidence"] in {"Neutral / unproven", "Early negative signal", "Proven poor"}:
            return "Bench but viable: confidence signal is lower than selected set."
        return "Coverage option with decent score, but current picks are stronger keeps."

    module_sections = [
        """
        <div class="tb-module">
            <h4>Bench / Alternatives</h4>
            <div class="tb-module-sub">Backups are shown by category with quick quality context and why they were left on the bench.</div>
        </div>
        """
    ]
    for category in category_order:
        category_pool = tactic_perf[tactic_perf["bucket"] == category].copy()
        alternatives = category_pool[~category_pool["tactic_name"].isin(selected_names)].head(3) if not category_pool.empty else pd.DataFrame()
        alt_items: list[str] = []
        if alternatives.empty:
            alt_items.append(
                f"<div class='tb-empty' style='padding:11px 10px;'>No meaningful {category.lower()} alternatives in current sample.</div>"
            )
            module_sections.append(
                f"<div class='tb-module tb-alt-group'><div class='tb-alt-group-head'>{category} alternatives</div>{''.join(alt_items)}</div>"
            )
            continue
        for _, row in alternatives.iterrows():
            overlap_with = next(
                (
                    str(sel["tactic_name"])
                    for _, sel in selected_df.iterrows()
                    if _tactics_are_near_duplicate(
                        str(row["tactic_name"]),
                        str(sel["tactic_name"]),
                        row["route_tags"] if isinstance(row["route_tags"], set) else set(),
                        sel["route_tags"] if isinstance(sel["route_tags"], set) else set(),
                    )
                ),
                None,
            )
            why_not = _alt_reason(row, overlap_with)
            tier_note = build_recommendation_reason(row, include_base=False)
            alt_reason = f"{why_not} {tier_note}".strip() if tier_note else why_not
            priority_label = str(row["keep_priority_label"])
            priority_tier = str(row["keep_priority_tier"])
            color_tokens = keep_priority_color_token(priority_tier)
            alt_items.append(
                f"""
                <div class="tb-alt-item" style="--accent:{color_tokens['accent']}; border-color:{color_tokens['accent']}55; background:linear-gradient(160deg, {color_tokens['bg']}, rgba(10, 16, 28, 0.9));">
                    <div class="tb-alt-item-top">
                        <div class="tb-alt-name">{row["tactic_name"]}</div>
                        <span class="tb-category-pill" style="--accent:#7ea7da;">{category}</span>
                    </div>
                    <div class="tb-alt-meta">Score {row["recommendation_score"]:.1f} • WR {row["win_pct"]:.1f}% • Uses {int(row["times_used"])} • {row["confidence"]} • {priority_label}</div>
                    <div class="tb-tier-row" style="margin-left:0; margin-top:6px;">
                        <div class="tb-tier-chip"><span class="tier-label">S</span>{row["vs_s_text"]}</div>
                        <div class="tb-tier-chip"><span class="tier-label">A</span>{row["vs_a_text"]}</div>
                        <div class="tb-tier-chip"><span class="tier-label">B</span>{row["vs_b_text"]}</div>
                        <div class="tb-tier-chip"><span class="tier-label">C</span>{row["vs_c_text"]}</div>
                    </div>
                    <div class="tb-alt-reason">{alt_reason}</div>
                </div>
                """,
            )
        module_sections.append(
            f"<div class='tb-module tb-alt-group'><div class='tb-alt-group-head'>{category} alternatives</div>{''.join(alt_items)}</div>"
        )

    insights = []
    insights.append(("Strong standard depth" if int((selected_df["bucket"] == "Standard").sum()) >= 2 else "Standard depth is currently limited", "good" if int((selected_df["bucket"] == "Standard").sum()) >= 2 else "warn"))
    if not eco_exists_in_context:
        insights.append(("No Eco tactics recorded for this map-side context", "warn"))
    elif eco_fallback_used:
        insights.append(("Eco pool is weak, but the best available eco option was force-included for coverage.", "warn"))
    else:
        insights.append(("Only one eco option is currently trustworthy" if eco_depth_thin else "Eco depth has meaningful redundancy", "warn" if eco_depth_thin else "good"))
    insights.append(("No Ivy coverage available in current sample" if not has_ivy else "Ivy coverage exists in the selected set", "warn" if not has_ivy else "good"))
    insights.append(("Set leans slow-control heavy" if has_slow and not has_fast else "Good mix of fast and control profiles" if has_fast and has_slow else "Tempo profile is narrow", "warn" if (has_slow and not has_fast) or not (has_fast and has_slow) else "good"))
    insights.append(("Selected set is sample-light, so confidence remains tentative" if sample_light else "Good mix of proven and early-positive tactics", "warn" if sample_light else "good"))
    set_explanation = build_set_explanation(selected_df)
    if set_explanation:
        insights.append(set_explanation)
    insight_markup = "".join(f"<div class='tb-insight {level}'>{text}</div>" for text, level in insights)

    module_sections.append(
        f"""
        <div class="tb-module">
            <h4>Coverage &amp; Balance</h4>
            <div class="tb-module-sub">Compact health view of category depth, route variety, tempo mix, and confidence risk.</div>
            <div class="tb-badge-row">
                <span class="tb-chip">Total selected {len(selected_df)} / 7</span>
                <span class="tb-chip">Balanced score {balance_score}/100</span>
                <span class="tb-chip">{'Balanced' if balance_score >= 72 else 'Moderately narrow' if balance_score >= 56 else 'Narrow profile'}</span>
            </div>
            <div class="tb-balance-strip"><span style="width:{balance_score}%;"></span></div>
            <div class="tb-module-sub" style="margin-top:9px;">Category coverage</div>
            <div class="tb-badge-row">{category_mix_markup}</div>
            <div class="tb-module-sub" style="margin-top:8px;">Route coverage tags</div>
            <div class="tb-badge-row">{route_coverage_markup}</div>
            <div class="tb-insight-grid">{insight_markup}</div>
        </div>
        """
    )

    pistol_count = int((selected_df["bucket"] == "Pistol").sum())
    eco_count = int((selected_df["bucket"] == "Eco").sum())
    standard_count = int((selected_df["bucket"] == "Standard").sum())
    mid_count = int((selected_df["bucket"] == "Mid").sum())
    ivy_count = int((selected_df["bucket"] == "Ivy").sum())
    why_points = [f"Set prioritises {pistol_count} stable pistol slot, {eco_count} eco option{'s' if eco_count != 1 else ''}, and {standard_count} above-baseline standard picks with distinct tactical value."]
    if mid_count:
        why_points.append("Mid coverage is included because it improves route diversity without dragging quality below category baseline.")
    else:
        why_points.append("Mid was not forced in because available Mid options did not clear the quality threshold for this exact map-side pool.")
    if ivy_count:
        why_points.append("Ivy coverage is kept because it contributes independent route pressure with acceptable confidence.")
    else:
        why_points.append("No Ivy tactic was promoted because current Ivy data is too weak or redundant to justify a slot.")
    why_markup = "".join(f"<div class='tb-why-point'>{point}</div>" for point in why_points)
    module_sections.append(
        f"""
        <div class="tb-module">
            <h4>Why this set works</h4>
            <div class="tb-module-sub">Selection logic stays map-side specific, score-led, and coverage-aware without forcing low-quality fillers.</div>
            <div class="tb-why-points">{why_markup}</div>
        </div>
        """
    )
    st.markdown(f"<div class='tb-module-grid'>{''.join(module_sections)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='tb-section-title'>Recently used tactics (Last 5 days)</div>", unsafe_allow_html=True)
    recent_window_df, window_start, window_end = build_recent_tactic_window(context_df, lookback_days=5)
    if recent_window_df.empty or window_start is None or window_end is None:
        st.markdown(
            "<div class='tb-empty'>No tactics used in the last 5 days for this map-side context.</div>",
            unsafe_allow_html=True,
        )
    else:
        recent_summary = (
            recent_window_df.groupby("tactic_name", as_index=False)[["wins", "losses"]]
            .sum()
            .assign(
                uses_last_5d=lambda d: d["wins"] + d["losses"],
                win_pct_recent=lambda d: (d["wins"] / d["uses_last_5d"].clip(lower=1) * 100).round(1),
                net_rounds_recent=lambda d: d["wins"] - d["losses"],
            )
        )
        recent_summary = recent_summary.merge(
            safe_select_columns(
                tactic_perf_all,
                [
                    "tactic_name",
                    "bucket",
                    "context_baseline_win_pct",
                    "recommendation_score",
                    "trend_delta",
                    "quality_of_results_component",
                    "confidence",
                ],
                fill_defaults={
                    "bucket": "",
                    "context_baseline_win_pct": 50.0,
                    "recommendation_score": 50.0,
                    "trend_delta": 0.0,
                    "quality_of_results_component": 0.0,
                    "confidence": "Neutral / unproven",
                },
            ).drop_duplicates("tactic_name"),
            on="tactic_name",
            how="left",
        )
        recent_summary["bucket"] = recent_summary["bucket"].fillna(recent_summary["tactic_name"].apply(classify_recommendation_bucket))
        recent_summary["delta_vs_baseline_recent"] = (
            recent_summary["win_pct_recent"] - recent_summary["context_baseline_win_pct"].fillna(50.0)
        ).round(1)
        recent_dates = (
            recent_window_df.groupby("tactic_name", as_index=False)["date"]
            .agg(first_seen_window="min", last_seen_window="max")
        )
        recent_summary = recent_summary.merge(recent_dates, on="tactic_name", how="left")
        recent_summary["recent_status"] = recent_summary["tactic_name"].apply(
            lambda name: classify_recent_tactic_status(tactic_name=str(name), window_df=recent_window_df, full_context_df=context_df)
        )
        recent_summary["trend_delta_recent"] = recent_summary["trend_delta"].fillna(0.0)
        recent_summary["recent_confidence"] = recent_summary.apply(
            lambda row: compute_recent_signal_label(int(row["uses_last_5d"]), float(row["delta_vs_baseline_recent"])),
            axis=1,
        )
        recent_summary["short_note"] = recent_summary.apply(build_recent_tactic_note, axis=1)
        recent_summary = recent_summary.sort_values(
            ["uses_last_5d", "recommendation_score", "win_pct_recent"],
            ascending=[False, False, False],
        ).reset_index(drop=True)

        keep_count = int((recent_summary["delta_vs_baseline_recent"] >= 4).sum())
        weak_count = int((recent_summary["delta_vs_baseline_recent"] <= -4).sum())
        test_count = int(len(recent_summary) - keep_count - weak_count)
        new_count = int((recent_summary["recent_status"] == "New").sum())

        st.markdown(
            f"""
            <div class="tb-recent-summary">
                <div class="panel-title">{len(recent_summary)} tactics used in the last 5 days for {selected_map} • {selected_side}</div>
                <div class="panel-muted">Window anchored to latest filtered date: {window_start.strftime('%Y-%m-%d')} → {window_end.strftime('%Y-%m-%d')}.</div>
                <div class="tb-badge-row">
                    <span class="tb-chip">Looks worth keeping {keep_count}</span>
                    <span class="tb-chip">Needs more testing {test_count}</span>
                    <span class="tb-chip">Currently weak {weak_count}</span>
                    <span class="tb-chip">Newly introduced {new_count}</span>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        recent_cards_html: list[str] = []
        for _, row in recent_summary.head(12).iterrows():
            recent_cards_html.append(
                f"""
                <div class="tb-recent-card">
                    <div class="tb-recent-head">
                        <div class="tb-recent-name">{html.escape(str(row["tactic_name"]))}</div>
                        <span class="tb-category-pill" style="--accent:#7ea7da;">{html.escape(str(row["bucket"]))}</span>
                    </div>
                    <div class="tb-recent-meta">
                        Uses {int(row["uses_last_5d"])} • WR {float(row["win_pct_recent"]):.1f}% • Δbaseline {float(row["delta_vs_baseline_recent"]):+.1f}pp • Net rounds {int(row["net_rounds_recent"]):+d}<br/>
                        Signal: {html.escape(str(row["recent_confidence"]))} • Status: {html.escape(str(row["recent_status"]))} • First/Last seen: {pd.to_datetime(row["first_seen_window"]).strftime('%m-%d')} → {pd.to_datetime(row["last_seen_window"]).strftime('%m-%d')}
                    </div>
                    <div class="tb-recent-note">{html.escape(str(row["short_note"]))}</div>
                </div>
                """,
            )
        st.markdown(f"<div class='tb-recent-grid'>{''.join(recent_cards_html)}</div>", unsafe_allow_html=True)

        st.markdown("<div class='tb-section-title'>What’s working / What’s not</div>", unsafe_allow_html=True)
        eval_df = recent_summary.copy()
        eval_df["recent_eval_score"] = (
            eval_df["delta_vs_baseline_recent"] * 1.4
            + eval_df["trend_delta_recent"] * 0.35
            + eval_df["quality_of_results_component"].fillna(0.0) * 0.8
            + eval_df["recommendation_score"].fillna(50.0) * 0.22
            + np.sqrt(eval_df["uses_last_5d"].clip(lower=1)) * 2.4
        )
        eval_df.loc[eval_df["uses_last_5d"] <= 2, "recent_eval_score"] -= 5.0
        eval_df.loc[eval_df["uses_last_5d"] >= 8, "recent_eval_score"] += 2.0

        working_df = eval_df[
            (eval_df["recent_eval_score"] >= eval_df["recent_eval_score"].median()) | (eval_df["delta_vs_baseline_recent"] >= 4)
        ].sort_values(["recent_eval_score", "uses_last_5d"], ascending=[False, False]).head(6)
        not_working_df = eval_df[
            (eval_df["recent_eval_score"] <= eval_df["recent_eval_score"].median()) | (eval_df["delta_vs_baseline_recent"] <= -4)
        ].sort_values(["recent_eval_score", "uses_last_5d"], ascending=[True, False]).head(6)

        def _working_reason(r: pd.Series) -> str:
            if int(r["uses_last_5d"]) <= 3 and float(r["delta_vs_baseline_recent"]) > 0:
                return "Encouraging early return, but still low sample."
            if float(r["delta_vs_baseline_recent"]) >= 5 and int(r["uses_last_5d"]) >= 5:
                return "Above local baseline with usable recent reps."
            if float(r["trend_delta_recent"]) >= 5:
                return "Recent trend is improving; looks worth keeping."
            return "Positive recent signal in this map-side context."

        def _not_working_reason(r: pd.Series) -> str:
            if int(r["uses_last_5d"]) <= 3 and float(r["delta_vs_baseline_recent"]) < 0:
                return "Poor early return; needs more testing before final drop."
            if float(r["delta_vs_baseline_recent"]) <= -5 and int(r["uses_last_5d"]) >= 5:
                return "Below local baseline with repeated weak outcomes."
            if float(r["trend_delta_recent"]) <= -5:
                return "Recent dip is clear; currently looks droppable."
            return "Recently underperforming; monitor or reduce usage."

        left_html = [
            "<div class='tb-wash-col good'><div class='panel-title'>What’s working</div><div class='panel-muted'>Quick recent positives, not full-season truth.</div>"
        ]
        if working_df.empty:
            left_html.append("<div class='tb-empty' style='margin-top:8px;'>No clear positive signal in this recent window.</div>")
        for _, row in working_df.iterrows():
            left_html.append(
                textwrap.dedent(
                    f"""
                    <div class="tb-wash-item good">
                        <div class="tb-wash-title"><div class="tb-wash-name">{html.escape(str(row["tactic_name"]))}</div><span class="tb-category-pill" style="--accent:#55cfa7;">{html.escape(str(row["bucket"]))}</span></div>
                        <div class="tb-wash-meta">Uses {int(row["uses_last_5d"])} • WR {float(row["win_pct_recent"]):.1f}% • Δbaseline {float(row["delta_vs_baseline_recent"]):+.1f}pp • Signal {html.escape(str(row["recent_confidence"]))}</div>
                        <div class="tb-wash-reason">{html.escape(_working_reason(row))}</div>
                    </div>
                    """
                ).strip()
            )
        left_html.append("</div>")

        right_html = [
            "<div class='tb-wash-col bad'><div class='panel-title'>What’s not</div><div class='panel-muted'>Recent concerns to rework, reduce, or potentially drop.</div>"
        ]
        if not_working_df.empty:
            right_html.append("<div class='tb-empty' style='margin-top:8px;'>No immediate recent concern stands out.</div>")
        for _, row in not_working_df.iterrows():
            right_html.append(
                textwrap.dedent(
                    f"""
                    <div class="tb-wash-item bad">
                        <div class="tb-wash-title"><div class="tb-wash-name">{html.escape(str(row["tactic_name"]))}</div><span class="tb-category-pill" style="--accent:#eb8b77;">{html.escape(str(row["bucket"]))}</span></div>
                        <div class="tb-wash-meta">Uses {int(row["uses_last_5d"])} • WR {float(row["win_pct_recent"]):.1f}% • Δbaseline {float(row["delta_vs_baseline_recent"]):+.1f}pp • Signal {html.escape(str(row["recent_confidence"]))}</div>
                        <div class="tb-wash-reason">{html.escape(_not_working_reason(row))}</div>
                    </div>
                    """
                ).strip()
            )
        right_html.append("</div>")
        st.markdown(f"<div class='tb-wash-grid'>{''.join(left_html)}{''.join(right_html)}</div>", unsafe_allow_html=True)

    st.markdown("<div class='tb-section-title'>Copy recommended set</div>", unsafe_allow_html=True)
    compact_lines = [f"{row['bucket']}: {row['tactic_name']}" for _, row in selected_df[["bucket", "tactic_name"]].iterrows()]
    st.code("\n".join(compact_lines), language="text")
    summary_line = (
        f"This set prioritises {pistol_count} pistol, {eco_count} eco option{'s' if eco_count != 1 else ''}, "
        f"{standard_count} strong standard option{'s' if standard_count != 1 else ''}"
    )
    if mid_count or ivy_count:
        summary_line += f", and {mid_count + ivy_count} coverage pick{'s' if (mid_count + ivy_count) != 1 else ''}."
    else:
        summary_line += "."
    if standard_count >= 2 and bool((selected_df[selected_df["bucket"] == "Standard"]["route_tags"].apply(lambda t: "a" in t)).sum() >= 2):
        summary_line += " Multiple A-leaning standards are retained because they provide distinct usable profiles."
    if eco_count == 1:
        summary_line += " Eco depth is limited, so only one eco tactic is recommended."
    if not eco_exists_in_context:
        summary_line += " No Eco tactics recorded for this map-side context."
    elif eco_fallback_used:
        summary_line += " The eco slot is a forced coverage pick based on best available eco-relative profile."
    st.caption(summary_line)
    st.caption(
        "Why this set? The planner prioritises category-relative quality (especially eco vs eco), practical variety, and non-duplicate tactical value while allowing multiple strong tactics toward the same site."
    )


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

    base_df = build_medisports_vs_base_df(team_df, competition_source_col)
    if base_df.empty:
        st.warning("No match-level results available.")
        return

    st.markdown("### Overall team health")
    global_latest_season = (
        int(base_df["season_num_resolved"].dropna().max()) if "season_num_resolved" in base_df.columns and not base_df["season_num_resolved"].dropna().empty else None
    )
    default_season_option = f"S{global_latest_season}" if global_latest_season is not None else "Lifetime"
    all_seasons = sorted(
        base_df["season_num_resolved"].dropna().astype(int).unique().tolist(),
        reverse=True,
    )

    current_grouped_mode = bool(st.session_state.get("medisports_grouped_competitions", False))
    competition_for_controls = base_df.copy()
    competition_for_controls["competition_display"] = (
        competition_for_controls["competition_grouped"] if current_grouped_mode else competition_for_controls["competition_raw"]
    )

    t1, t2, t3, t4, t5 = st.columns([0.9, 1.0, 1.7, 1.0, 1.0])
    with t1:
        min_matches = int(st.slider("Minimum matches", 1, 8, 2, key="medisports_min_matches"))
    with t2:
        form_window = st.selectbox(
            "Form window",
            [
                "All time",
                "Last 10 days",
                "Last 20 days",
                "Last 30 days",
                "Last 10 matches",
                "Last 20 matches",
                "Last 30 matches",
            ],
            index=0,
            key="medisports_form_window",
        )
    with t3:
        comp_options = sorted(competition_for_controls["competition_display"].dropna().astype(str).unique().tolist())
        selected_comp = st.multiselect(
            "Tournament filter",
            comp_options,
            default=[],
            placeholder="All tournaments",
            key="medisports_comp_filter",
        )
    with t4:
        season_options = ["Lifetime"] + [f"S{season}" for season in all_seasons]
        default_season_index = season_options.index(default_season_option) if default_season_option in season_options else 0
        selected_season = st.selectbox(
            "Season",
            season_options,
            index=default_season_index,
            key="medisports_season_filter",
        )
    with t5:
        grouped_competitions = st.toggle("Grouped competitions", value=False, key="medisports_grouped_competitions")

    filtered = base_df.copy()
    filtered["competition_display"] = filtered["competition_grouped"] if grouped_competitions else filtered["competition_raw"]

    rows_before = int(filtered["match_id"].nunique()) if "match_id" in filtered.columns else int(len(filtered))
    if selected_season != "Lifetime":
        season_match = re.match(r"^S(\d+)$", str(selected_season), flags=re.IGNORECASE)
        if season_match is not None:
            target_season = f"S{int(season_match.group(1))}"
            filtered = filtered[filtered["season_resolved"] == target_season].copy()
    rows_after_season = int(filtered["match_id"].nunique()) if "match_id" in filtered.columns else int(len(filtered))

    selected_comp_keys = [normalize_competition_label(name) for name in selected_comp]
    if selected_comp_keys:
        filtered = filtered[filtered["competition_key"].isin(selected_comp_keys)].copy()
    rows_after_tournament = int(filtered["match_id"].nunique()) if "match_id" in filtered.columns else int(len(filtered))

    season_debug = base_df.copy()
    season_debug["excluded_for_season"] = False
    if selected_season != "Lifetime":
        season_debug["excluded_for_season"] = season_debug["season_resolved"] != selected_season
    season_debug["excluded_for_tournament"] = False
    if selected_comp_keys:
        season_debug["excluded_for_tournament"] = ~season_debug["competition_key"].isin(selected_comp_keys)

    with st.expander("Medisports VS debug (temporary)", expanded=False):
        st.markdown(
            f"- Selected season: **{selected_season}**\n"
            f"- Selected tournament(s): **{', '.join(selected_comp) if selected_comp else 'All tournaments'}**\n"
            f"- Rows before filtering: **{rows_before}**\n"
            f"- Rows after season filter: **{rows_after_season}**\n"
            f"- Rows after tournament filter: **{rows_after_tournament}**"
        )
        if not season_debug.empty:
            debug_cols = [
                col for col in [
                    "match_id",
                    "date",
                    "competition_raw",
                    "competition_key",
                    "opponent_original_raw",
                    "opponent_cleaned_raw",
                    "opponent_raw",
                    "opponent_away_status_applied",
                    "opponent_canonicalized",
                    "opponent_key",
                    "season_resolved",
                    "excluded_for_season",
                    "excluded_for_tournament",
                ]
                if col in season_debug.columns
            ]
            st.dataframe(
                season_debug[debug_cols].sort_values(["excluded_for_season", "excluded_for_tournament", "date"], ascending=[True, True, False]),
                use_container_width=True,
                hide_index=True,
            )
            st.markdown("**Opponent raw vs key grouping counts:**")
            opponent_debug = (
                season_debug.groupby(["opponent_key", "opponent_raw", "opponent_original_raw", "opponent_cleaned_raw", "opponent_canonicalized"], as_index=False)
                .agg(matches=("match_id", "nunique"))
                .sort_values(["opponent_key", "matches"], ascending=[True, False])
            )
            st.dataframe(opponent_debug, use_container_width=True, hide_index=True)
            league_debug = season_debug[
                season_debug["competition_raw"].astype(str).str.contains("league", case=False, na=False)
                & season_debug["excluded_for_season"]
            ]
            if not league_debug.empty:
                st.markdown("**League rows excluded by season filter:**")
                st.dataframe(
                    league_debug[debug_cols].sort_values("date", ascending=False).head(30),
                    use_container_width=True,
                    hide_index=True,
                )
    if form_window != "All time":
        window_match = re.match(r"^Last\s+(\d+)\s+(days|matches)$", str(form_window), flags=re.IGNORECASE)
        if window_match is not None:
            window_size = int(window_match.group(1))
            window_unit = str(window_match.group(2)).lower()
            filtered = filtered.sort_values("date", ascending=False).copy()
            if window_unit == "days":
                latest_date = pd.to_datetime(filtered["date"], errors="coerce").max()
                if pd.notna(latest_date):
                    start_date = latest_date - pd.Timedelta(days=window_size - 1)
                    filtered = filtered[pd.to_datetime(filtered["date"], errors="coerce") >= start_date].copy()
            else:
                filtered = filtered.head(window_size)
    if filtered.empty:
        st.info("No matches left after filters.")
        return
    filtered["competition"] = filtered["competition_display"]
    filtered["opponent_team"] = filtered["opponent_raw"]
    opponent_latest_tier = resolve_latest_opponent_tier(filtered)
    filtered = filtered.merge(opponent_latest_tier, on="opponent_key", how="left")
    filtered["opponent_tier"] = filtered["latest_tier"]
    filtered["opponent_display"] = filtered.apply(
        lambda row: (
            f"{row['opponent_team']}  ·  Tier {row['latest_tier']}"
            if str(row.get("latest_tier", "")).strip() not in {"", "<NA>", "nan", "None"}
            else str(row["opponent_team"])
        ),
        axis=1,
    )
    scope = "Lifetime" if form_window == "All time" else form_window
    selected_scope = "All tournaments" if not selected_comp else f"{len(selected_comp)} tournament(s)"
    status_html = (
        "<div class='status-strip'>"
        f"<div class='status-chip'><div class='label'>Current view scope</div><div class='value'>{html.escape(scope)} · {html.escape(selected_scope)}</div></div>"
        f"<div class='status-chip'><div class='label'>Active season</div><div class='value'>{html.escape(selected_season)} (latest in data: {html.escape(default_season_option)})</div></div>"
        f"<div class='status-chip'><div class='label'>Filtered match count</div><div class='value'>{int(filtered['match_id'].nunique())} matches</div></div>"
        "</div>"
    )
    st.markdown(status_html, unsafe_allow_html=True)
    image_index = _build_image_index()
    vs_summary = (
        filtered.groupby("opponent_key", as_index=False)
        .agg(
            opponent_team=("opponent_raw", lambda s: _preferred_label(s, fallback="Unknown opponent")),
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            draws=("match_result", lambda s: int((s == "Draw").sum())),
            round_wins=("round_wins", "sum"),
            round_losses=("round_losses", "sum"),
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
        .sort_values(["win_rate_pct", "round_diff", "matches", "opponent_team"], ascending=[False, False, False, True])
    )
    vs_summary = vs_summary.merge(opponent_latest_tier, on="opponent_key", how="left")
    vs_summary["latest_tier"] = vs_summary["latest_tier"].fillna("—")
    vs_summary["tier"] = vs_summary["latest_tier"]
    vs_summary["opponent_display"] = vs_summary.apply(
        lambda row: f"{row['opponent_team']}  ·  Tier {row['latest_tier']}" if str(row["latest_tier"]) not in {"", "—", "nan"} else str(row["opponent_team"]),
        axis=1,
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
        filtered.groupby("competition_key", as_index=False)
        .agg(
            competition=("competition_display", lambda s: _preferred_label(s, fallback="Unknown competition")),
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

    performance_cards = [
        ("Matches", str(overall_matches), "After filters"),
        ("Win rate", f"{overall_win_rate:.1f}%", f"{overall_wins}W-{overall_losses}L"),
        ("Round diff", f"{overall_round_diff:+d}", "Total net rounds"),
        ("Round win %", f"{overall_round_win_pct:.1f}%", "Round-level conversion"),
    ]
    perf_html = "".join(
        f"<div class='kpi-card'><div class='kpi-value'>{html.escape(v)}</div><div class='kpi-label'>{html.escape(l)}</div><div class='kpi-sub'>{html.escape(s)}</div></div>"
        for l, v, s in performance_cards
    )
    segment_cards = [
        (
            "Best map",
            f'{best_map.iloc[0]["map"]}' if not best_map.empty else "n/a",
            f'WR {best_map.iloc[0]["win_rate_pct"]:.1f}% · RD {int(best_map.iloc[0]["round_diff"]):+d}' if not best_map.empty else "No data",
        ),
        (
            "Worst map",
            f'{worst_map.iloc[0]["map"]}' if not worst_map.empty else "n/a",
            f'WR {worst_map.iloc[0]["win_rate_pct"]:.1f}% · RD {int(worst_map.iloc[0]["round_diff"]):+d}' if not worst_map.empty else "No data",
        ),
        (
            "Best tier",
            f'Tier {best_tier.iloc[0]["tier"]}' if not best_tier.empty else "n/a",
            f'WR {best_tier.iloc[0]["win_rate_pct"]:.1f}% · RD {int(best_tier.iloc[0]["round_diff"]):+d}' if not best_tier.empty else "No data",
        ),
        (
            "Opponent segment",
            f'{best_seg.iloc[0]["opponent_team"]}' if not best_seg.empty else "n/a",
            f'Best RD {int(best_seg.iloc[0]["round_diff"]):+d} · Worst {worst_seg.iloc[0]["opponent_team"] if not worst_seg.empty else "n/a"} ({int(worst_seg.iloc[0]["round_diff"]):+d})' if not best_seg.empty else "Low sample",
        ),
    ]
    segment_html = "".join(
        f"<div class='kpi-card'><div class='kpi-value'>{html.escape(v)}</div><div class='kpi-label'>{html.escape(l)}</div><div class='kpi-sub'>{html.escape(s)}</div></div>"
        for l, v, s in segment_cards
    )
    st.markdown(
        f"<div class='panel-card'><div class='panel-muted'>Performance KPIs</div><div class='kpi-grid'>{perf_html}</div></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='panel-card'><div class='panel-muted'>Best / worst segments</div><div class='kpi-grid'>{segment_html}</div></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### What needs fixing?")
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
        "<div class='insight-panel'><div class='insight-title'>Priority fixes</div><ul class='insight-list'>"
        + "".join(f"<li>{html.escape(i)}</li>" for i in insights[:5])
        + "</ul></div>",
        unsafe_allow_html=True,
    )

    st.markdown("### Who do we beat / lose to?")
    leaderboard = vs_summary[vs_summary["matches"] >= min_matches].copy()
    if leaderboard.empty:
        st.info("No opponents meet the minimum-match threshold for this filter set.")
    else:
        chart_frame = leaderboard.sort_values("round_diff", ascending=True).head(16).copy()
        if go is None:
            _render_plotly_unavailable()
        else:
            rd_bar = go.Figure(
                go.Bar(
                    x=chart_frame["round_diff"],
                    y=chart_frame["opponent_display"],
                    orientation="h",
                    marker=dict(
                        color=chart_frame["round_diff"],
                        colorscale=[[0.0, "#ff6c7a"], [0.5, "#f0be4f"], [1.0, "#31d17b"]],
                        cmin=float(chart_frame["round_diff"].min()),
                        cmax=float(chart_frame["round_diff"].max()),
                    ),
                    customdata=chart_frame[["matches", "record", "win_rate_pct"]],
                    hovertemplate="%{y}<br>Round diff: %{x:+.0f}<br>Matches: %{customdata[0]}<br>Record: %{customdata[1]}<br>WR: %{customdata[2]:.1f}%<extra></extra>",
                    showlegend=False,
                )
            )
            rd_bar.update_layout(title="Round differential by opponent")
            rd_bar.update_xaxes(title_text="Round differential")
            rd_bar.update_yaxes(title_text="", automargin=True)
            _apply_plotly_dark_style(rd_bar, height=430, margin=dict(l=210, r=24, t=48, b=44))
            st.plotly_chart(rd_bar, use_container_width=True)

        status_class = {"Strong": "vs-pill-good", "Even": "vs-pill-mid", "Weak": "vs-pill-bad", "Low Sample": "vs-pill-mid"}

        def _rank_rows(frame: pd.DataFrame, heading: str) -> str:
            rows_html = []
            for idx, (_, row) in enumerate(frame.iterrows(), start=1):
                round_class = "vs-pill-good" if float(row["round_diff"]) >= 0 else "vs-pill-bad"
                wr_class = "vs-pill-good" if float(row["win_rate_pct"]) >= 55 else ("vs-pill-mid" if float(row["win_rate_pct"]) >= 45 else "vs-pill-bad")
                status = str(row["status"])
                rows_html.append(
                    f'<div class="ranked-row"><div class="vs-pill">#{idx}</div><div class="rank-cell-main"><span class="rank-name">{html.escape(str(row["opponent_display"]))}</span></div><div class="stat-label">Matches <b>{int(row["matches"])}</b></div><div class="stat-label">Record <b>{html.escape(str(row["record"]))}</b></div><div><span class="vs-pill {wr_class}">WR {float(row["win_rate_pct"]):.1f}%</span></div><div><span class="vs-pill {round_class}">RD {int(row["round_diff"]):+d}</span></div><div><span class="vs-pill">Map {html.escape(str(row["most_played_map"]))}</span></div><div><span class="vs-pill {status_class.get(status, "vs-pill-mid")}">{html.escape(status)}</span></div></div>'
                )
            return f"<div class='panel-card'><div class='panel-muted'>{html.escape(heading)}</div><div class='ranked-list'>{''.join(rows_html)}</div></div>"

        strongest = leaderboard.sort_values(["round_diff", "win_rate_pct"], ascending=[False, False]).head(6)
        weakest = leaderboard.sort_values(["round_diff", "win_rate_pct"], ascending=[True, True]).head(6)
        left_col, right_col = st.columns(2)
        with left_col:
            st.markdown(_rank_rows(strongest, "Strongest matchups"), unsafe_allow_html=True)
        with right_col:
            st.markdown(_rank_rows(weakest, "Weakest matchups"), unsafe_allow_html=True)

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
                        <div class="panel-title">{html.escape(str(row["opponent_display"]))}</div>
                        <div style="display:flex;flex-wrap:wrap;gap:6px;margin-top:6px;">
                            <span class="vs-pill">{int(row["wins"])}W-{int(row["losses"])}L-{int(row["draws"])}D</span>
                            <span class="vs-pill {'vs-pill-good' if float(row["win_rate_pct"]) >= 55 else 'vs-pill-bad'}">WR {float(row["win_rate_pct"]):.1f}%</span>
                            <span class="vs-pill {'vs-pill-good' if int(row["round_diff"]) >= 0 else 'vs-pill-bad'}">RD {int(row["round_diff"]):+d}</span>
                            <span class="vs-pill">Map {html.escape(str(row["most_played_map"]))}</span>
                            <span class="vs-pill">Tier {html.escape(str(row["tier"]))}</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    st.markdown("### Where do we perform best?")
    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.markdown("#### Matchup strength (round differential)")
        diff_data = vs_summary[vs_summary["matches"] >= min_matches].sort_values("round_diff", ascending=False)
        if go is not None:
            wrapped_labels = _wrap_labels(diff_data["opponent_display"], width=26)
            bar_height = 30
            min_height = 340
            chart_height = max(min_height, len(diff_data) * bar_height + 80)
            longest_label = max((len(name) for name in diff_data["opponent_display"].astype(str)), default=0)
            left_margin = min(420, max(170, 80 + longest_label * 6))

            diff_chart = go.Figure(
                go.Bar(
                    x=diff_data["round_diff"],
                    y=wrapped_labels,
                    orientation="h",
                    marker_color=["#44c06f" if value >= 0 else "#e85c6b" for value in diff_data["round_diff"]],
                    customdata=diff_data[["opponent_display", "record", "matches", "round_diff_per_match"]],
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
            wrapped_labels = _wrap_labels(wl_data["opponent_display"], width=26)
            bar_height = 30
            min_height = 340
            chart_height = max(min_height, len(wl_data) * bar_height + 80)
            longest_label = max((len(name) for name in wl_data["opponent_display"].astype(str)), default=0)
            left_margin = min(420, max(170, 80 + longest_label * 6))

            wl_chart = go.Figure(
                go.Bar(
                    x=wl_data["match_diff"],
                    y=wrapped_labels,
                    orientation="h",
                    marker_color=["#44c06f" if value >= 0 else "#e85c6b" for value in wl_data["match_diff"]],
                    customdata=wl_data[["opponent_display", "record", "matches", "win_loss_per_match"]],
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
        filtered.groupby(["map", "opponent_key"], as_index=False)
        .agg(
            opponent_team=("opponent_raw", lambda s: _preferred_label(s, fallback="Unknown opponent")),
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
    map_summary = map_summary.merge(opponent_latest_tier, on="opponent_key", how="left")
    map_summary["opponent_display"] = map_summary.apply(
        lambda row: (
            f"{row['opponent_team']}  ·  Tier {row['latest_tier']}"
            if str(row.get("latest_tier", "")).strip() not in {"", "<NA>", "nan", "None"}
            else str(row["opponent_team"])
        ),
        axis=1,
    )
    map_heat = map_summary[map_summary["matches"] >= min_matches]
    if map_heat.empty:
        st.info("No opponent-map pairs meet minimum matches.")
    else:
        if go is None:
            _render_plotly_unavailable()
        else:
            opponent_order = (
                map_heat.groupby("opponent_display", as_index=False)["win_rate_pct"]
                .mean()
                .sort_values("win_rate_pct", ascending=False)["opponent_display"]
                .tolist()
            )
            map_order = sorted(map_heat["map"].astype(str).unique().tolist())
            z = (
                map_heat.pivot(index="opponent_display", columns="map", values="win_rate_pct")
                .reindex(index=opponent_order, columns=map_order)
            )
            matches_text = (
                map_heat.pivot(index="opponent_display", columns="map", values="matches")
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
            clean_competition = _sanitize_competition_value(row.get("competition", ""))
            clean_best_map = _sanitize_competition_value(row.get("best_map", ""))
            logo_html = (
                f'<img class="rank-logo" src="{row["competition_logo"]}" alt="competition logo">'
                if row["competition_logo"]
                else '<span class="rank-logo"></span>'
            )
            t_rows.append(
                textwrap.dedent(
                    f"""
                    <div class="ranked-row" style="grid-template-columns: minmax(0, 1.8fr) repeat(6, minmax(0, 1fr));">
                        <div class="rank-cell-main">{logo_html}<span class="rank-name">{html.escape(str(clean_competition))}</span></div>
                        <div class="stat-label">Matches <b>{int(row["matches"])}</b></div>
                        <div class="stat-label">Record <b>{int(row["wins"])}-{int(row["losses"])}-{int(row["draws"])}</b></div>
                        <div><span class="vs-pill {wr_class}">WR {float(row["win_rate_pct"]):.1f}%</span></div>
                        <div><span class="vs-pill {rd_class}">RD {int(row["round_diff"]):+d}</span></div>
                        <div><span class="vs-pill">Best map {html.escape(str(clean_best_map))}</span></div>
                        <div></div>
                    </div>
                    """
                ).strip()
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
                textwrap.dedent(
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
                ).strip()
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
            ["opponent_display", "matches", "record", "win_rate_pct", "round_diff", "map_pill", "tier_pill", "confidence", "status"]
        ].rename(
            columns={
                "opponent_display": "Opponent",
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
        sorted(filtered["opponent_display"].dropna().astype(str).unique().tolist()),
        default=[],
        key="medisports_opp_filter",
    )
    match_table = filtered[filtered["match_result"].isin(result_filter)].copy()
    if opp_filter:
        match_table = match_table[match_table["opponent_display"].isin(opp_filter)]
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
                "opponent_display",
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
            "opponent_display": st.column_config.TextColumn("Opponent", width="medium"),
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
        st.session_state["page"] = "front_page"

    page = st.session_state["page"]
    competition_source_col = "competition"
    if page in {"front_page", "profiles", "tactics", "medisports_vs", "tactical_set", "tournament_summary", "opponent_review"}:
        competition_view = st.radio(
            "Competition View",
            ["Raw competition names", "Grouped competition names"],
            index=0,
            horizontal=True,
            key="competition_view_mode",
        )
        competition_source_col = "competition" if competition_view == "Raw competition names" else "grouped_competition"

    if page == "front_page":
        _front_page(player_df, tactics_df, competition_source_col)
    elif page == "profiles":
        _hltv_profile_view(player_df, tactics_df, achievements_df, competition_source_col)
    elif page == "tactics":
        _teams_tactical_breakdown(tactics_df, player_df, competition_source_col)
    elif page == "medisports_vs":
        _medisports_vs_breakdown(tactics_df, player_df, competition_source_col)
    elif page == "tournament_summary":
        _tournament_summary_page(tactics_df, player_df, competition_source_col)
    elif page == "opponent_review":
        _opponent_review_page(tactics_df, player_df, competition_source_col)
    elif page == "tactical_set":
        _tactical_set_recommendations(tactics_df, player_df, competition_source_col)
    else:
        _home()


if __name__ == "__main__":
    main()
