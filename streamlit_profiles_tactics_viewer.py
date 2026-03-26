"""Grevs CPL pages built from local CSV data files.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

import base64
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
IMAGE_FOLDERS = {
    "competition": "competition_logos",
    "map": "map_images",
    "achievement": "Achievement_png",
    "team": "team_logos",
    "player": "player_photos",
}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
APP_ROOT = Path(__file__).parent


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
            padding: 12px 14px;
            background: rgba(18, 25, 40, 0.8);
            min-height: 108px;
        }
        .stat-label { color: #9da7bd; font-size: 0.78rem; }
        .stat-value { color: #f5f7fb; font-size: 1.55rem; font-weight: 800; line-height: 1.15; }
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
            display: grid;
            gap: 8px;
            margin-top: 8px;
        }
        .achievement-inline-item {
            border: 1px solid rgba(151, 166, 195, 0.28);
            border-radius: 10px;
            padding: 8px 10px;
            background: rgba(18, 25, 40, 0.72);
            display: flex;
            align-items: center;
            gap: 8px;
            flex-wrap: wrap;
        }
        .achievement-inline-item img {
            width: 28px;
            height: 28px;
            border-radius: 6px;
            object-fit: cover;
        }
        .achievement-inline-name {
            color: #f5f7fb;
            font-weight: 700;
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
            margin-bottom: 8px;
            font-size: 0.85rem;
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
    st.title("Grevs CPL Pages")
    st.write("Welcome! Choose a page below.")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("HLTV CPL Profile Viewer", use_container_width=True, type="primary"):
            st.session_state["page"] = "profiles"
            st.rerun()
    with col2:
        if st.button("Teams Tactical Breakdown", use_container_width=True):
            st.session_state["page"] = "tactics"
            st.rerun()
    with col3:
        if st.button("Medisports Vs Breakdown", use_container_width=True):
            st.session_state["page"] = "medisports_vs"
            st.rerun()


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
    st.title("HLTV CPL Profile Viewer")
    if st.button("← Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

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

    if filtered_players.empty:
        st.warning("No player rows match the current filters.")
        return

    first_row = filtered_players.sort_values("date", ascending=False).iloc[0]

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
        achievement_rows = []
        for _, ach_row in player_ach.iterrows():
            ach_tier = str(ach_row.get("achievement_tier", "-"))
            ach_tier_class = _achievement_tier_class(ach_tier)
            ach_image = ach_row.get("achievement_image")
            ach_image_html = (
                f"<img src='data:image/png;base64,{base64.b64encode(ach_image.read_bytes()).decode('utf-8')}'>"
                if ach_image
                else ""
            )
            achievement_rows.append(
                "<div class='achievement-inline-item'>"
                f"{ach_image_html}"
                f"<span class='achievement-inline-name'>{ach_row.get('achievement_name', '-')}</span>"
                f"<span class='achievement-tier {ach_tier_class}'>Tier {ach_tier}</span>"
                f"<span class='panel-muted'>({ach_row.get('season_name', '-')})</span>"
                "</div>"
            )
        achievement_inline_html = f"<div class='achievement-inline-list'>{''.join(achievement_rows)}</div>"

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
                            <div class="panel-muted">Role: Fragger · Country: - · Handedness: -</div>
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
        ach_cols = st.columns(3)
        for i, (_, ach_row) in enumerate(player_ach.iterrows()):
            with ach_cols[i % 3]:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                ach_image = ach_row.get("achievement_image")
                ach_tier = str(ach_row.get("achievement_tier", "-"))
                tier_class = _achievement_tier_class(ach_tier)
                st.markdown(
                    f'<div class="achievement-tier {tier_class}">Tier {ach_tier}</div>',
                    unsafe_allow_html=True,
                )
                if ach_image:
                    st.image(str(ach_image), use_container_width=True)
                st.markdown(
                    f"**{ach_row.get('achievement_name', '-') }**  \n"
                    f"Season: `{ach_row.get('season_name', '-')}`  \n"
                    f"Position: `{ach_row.get('position', '-')}`"
                )
                st.markdown("</div>", unsafe_allow_html=True)

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
    st.title("Teams Tactical Breakdown")
    if st.button("← Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

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

    tactic_opts = recent_tactic_opts
    with filter_cols[4]:
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
    df = df[df["tactic_name"].isin(selected_tactics)]

    if df.empty:
        st.warning("No tactics found for selected filters.")
        return

    uniqueness = (
        df.groupby("tactic_name", as_index=False)
        .agg(unique_sides=("side", "nunique"), unique_maps=("map", "nunique"))
        .sort_values(["unique_sides", "unique_maps", "tactic_name"], ascending=[False, False, True])
    )
    cross_side_count = int((uniqueness["unique_sides"] > 1).sum())
    cross_map_count = int((uniqueness["unique_maps"] > 1).sum())
    st.caption(
        f"Tactic uniqueness check: {cross_side_count} tactic(s) appear on multiple sides, "
        f"{cross_map_count} tactic(s) appear on multiple maps."
    )

    summary = (
        df.groupby(["tactic_name", "side", "map"], as_index=False)[["wins", "losses", "total_rounds"]]
        .sum()
        .assign(win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
        .sort_values(["win_rate_pct", "wins"], ascending=False)
    )
    image_index = _build_image_index()

    summary["competition_logo"] = (
        df.groupby(["tactic_name", "side", "map"])["competition"]
        .first()
        .map(lambda comp: _find_image(image_index, "competition", comp))
        .reindex(summary.set_index(["tactic_name", "side", "map"]).index)
        .values
    )
    summary["map_image"] = summary["map"].map(lambda map_name: _find_image(image_index, "map", map_name))

    top_row = summary.head(1)
    if not top_row.empty:
        best = top_row.iloc[0]
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-muted">Best current tactic</div>
                <div class="panel-title">{best["tactic_name"]}</div>
                <div class="stats-grid">
                    <div class="stat-chip"><div class="stat-label">Side</div><div class="stat-value">{best["side"]}</div></div>
                    <div class="stat-chip"><div class="stat-label">Wins</div><div class="stat-value">{int(best["wins"])}</div></div>
                    <div class="stat-chip"><div class="stat-label">Losses</div><div class="stat-value">{int(best["losses"])}</div></div>
                    <div class="stat-chip"><div class="stat-label">Rounds</div><div class="stat-value">{int(best["total_rounds"])}</div></div>
                    <div class="stat-chip"><div class="stat-label">Win Rate</div><div class="stat-value">{best["win_rate_pct"]:.1f}%</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.subheader("Top Tactical Outcomes")
    st.dataframe(
        summary.head(30),
        use_container_width=True,
        hide_index=True,
        column_config={
            "competition_logo": st.column_config.ImageColumn("Competition"),
            "map_image": st.column_config.ImageColumn("Map"),
        },
    )
    st.bar_chart(summary.head(15).set_index("tactic_name")["win_rate_pct"])
    st.subheader("Visual Tactical Insights")
    viz_col_1, viz_col_2 = st.columns(2)

    with viz_col_1:
        st.markdown("#### Heatmap: Win Rate by Tactic and Side")
        winrate_heat = (
            summary.pivot_table(
                index="tactic_name",
                columns="side",
                values="win_rate_pct",
                aggfunc="mean",
            )
            .fillna(0)
            .head(12)
        )
        if winrate_heat.empty:
            st.info("Not enough data to render the heatmap.")
        else:
            heatmap_data = (
                winrate_heat.reset_index()
                .melt(id_vars="tactic_name", var_name="side", value_name="win_rate_pct")
            )
            heatmap_chart = (
                alt.Chart(heatmap_data)
                .mark_rect(cornerRadius=3)
                .encode(
                    x=alt.X("side:N", title="Side"),
                    y=alt.Y("tactic_name:N", title="Tactic"),
                    color=alt.Color("win_rate_pct:Q", title="Win Rate %", scale=alt.Scale(scheme="viridis")),
                    tooltip=[
                        alt.Tooltip("tactic_name:N", title="Tactic"),
                        alt.Tooltip("side:N", title="Side"),
                        alt.Tooltip("win_rate_pct:Q", title="Win Rate %", format=".1f"),
                    ],
                )
                .properties(height=460, title="Top Tactics Win Rate Heatmap")
            )
            st.altair_chart(heatmap_chart, use_container_width=True)

    with viz_col_2:
        st.markdown("#### Altair: Wins vs Losses by Tactic")
        altair_data = summary.head(15).copy()
        if altair_data.empty:
            st.info("Not enough data to render the Altair chart.")
        else:
            altair_long = altair_data.melt(
                id_vars=["tactic_name", "side"],
                value_vars=["wins", "losses"],
                var_name="result",
                value_name="round_outcomes",
            )
            altair_chart = (
                alt.Chart(altair_long)
                .mark_bar()
                .encode(
                    x=alt.X("tactic_name:N", sort="-y", title="Tactic"),
                    y=alt.Y("round_outcomes:Q", title="Rounds"),
                    color=alt.Color("result:N", title="Outcome"),
                    tooltip=["tactic_name", "side", "result", "round_outcomes"],
                )
                .properties(height=430)
            )
            st.altair_chart(altair_chart, use_container_width=True)

    st.subheader("Opponent Impact")
    opponent_summary = (
        df.groupby(["opponent_team", "tactic_name"], as_index=False)[["wins", "losses"]]
        .sum()
        .assign(
            rounds_played=lambda d: d["wins"] + d["losses"],
            win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1),
        )
        .sort_values(["rounds_played", "win_rate_pct"], ascending=[False, False])
    )
    opp_col_1, opp_col_2 = st.columns(2)
    with opp_col_1:
        st.markdown("#### Win Rate by Opponent + Tactic")
        heat_source = opponent_summary[opponent_summary["rounds_played"] >= 2].copy()
        if heat_source.empty:
            st.info("Need more rounds against opponents to build this heatmap.")
        else:
            heat = (
                alt.Chart(heat_source)
                .mark_rect()
                .encode(
                    x=alt.X("opponent_team:N", title="Opponent"),
                    y=alt.Y("tactic_name:N", title="Tactic", sort="-x"),
                    color=alt.Color("win_rate_pct:Q", title="Win Rate %", scale=alt.Scale(scheme="redyellowgreen")),
                    tooltip=["opponent_team", "tactic_name", "wins", "losses", "win_rate_pct"],
                )
                .properties(height=460)
            )
            st.altair_chart(heat, use_container_width=True)
    with opp_col_2:
        st.markdown("#### Tactical Results vs Selected Opponent")
        opponent_opts = sorted(df["opponent_team"].dropna().unique().tolist())
        selected_opp = st.selectbox("Opponent team", opponent_opts, key="tactic_vs_opponent_select")
        opp_view = opponent_summary[opponent_summary["opponent_team"] == selected_opp].copy()
        if opp_view.empty:
            st.info("No tactic rows for this opponent.")
        else:
            st.dataframe(
                opp_view[["tactic_name", "wins", "losses", "rounds_played", "win_rate_pct"]].head(25),
                use_container_width=True,
                hide_index=True,
            )
            opp_bar = (
                alt.Chart(opp_view.head(15))
                .mark_bar()
                .encode(
                    x=alt.X("tactic_name:N", sort="-y", title="Tactic"),
                    y=alt.Y("win_rate_pct:Q", title="Win Rate %"),
                    color=alt.Color("win_rate_pct:Q", scale=alt.Scale(scheme="teals"), legend=None),
                    tooltip=["tactic_name", "wins", "losses", "rounds_played", "win_rate_pct"],
                )
                .properties(height=350)
            )
            st.altair_chart(opp_bar, use_container_width=True)

    st.subheader("Side Breakdown")
    side_summary = (
        df.groupby("side", as_index=False)[["wins", "losses", "total_rounds"]]
        .sum()
        .assign(win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
        .sort_values("win_rate_pct", ascending=False)
    )
    st.dataframe(side_summary, use_container_width=True, hide_index=True)

    red_col, blue_col = st.columns(2)
    for col, side_name in [(red_col, "Red"), (blue_col, "Blue")]:
        side_view = summary[summary["side"].astype(str).str.lower() == side_name.lower()].copy()
        with col:
            st.markdown(f"### {side_name} Side Tactics")
            if side_view.empty:
                st.info(f"No {side_name.lower()} side tactics for the selected filters.")
            else:
                st.dataframe(
                    side_view.head(15)[["tactic_name", "map", "wins", "losses", "total_rounds", "win_rate_pct"]],
                    use_container_width=True,
                    hide_index=True,
                )

    st.subheader("Map Breakdown")
    map_summary = (
        df.groupby(["map", "side"], as_index=False)[["wins", "losses", "total_rounds"]]
        .sum()
        .assign(win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
        .sort_values(["map", "side"])
    )
    st.dataframe(map_summary, use_container_width=True, hide_index=True)


def _medisports_vs_breakdown(tactics_df: pd.DataFrame) -> None:
    _inject_styles()
    st.title("Medisports Vs Breakdown")
    if st.button("← Back to Home"):
        st.session_state["page"] = "home"
        st.rerun()

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

    stats = st.columns(4)
    stats[0].metric("Matches", overall_matches)
    stats[1].metric("Wins", overall_wins)
    stats[2].metric("Losses", overall_losses)
    stats[3].metric("Win Rate", f"{overall_rate:.1f}%")
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

    chart_col_1, chart_col_2 = st.columns(2)
    with chart_col_1:
        st.markdown("#### Teams We Beat Most")
        st.bar_chart(vs_summary.set_index("opponent_team")["wins"])
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
