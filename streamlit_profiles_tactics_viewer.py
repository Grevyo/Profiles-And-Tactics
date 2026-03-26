"""Grevs CPL pages built from local CSV data files.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

import base64
import html
from pathlib import Path
import re

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Grevs CPL Pages", layout="wide")

DATA_DIR = Path(__file__).parent / "data"
PLAYER_CSV = DATA_DIR / "PlayerDataMatser.csv"
TACTICS_CSV = DATA_DIR / "TacticsDataMaster.csv"
ACHIEVEMENTS_CSV = DATA_DIR / "Achievements.csv"
PLAYER_META_CSV = DATA_DIR / "player.csv"
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


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .panel-card {
            background: radial-gradient(circle at top, #1a2234 0%, #0b0f17 68%);
            border: 1px solid rgba(151, 166, 195, 0.45);
            border-radius: 16px;
            padding: 20px 22px;
            margin-bottom: 16px;
            box-shadow: 0 16px 32px rgba(0, 0, 0, 0.32);
        }
        .panel-muted {
            color: #9da7bd;
            font-size: 0.85rem;
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
            grid-template-columns: repeat(3, minmax(0, 1fr));
            gap: 10px;
            margin-top: 12px;
        }
        .overview-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
        .stat-chip {
            border: 1px solid rgba(151, 166, 195, 0.35);
            border-radius: 10px;
            padding: 9px 11px;
            background: rgba(18, 25, 40, 0.8);
            min-height: 84px;
        }
        .stat-label { color: #9da7bd; font-size: 0.78rem; }
        .stat-value { color: #f5f7fb; font-size: 1.25rem; font-weight: 800; line-height: 1.15; }
        .stat-trend { font-size: 0.78rem; margin-top: 4px; font-weight: 600; }
        .trend-good { color: #31d17b; }
        .trend-mid { color: #f0be4f; }
        .trend-bad { color: #ff6c7a; }
        .chip-good {
            border-color: rgba(49, 209, 123, 0.6);
            background: linear-gradient(180deg, rgba(25, 56, 45, 0.92), rgba(16, 30, 26, 0.84));
        }
        .chip-mid {
            border-color: rgba(240, 190, 79, 0.58);
            background: linear-gradient(180deg, rgba(66, 54, 24, 0.92), rgba(31, 27, 17, 0.84));
        }
        .chip-bad {
            border-color: rgba(255, 108, 122, 0.62);
            background: linear-gradient(180deg, rgba(72, 31, 37, 0.92), rgba(32, 18, 22, 0.84));
        }
        .stat-meter {
            width: 100%;
            background: rgba(151, 166, 195, 0.2);
            border-radius: 999px;
            overflow: hidden;
            height: 6px;
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
            grid-template-columns: 1.45fr 0.95fr 1.15fr;
            gap: 12px;
            align-items: stretch;
        }
        .identity-strip {
            border: 1px solid rgba(151, 166, 195, 0.35);
            border-radius: 12px;
            padding: 12px;
            background: rgba(14, 20, 32, 0.78);
        }
        .identity-strip-main {
            display: grid;
            grid-template-columns: 110px 1fr;
            gap: 12px;
            align-items: center;
        }
        .portrait-frame {
            border: 1px solid rgba(104, 143, 210, 0.5);
            border-radius: 10px;
            padding: 6px;
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
            gap: 8px;
            margin-top: 6px;
        }
        .achievement-inline-list-single {
            justify-content: flex-start;
        }
        .achievement-inline-item {
            width: 132px;
            height: 162px;
            border: 1px solid rgba(151, 166, 195, 0.34);
            border-radius: 10px;
            background: linear-gradient(180deg, rgba(22, 31, 47, 0.92), rgba(10, 16, 27, 0.94));
            display: block;
            flex: 0 0 132px;
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
            padding: 22px 10px 30px;
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
            font-size: 0.66rem;
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
            font-size: 2rem;
            color: #f5f7fb;
            font-weight: 900;
            margin-top: 2px;
            line-height: 1.05;
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
            border: 1px solid rgba(118, 168, 255, 0.45);
            border-radius: 14px;
            padding: 12px;
            background: linear-gradient(120deg, rgba(54, 87, 155, 0.45) 0%, rgba(35, 57, 103, 0.2) 100%);
            box-shadow: 0 0 18px rgba(54, 116, 255, 0.22);
            text-align: center;
        }
        .overview-side {
            border: 1px solid rgba(151, 166, 195, 0.35);
            border-radius: 12px;
            padding: 12px;
            background: rgba(14, 20, 32, 0.78);
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
            margin-top: 12px;
            margin-bottom: 5px;
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
                        <span class="hero-pill">HLTV Style</span>
                        <span class="hero-pill">Medicart Data</span>
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
    normalized = _normalize_key(value)
    entries = image_index.get(image_type, {})
    return entries.get(normalized)


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


@st.cache_data(show_spinner=False)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    players = pd.read_csv(PLAYER_CSV)
    tactics = pd.read_csv(TACTICS_CSV)
    players = _normalize_match_id_column(players)
    tactics = _normalize_match_id_column(tactics)

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

    return players, tactics, achievements


@st.cache_data(show_spinner=False)
def _load_player_metadata() -> pd.DataFrame:
    if not PLAYER_META_CSV.exists():
        return pd.DataFrame()

    metadata = pd.read_csv(PLAYER_META_CSV)
    metadata.columns = metadata.columns.astype(str).str.strip()
    metadata = metadata.apply(lambda col: col.str.strip() if col.dtype == object else col)
    if metadata.empty:
        return metadata

    player_col = next((col for col in metadata.columns if col.casefold() == "player"), None)
    if player_col is None:
        return pd.DataFrame()

    metadata = metadata.rename(columns={player_col: "player"})
    metadata["player_lookup"] = metadata["player"].astype(str).str.strip().str.casefold()
    metadata = metadata.drop_duplicates(subset=["player_lookup"], keep="last")
    return metadata


def _player_meta_value(player_meta: pd.Series | None, key: str, default: str = "-") -> str:
    if player_meta is None:
        return default
    value = str(player_meta.get(key, "")).strip()
    return value if value else default


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


def _expand_tactics_by_round_type(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "tactic_name" not in df.columns:
        return df.copy()

    expanded = df.copy()
    tactic_names = expanded["tactic_name"].fillna("").astype(str)
    round_types: list[list[str]] = []
    for tactic_name in tactic_names:
        tags: list[str] = []
        if "(P)" in tactic_name:
            # Pistol tactics are also available as eco + standard callups.
            tags.extend(["Pistol", "Eco", "Standard"])
        elif "(E)" in tactic_name:
            tags.append("Eco")
        elif "(S)" in tactic_name:
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


def _build_match_level_results(tactics_df: pd.DataFrame) -> pd.DataFrame:
    if tactics_df.empty:
        return pd.DataFrame()
    match_cols = ["match_id", "date", "map", "competition", "my_team", "opponent_team"]
    meta_cols = [col for col in match_cols if col in tactics_df.columns]
    match_meta = tactics_df.groupby("match_id", as_index=False)[meta_cols].first()
    results = (
        tactics_df.groupby("match_id", as_index=False)[["wins", "losses"]]
        .sum()
        .rename(columns={"wins": "round_wins", "losses": "round_losses"})
    )
    results["round_diff"] = results["round_wins"] - results["round_losses"]
    results["match_result"] = results["round_diff"].apply(lambda x: "Win" if x > 0 else ("Loss" if x < 0 else "Draw"))
    return match_meta.merge(results, on="match_id", how="inner")


def _apply_shared_filters(
    player_df: pd.DataFrame,
    tactics_df: pd.DataFrame,
    selected_player: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    filtered_players = player_df[player_df["player"] == selected_player].copy()

    min_date = filtered_players["date"].min().date()
    max_date = filtered_players["date"].max().date()

    st.markdown('<p class="compact-filter-header">Player Filters</p>', unsafe_allow_html=True)
    filter_cols = st.columns(5)
    tier_options = sorted(filtered_players["tier"].dropna().unique().tolist())
    with filter_cols[0]:
        selected_tiers = _multiselect_filter("Tier of Team", tier_options, key="profile_tier")

    event_options = sorted(filtered_players["competition"].dropna().unique().tolist())
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
        filtered_players = filtered_players[filtered_players["competition"].isin(selected_events)]
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


def _hltv_profile_view(player_df: pd.DataFrame, tactics_df: pd.DataFrame, achievements_df: pd.DataFrame) -> None:
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
        filtered_players, filtered_tactics = _apply_shared_filters(player_df, tactics_df, selected_player)
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
    deaths = int(metrics["deaths"])
    assists = int(metrics["assists"])
    damage = int(filtered_players["damage"].sum())
    rounds = int(filtered_players["rounds_played"].sum())
    avg_acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0
    avg_hs = float(filtered_players["hs_pct"].mean()) if not filtered_players.empty else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if not filtered_players.empty else 0.0

    stat_chips_overview = [
        _build_stat_chip("Rating", f'{metrics["grevscore"]:.2f}', metrics["grevscore"], 0.65, 1.35),
        _build_stat_chip("Matches", f'{int(metrics["matches"])}', metrics["matches"], 3, 16),
        _build_stat_chip("K/D", f'{metrics["kd"]:.2f}', metrics["kd"], 0.7, 1.3),
        _build_stat_chip("KDA", f'{metrics["kda"]:.2f}', metrics["kda"], 1.0, 2.2),
    ]
    stat_chips_damage = [
        _build_stat_chip("DPM", f'{metrics["dpm"]:.1f}', metrics["dpm"], 1800, 3600),
        _build_stat_chip("KPM", f'{metrics["kpm"]:.2f}', metrics["kpm"], 0.45, 1.0),
        _build_stat_chip("Impact", f'{metrics["impact"]:.1f}', metrics["impact"], 45, 95),
    ]
    stat_chips_efficiency = [
        _build_stat_chip("Acc%", f'{metrics["acc"]:.1f}%', metrics["acc"], 45, 80),
        _build_stat_chip("Avg KPD", f"{avg_kpd:.2f}", avg_kpd, 0.8, 1.5),
        _build_stat_chip("HS%", f"{avg_hs:.1f}%", avg_hs, 24, 55),
    ]
    side_split = "-"
    if not filtered_tactics.empty and "side" in filtered_tactics.columns:
        side_summary = (
            filtered_tactics.groupby("side", as_index=False)[["wins", "losses"]].sum().sort_values("wins", ascending=False)
        )
        if not side_summary.empty:
            s = side_summary.iloc[0]
            side_split = f'{s["side"]}: {int(s["wins"])}W-{int(s["losses"])}L'
    best_map = (
        filtered_players.groupby("map")["kills"].sum().sort_values(ascending=False).index[0]
        if "map" in filtered_players.columns and not filtered_players.empty
        else "-"
    )
    stat_chips_context = [
        _build_stat_chip("Best Map", best_map, float(metrics["kd"]), 0.7, 1.3),
        _build_stat_chip("Record", f"{kills}/{deaths}/{assists}", metrics["kda"], 1.0, 2.2),
        _build_stat_chip("Side Split", side_split, float(metrics["kpm"]), 0.45, 1.0),
        _build_stat_chip("Team Rank", f"#{team_rank}/{rank_total}", percentile, 0, 100),
    ]

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

    st.markdown(
        f"""
        <div class="panel-card">
            <div class="top-identity-grid">
                <div class="identity-strip">
                    <div class="identity-strip-main">
                        <div class="portrait-frame">
                            {"<img class='player-headshot' src='data:image/png;base64," + base64.b64encode(player_image.read_bytes()).decode("utf-8") + "'>" if player_image else "<div class='panel-muted'>No portrait found.</div>"}
                            <div class="portrait-strip">
                                <div>Rating note: <strong>{score_tier}</strong></div>
                                <div>Percentile: <strong>{percentile:.0f}th</strong></div>
                            </div>
                        </div>
                        <div>
                            <div class="profile-label">Player Identity</div>
                            <div class="profile-name">{selected_player}</div>
                            <div class="team-line">{team_logo_html}<span>{first_row.get("my_team", "-")}</span></div>
                            <div class="panel-muted">Role: {_player_meta_value(player_meta_row, "role", "Fragger")} · Country: {_player_meta_value(player_meta_row, "nation")} · Handedness: {_player_meta_value(player_meta_row, "handedness")}</div>
                        </div>
                    </div>
                    <div class="quick-row">
                        <div class="identity-kv">
                            <div class="profile-label">Best Map</div>
                            <div class="identity-kv-value">{best_map}</div>
                        </div>
                        <div class="identity-kv">
                            <div class="profile-label">Team Rank</div>
                            <div class="identity-kv-value">#{team_rank}/{rank_total}</div>
                        </div>
                    </div>
                    <div class="section-label">Achievements</div>
                    {achievement_inline_html}
                </div>
                <div class="hero-grevscore">
                    <div class="hero-grevscore-label">Grevscore</div>
                    <div class="hero-grevscore-tier">{score_tier} · {percentile:.0f}th percentile</div>
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
                    <div class="panel-muted" style="margin-top:6px;">
                        {"Side note: Below average" if metrics["grevscore"] < 0.95 else "Side note: Above average"}
                    </div>
                    <div class="panel-muted">
                        Team rank #{team_rank}/{rank_total}
                    </div>
                </div>
                <div class="overview-side">
                    <div class="section-label">Overview</div>
                    <div class="stats-grid overview-grid">
                        {"".join(stat_chips_overview)}
                    </div>
                </div>
            </div>
            <div class="section-label">Damage / Output</div>
            <div class="stats-grid">
                {"".join(stat_chips_damage)}
            </div>
            <div class="section-label">Accuracy / Efficiency</div>
            <div class="stats-grid">
                {"".join(stat_chips_efficiency)}
            </div>
            <div class="section-label">Context</div>
            <div class="stats-grid">
                {"".join(stat_chips_context)}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    form_score, recent_form = _calculate_form_section(filtered_players, tactics_df)
    st.subheader("FORM (Last 10 Games)")
    st.write(f"Form Score: **{form_score:.1f}/100**")
    st.progress(min(max(form_score / 100.0, 0.0), 1.0))
    if recent_form.empty:
        st.info("Not enough recent match data for form trends.")
    else:
        form_timeline = recent_form.sort_values("date").copy()
        block_cols = st.columns(10)
        recent_blocks = form_timeline["match_form_score"].tail(10).tolist()
        for idx, score in enumerate(recent_blocks):
            color = "#31d17b" if score >= 70 else ("#f0be4f" if score >= 45 else "#ff6c7a")
            block_cols[idx].markdown(
                f"<div style='height:30px;border-radius:6px;background:{color};opacity:0.9;'></div>",
                unsafe_allow_html=True,
            )
        graph_col1, graph_col2, graph_col3 = st.columns(3)
        with graph_col1:
            st.caption("Form Score Momentum")
            st.line_chart(form_timeline.set_index("date")["match_form_score"], use_container_width=True)
        with graph_col2:
            st.caption("KPD Trend")
            st.area_chart(form_timeline.set_index("date")["kpd"], use_container_width=True)
        with graph_col3:
            winloss = form_timeline.copy()
            winloss["result"] = (winloss["wins"] > winloss["losses"]).astype(int)
            st.caption("Win/Loss Pattern")
            st.bar_chart(winloss.set_index("date")["result"], use_container_width=True)

        preview_cols = [
            "date",
            "map",
            "opponent_team",
            "kills",
            "deaths",
            "mvps",
            "kpd",
            "kda",
            "wins",
            "losses",
            "carried",
            "match_form_score",
        ]
        preview_cols = [c for c in preview_cols if c in recent_form.columns]
        st.dataframe(
            recent_form[preview_cols].sort_values("date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

    st.subheader("Performance Indicators")
    ind1, ind2, ind3 = st.columns(3)
    with ind1:
        st.write(f"Accuracy: **{avg_acc:.1f}%**")
        st.progress(min(max(avg_acc / 100, 0.0), 1.0))
    with ind2:
        st.write(f"Headshot %: **{avg_hs:.1f}%**")
        st.progress(min(max(avg_hs / 100, 0.0), 1.0))
    with ind3:
        kpd_scaled = min(max(avg_kpd / 2.5, 0.0), 1.0)
        st.write(f"KPD: **{avg_kpd:.2f}**")
        st.progress(kpd_scaled)

    st.caption(f"Total rounds played in filter: {rounds}")

    left, right = st.columns(2)
    with left:
        st.subheader("Kills by Map")
        kills_by_map = (
            filtered_players.groupby("map", as_index=False)["kills"].sum().sort_values("kills", ascending=False)
        )
        st.bar_chart(kills_by_map.set_index("map"))

    with right:
        st.subheader("Trend: Kills by Date")
        by_date = filtered_players.groupby("date", as_index=False)["kills"].sum().sort_values("date")
        st.line_chart(by_date.set_index("date"))

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
        "competition",
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
    st.dataframe(filtered_players[show_cols].sort_values("date", ascending=False), use_container_width=True, hide_index=True)


def _teams_tactical_breakdown(tactics_df: pd.DataFrame, player_df: pd.DataFrame) -> None:
    _inject_styles()
    _render_top_hero(
        active_page="tactics",
        subtitle="Team tactical breakdowns, map outcomes, and strategic performance context.",
    )

    recent_cutoff = pd.Timestamp.utcnow().tz_localize(None) - pd.Timedelta(days=10)
    player_recent = player_df[player_df["date"] >= recent_cutoff].copy()
    recent_match_ids = player_recent["match_id"].dropna().unique().tolist()
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

    recent_df = df[df["match_id"].isin(recent_match_ids) & (df["date"] >= recent_cutoff)].copy()
    recent_tactic_opts = sorted(recent_df["tactic_name"].dropna().unique().tolist())
    if not recent_tactic_opts:
        st.warning("No tactics have been used within the last 10 days.")
        return

    st.subheader("Tactics Filters")
    filter_cols = st.columns(5)
    side_opts = sorted(df["side"].dropna().unique().tolist())
    with filter_cols[0]:
        sides = _multiselect_filter("Side", side_opts, key="tactic_side")
    tier_opts = sorted(df["tier"].dropna().unique().tolist())
    with filter_cols[1]:
        tiers = _multiselect_filter("Tier", tier_opts, key="tactic_tier")

    comp_opts = sorted(df["competition"].dropna().unique().tolist())
    with filter_cols[2]:
        comps = _multiselect_filter("Event", comp_opts, key="tactic_event")

    opp_opts = sorted(df["opponent_team"].dropna().unique().tolist())
    with filter_cols[3]:
        opps = _multiselect_filter("Opponent", opp_opts, key="tactic_opp")
    round_type_opts = ["Pistol", "Eco", "Standard"]
    with filter_cols[4]:
        selected_round_types = st.multiselect(
            "Round Type",
            round_type_opts,
            default=round_type_opts,
            key="tactic_round_type_filter",
            placeholder="Select round types",
        )
        st.markdown(
            f'<div class="panel-muted">Round types: {len(selected_round_types)} selected</div>',
            unsafe_allow_html=True,
        )

    tactic_opts = recent_tactic_opts
    with st.container():
        selected_tactics = st.multiselect(
            "Tactics",
            tactic_opts,
            default=tactic_opts,
            key="tactic_name_filter",
            placeholder="Select tactics",
        )
        st.markdown(
            f'<div class="panel-muted">Tactics: {len(selected_tactics)} selected</div>',
            unsafe_allow_html=True,
        )

    if sides:
        df = df[df["side"].isin(sides)]
    if tiers:
        df = df[df["tier"].isin(tiers)]
    if comps:
        df = df[df["competition"].isin(comps)]
    if opps:
        df = df[df["opponent_team"].isin(opps)]
    df = df[df["tactic_name"].isin(selected_tactics)].copy()

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
    tactic_perf["trend"] = tactic_perf["trend_delta"].fillna(0).apply(
        lambda v: "Rising" if v >= 8 else ("Falling" if v <= -8 else "Stable")
    )

    def _confidence_label(row: pd.Series) -> str:
        uses = row["times_used"]
        win = row["win_pct"]
        if uses < 5:
            return "Unclear sample"
        if uses >= 10 and win >= 60:
            return "Strong"
        if uses >= 7 and win >= 52:
            return "Promising"
        if uses >= 10 and win < 45:
            return "Underperforming"
        return "Unclear sample"

    tactic_perf["confidence"] = tactic_perf.apply(_confidence_label, axis=1)

    def _action_label(row: pd.Series, avg_win: float) -> str:
        if row["win_pct"] > 60 and row["times_used"] >= 10:
            return "Keep"
        if row["win_pct"] < 45 and row["times_used"] >= 10:
            return "Stop using"
        if row["win_pct"] > 65 and row["times_used"] < 5:
            return "Test more"
        if row["usage_pct"] > 12 and row["win_pct"] < avg_win:
            return "Rework"
        if row["usage_pct"] < 8 and row["win_pct"] >= 58 and row["times_used"] >= 6:
            return "Use more"
        return "Monitor"

    overall_avg_win = float(tactic_perf["win_pct"].mean())
    tactic_perf["recommended_action"] = tactic_perf.apply(lambda r: _action_label(r, overall_avg_win), axis=1)
    tactic_perf["tags"] = tactic_perf.apply(
        lambda r: ", ".join(
            [
                tag
                for tag in [
                    "Reliable" if (r["confidence"] == "Strong") else None,
                    "Underused" if (r["recommended_action"] == "Use more") else None,
                    "Overused" if (r["recommended_action"] == "Rework") else None,
                    "Falling off" if (r["trend"] == "Falling") else None,
                    "Map-specific" if (r["round_share_pct"] > 25) else None,
                ]
                if tag
            ]
        ),
        axis=1,
    )

    selected_key = st.selectbox(
        "Selected tactic summary",
        tactic_perf.apply(lambda r: f'{r["tactic_name"]} | {r["map"]} | {r["side"]}', axis=1).tolist(),
        key="selected_tactic_summary",
    )
    selected_row = tactic_perf[
        tactic_perf.apply(lambda r: f'{r["tactic_name"]} | {r["map"]} | {r["side"]}', axis=1) == selected_key
    ].iloc[0]
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-muted">Selected tactic summary</div>
            <div class="panel-title">{selected_row["tactic_name"]}</div>
            <div class="stats-grid">
                <div class="stat-chip"><div class="stat-label">Map</div><div class="stat-value">{selected_row["map"]}</div></div>
                <div class="stat-chip"><div class="stat-label">Side</div><div class="stat-value">{selected_row["side"]}</div></div>
                <div class="stat-chip"><div class="stat-label">Times used</div><div class="stat-value">{int(selected_row["times_used"])}</div></div>
                <div class="stat-chip"><div class="stat-label">Rounds won</div><div class="stat-value">{int(selected_row["wins"])}</div></div>
                <div class="stat-chip"><div class="stat-label">Win rate</div><div class="stat-value">{selected_row["win_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Round share</div><div class="stat-value">{selected_row["round_share_pct"]:.1f}%</div></div>
                <div class="stat-chip"><div class="stat-label">Recent form (last 5)</div><div class="stat-value">{selected_row.get("recent_form_5", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">Recent form (last 10)</div><div class="stat-value">{selected_row.get("recent_form_10", "n/a")}</div></div>
                <div class="stat-chip"><div class="stat-label">Net round impact</div><div class="stat-value">{int(selected_row["net_rounds"])}</div></div>
                <div class="stat-chip"><div class="stat-label">Confidence</div><div class="stat-value">{selected_row["confidence"]}</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Tactic performance table")
    perf_cols = [
        "tactic_name",
        "map",
        "side",
        "times_used",
        "wins",
        "losses",
        "win_pct",
        "net_rounds",
        "usage_pct",
        "vs S tier win %",
        "vs A tier win %",
        "vs B tier win %",
        "vs C tier win %",
        "last_10_usage_win_pct",
        "trend",
        "confidence",
        "tags",
    ]
    st.dataframe(tactic_perf[perf_cols].sort_values(["win_pct", "times_used"], ascending=[False, False]), use_container_width=True, hide_index=True)

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
        trend_chart = (
            alt.Chart(selected_rounds)
            .transform_fold(["rolling_5", "rolling_10"], as_=["metric", "value"])
            .mark_line(point=True)
            .encode(
                x=alt.X("use_idx:Q", title="Match/Round order"),
                y=alt.Y("value:Q", title="Rolling win rate %"),
                color=alt.Color("metric:N", title="Window"),
                tooltip=["date", "match_id", "round_result", "rolling_5", "rolling_10"],
            )
            .properties(height=320)
        )
        outcome_scatter = (
            alt.Chart(selected_rounds)
            .mark_circle(size=65, opacity=0.65)
            .encode(
                x=alt.X("use_idx:Q", title="Use order"),
                y=alt.Y("round_result:Q", title="Round result (+1/-1)"),
                color=alt.condition("datum.round_result > 0", alt.value("#31d17b"), alt.value("#ff6c7a")),
                tooltip=["date", "match_id", "round_result"],
            )
            .properties(height=140)
        )
        st.altair_chart(outcome_scatter & trend_chart, use_container_width=True)

    st.subheader("Map + side split heatmap")
    heatmap_data = tactic_perf.copy()
    heatmap_data["map_side"] = heatmap_data["map"].astype(str) + " " + heatmap_data["side"].astype(str)
    heat = (
        alt.Chart(heatmap_data)
        .mark_rect()
        .encode(
            x=alt.X("map_side:N", title="Map + Side"),
            y=alt.Y("tactic_name:N", title="Tactic", sort="-x"),
            color=alt.Color("win_pct:Q", title="Win %", scale=alt.Scale(scheme="redyellowgreen")),
            tooltip=["tactic_name", "map", "side", "times_used", "win_pct", "round_share_pct"],
        )
        .properties(height=420)
    )
    st.altair_chart(heat, use_container_width=True)

    st.subheader("Round share vs success")
    scatter = (
        alt.Chart(tactic_perf)
        .mark_circle(opacity=0.8)
        .encode(
            x=alt.X("usage_pct:Q", title="Usage rate / round share %"),
            y=alt.Y("win_pct:Q", title="Win rate %"),
            size=alt.Size("times_used:Q", title="Times used"),
            color=alt.Color("confidence:N", title="Confidence"),
            tooltip=["tactic_name", "map", "side", "times_used", "usage_pct", "win_pct", "confidence", "recommended_action"],
        )
        .properties(height=380)
    )
    st.altair_chart(scatter, use_container_width=True)

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
        tier_chart = (
            alt.Chart(sel_tier)
            .mark_bar()
            .encode(
                x=alt.X("tier:N", sort=["S", "A", "B", "C"], title="Tier"),
                y=alt.Y("tier_win_pct:Q", title="Win rate %"),
                color=alt.Color("tier:N", legend=None),
                tooltip=["tier", "wins", "losses", "tier_win_pct", "tier_adjusted_score"],
            )
            .properties(height=300)
        )
        st.altair_chart(tier_chart, use_container_width=True)

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
    drill_cols = ["match_id", "opponent_team", "tier", "map", "side", "wins", "losses", "competition", "date"]
    st.dataframe(drilldown[drill_cols].sort_values("date", ascending=False), use_container_width=True, hide_index=True)


def _medisports_vs_breakdown(tactics_df: pd.DataFrame) -> None:
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
    match_results = _build_match_level_results(team_df)
    if match_results.empty:
        st.warning("No match-level results available.")
        return

    overall_matches = int(match_results["match_id"].nunique())
    overall_wins = int((match_results["match_result"] == "Win").sum())
    overall_losses = int((match_results["match_result"] == "Loss").sum())
    overall_draws = int((match_results["match_result"] == "Draw").sum())
    overall_rate = (overall_wins / max(overall_wins + overall_losses, 1)) * 100

    st.markdown(
        f"""
        <div class="panel-card">
            <div class="panel-muted">Overall Medisports form</div>
            <div class="stats-grid">
                <div class="stat-chip"><div class="stat-label">Matches</div><div class="stat-value">{overall_matches}</div></div>
                <div class="stat-chip"><div class="stat-label">Wins</div><div class="stat-value">{overall_wins}</div></div>
                <div class="stat-chip"><div class="stat-label">Losses</div><div class="stat-value">{overall_losses}</div></div>
                <div class="stat-chip"><div class="stat-label">Win Rate</div><div class="stat-value">{overall_rate:.1f}%</div></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.caption(f"Draws: {overall_draws}")

    vs_summary = (
        match_results.groupby("opponent_team", as_index=False)
        .agg(
            matches=("match_id", "nunique"),
            wins=("match_result", lambda s: int((s == "Win").sum())),
            losses=("match_result", lambda s: int((s == "Loss").sum())),
            draws=("match_result", lambda s: int((s == "Draw").sum())),
            round_wins=("round_wins", "sum"),
            round_losses=("round_losses", "sum"),
        )
        .assign(
            win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
            round_diff=lambda d: d["round_wins"] - d["round_losses"],
        )
        .sort_values(["win_rate_pct", "wins", "matches"], ascending=[False, False, False])
    )
    st.subheader("How Medisports Performs vs Each Team")
    st.dataframe(vs_summary, use_container_width=True, hide_index=True)
    spotlight = vs_summary.sort_values(["matches", "win_rate_pct"], ascending=[False, False]).head(3)
    if not spotlight.empty:
        st.markdown("#### Opponent Spotlight")
        spotlight_cols = st.columns(len(spotlight))
        for i, (_, row) in enumerate(spotlight.iterrows()):
            with spotlight_cols[i]:
                st.markdown(
                    f"""
                    <div class="panel-card">
                        <div class="panel-muted">vs {row["opponent_team"]}</div>
                        <div class="panel-title">{int(row["wins"])}W - {int(row["losses"])}L</div>
                        <div class="stat-label">Matches: {int(row["matches"])} | WR: {row["win_rate_pct"]:.1f}%</div>
                        <div class="stat-label">Round diff: {int(row["round_diff"]):+d}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.markdown("#### Match Wins/Losses by Opponent")
        wins_chart = (
            alt.Chart(vs_summary.sort_values("wins", ascending=False))
            .mark_bar(cornerRadiusEnd=4)
            .encode(
                x=alt.X("wins:Q", title="Wins"),
                y=alt.Y("opponent_team:N", sort="-x", title="Opponent"),
                color=alt.value("#57d28a"),
                tooltip=["opponent_team", "wins", "losses", "draws", "matches"],
            )
            .properties(height=380)
        )
        st.altair_chart(wins_chart, use_container_width=True)
    with chart_col_2:
        st.markdown("#### Win Rate by Team (min 1 match)")
        rate_chart = (
            alt.Chart(vs_summary)
            .mark_bar()
            .encode(
                x=alt.X("opponent_team:N", sort="-y", title="Opponent"),
                y=alt.Y("win_rate_pct:Q", title="Win Rate %"),
                color=alt.Color("matches:Q", title="Matches", scale=alt.Scale(scheme="blues")),
                tooltip=["opponent_team", "matches", "wins", "losses", "draws", "win_rate_pct", "round_diff"],
            )
            .properties(height=380)
        )
        st.altair_chart(rate_chart, use_container_width=True)

    st.markdown("#### Round Differential by Opponent")
    round_diff_chart = (
        alt.Chart(vs_summary.sort_values("round_diff", ascending=False))
        .mark_bar(cornerRadiusEnd=4)
        .encode(
            x=alt.X("round_diff:Q", title="Round Differential"),
            y=alt.Y("opponent_team:N", sort="-x", title="Opponent"),
            color=alt.condition(
                "datum.round_diff >= 0",
                alt.value("#44c06f"),
                alt.value("#e85c6b"),
            ),
            tooltip=["opponent_team", "round_wins", "round_losses", "round_diff", "matches"],
        )
        .properties(height=300)
    )
    st.altair_chart(round_diff_chart, use_container_width=True)

    st.subheader("Match-by-Match Results")
    result_filter = st.multiselect(
        "Result filter",
        ["Win", "Loss", "Draw"],
        default=["Win", "Loss", "Draw"],
        key="medisports_result_filter",
    )
    filtered_matches = match_results[match_results["match_result"].isin(result_filter)].sort_values("date", ascending=False)
    st.dataframe(
        filtered_matches[
            ["date", "opponent_team", "map", "competition", "round_wins", "round_losses", "round_diff", "match_result"]
        ],
        use_container_width=True,
        hide_index=True,
    )


def main() -> None:
    player_df, tactics_df, achievements_df = _load_data()

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    page = st.session_state["page"]
    if page == "profiles":
        _hltv_profile_view(player_df, tactics_df, achievements_df)
    elif page == "tactics":
        _teams_tactical_breakdown(tactics_df, player_df)
    elif page == "medisports_vs":
        _medisports_vs_breakdown(tactics_df)
    else:
        _home()


if __name__ == "__main__":
    main()
