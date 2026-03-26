"""Grevs CPL pages built from local CSV data files.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

import base64
from pathlib import Path
import re

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
            margin-top: 10px;
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
            grid-template-columns: 170px 1.5fr 1fr;
            gap: 14px;
            align-items: stretch;
        }
        .portrait-frame {
            border: 1px solid rgba(104, 143, 210, 0.6);
            border-radius: 14px;
            padding: 8px;
            background: linear-gradient(180deg, rgba(41, 59, 97, 0.35), rgba(15, 21, 34, 0.65));
            box-shadow: 0 0 18px rgba(58, 102, 189, 0.24);
        }
        .portrait-strip {
            margin-top: 8px;
            font-size: 0.74rem;
            color: #b5c3e2;
            display: grid;
            gap: 3px;
        }
        .identity-card {
            border: 1px solid rgba(151, 166, 195, 0.35);
            border-radius: 12px;
            padding: 14px;
            background: rgba(14, 20, 32, 0.78);
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
            grid-template-columns: repeat(2, minmax(0, 1fr));
            gap: 8px;
            margin-top: 10px;
        }
        .identity-kv {
            border: 1px solid rgba(151, 166, 195, 0.28);
            border-radius: 10px;
            padding: 8px 10px;
            background: rgba(18, 25, 40, 0.72);
            min-height: 64px;
        }
        .identity-kv-value {
            font-size: 1.2rem;
            color: #f5f7fb;
            font-weight: 800;
            line-height: 1.15;
        }
        .hero-grevscore {
            border: 1px solid rgba(118, 168, 255, 0.45);
            border-radius: 14px;
            padding: 14px;
            background: linear-gradient(120deg, rgba(54, 87, 155, 0.45) 0%, rgba(35, 57, 103, 0.2) 100%);
            box-shadow: 0 0 18px rgba(54, 116, 255, 0.22);
        }
        .hero-grevscore-label {
            color: #b8caf0;
            font-size: 0.82rem;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }
        .hero-grevscore-value {
            color: #f5f8ff;
            font-size: 2.6rem;
            font-weight: 900;
            line-height: 1.05;
        }
        .hero-grevscore-tier {
            font-size: 0.8rem;
            color: #d6e2ff;
            margin-top: 3px;
            letter-spacing: 0.04em;
        }
        .gauge-wrap {
            margin-top: 10px;
            position: relative;
            width: 100%;
            height: 120px;
        }
        .gauge-arc {
            position: absolute;
            left: 50%;
            top: 56px;
            width: 170px;
            height: 86px;
            transform: translateX(-50%);
            border-radius: 170px 170px 0 0;
            border: 11px solid rgba(0, 0, 0, 0);
            border-bottom: 0;
            background:
                linear-gradient(90deg, #ff6c7a 0%, #f0be4f 50%, #31d17b 100%);
            -webkit-mask: radial-gradient(circle at bottom, transparent 53px, #000 54px);
            mask: radial-gradient(circle at bottom, transparent 53px, #000 54px);
        }
        .gauge-needle {
            position: absolute;
            left: 50%;
            top: 73px;
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
            top: 132px;
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
            margin-top: 18px;
        }
        .section-label {
            font-size: 0.78rem;
            color: #9eb0d4;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-top: 8px;
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


@st.cache_data(show_spinner=False)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    players = pd.read_csv(PLAYER_CSV)
    tactics = pd.read_csv(TACTICS_CSV)

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
    return (
        f'<div class="stat-chip"><div class="stat-label">{label}</div>'
        f'<div class="stat-value">{display}</div>'
        f'<div class="stat-trend {tier_class}">{arrow} {meter:.0f}/100</div>'
        f'<div class="stat-meter"><div class="stat-meter-fill" style="width:{meter:.0f}%"></div></div></div>'
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
    st.title("Grevs CPL Pages")
    st.write("Welcome! Choose a page below.")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("HLTV CPL Profile Viewer", use_container_width=True, type="primary"):
            st.session_state["page"] = "profiles"
            st.rerun()
    with col2:
        if st.button("Teams Tactical Breakdown", use_container_width=True):
            st.session_state["page"] = "tactics"
            st.rerun()


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
    competition_logo = _find_image(image_index, "competition", first_row.get("competition"))

    metrics = _calc_player_card_metrics(filtered_players, filtered_tactics)
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

    stat_chips = [
        f'<div class="stat-chip"><div class="stat-label">Matches</div><div class="stat-value">{int(metrics["matches"])}</div></div>',
        _build_stat_chip("K/D", f'{metrics["kd"]:.2f}', metrics["kd"], 0.7, 1.3),
        _build_stat_chip("KDA", f'{metrics["kda"]:.2f}', metrics["kda"], 1.0, 2.2),
        f'<div class="stat-chip"><div class="stat-label">K / D / A</div><div class="stat-value">{kills}/{deaths}/{assists}</div></div>',
        _build_stat_chip("DPM", f'{metrics["dpm"]:.1f}', metrics["dpm"], 1800, 3600),
        _build_stat_chip("Acc%", f'{metrics["acc"]:.1f}%', metrics["acc"], 45, 80),
        _build_stat_chip("KPM", f'{metrics["kpm"]:.2f}', metrics["kpm"], 0.45, 1.0),
        _build_stat_chip("Impact", f'{metrics["impact"]:.1f}', metrics["impact"], 45, 95),
        _build_stat_chip("Avg KPD", f"{avg_kpd:.2f}", avg_kpd, 0.8, 1.5),
    ]
    team_logo_html = ""
    if team_logo:
        team_logo_html = (
            f'<img style="width:42px;border-radius:8px;vertical-align:middle;margin-right:8px;" src="data:image/png;base64,{base64.b64encode(team_logo.read_bytes()).decode("utf-8")}">'
        )
    competition_logo_html = ""
    if competition_logo:
        competition_logo_html = (
            f'<img style="width:34px;border-radius:8px;vertical-align:middle;margin-right:6px;" src="data:image/png;base64,{base64.b64encode(competition_logo.read_bytes()).decode("utf-8")}">'
        )
    st.markdown(
        f"""
        <div class="panel-card">
            <div class="top-identity-grid">
                <div class="portrait-frame">
                    {"<img class='player-headshot' src='data:image/png;base64," + base64.b64encode(player_image.read_bytes()).decode("utf-8") + "'>" if player_image else "<div class='panel-muted'>No portrait found.</div>"}
                    <div class="portrait-strip">
                        <div>Team: <strong>{first_row.get("my_team", "-")}</strong></div>
                        <div>Matches: <strong>{int(metrics["matches"])}</strong></div>
                        <div>Form: <strong>{score_tier}</strong></div>
                    </div>
                </div>
                <div class="identity-card">
                    <div class="profile-label">Player Profile</div>
                    <div class="profile-name">{selected_player}</div>
                    <div class="panel-muted">{team_logo_html}<span>{first_row.get("my_team", "-")}</span></div>
                    <div class="identity-grid">
                        <div class="identity-kv">
                            <div class="profile-label">Role</div>
                            <div class="identity-kv-value">{first_row.get("role", "Player")}</div>
                        </div>
                        <div class="identity-kv">
                            <div class="profile-label">Record</div>
                            <div class="identity-kv-value">{kills}/{deaths}/{assists}</div>
                        </div>
                        <div class="identity-kv">
                            <div class="profile-label">Best Map</div>
                            <div class="identity-kv-value">{filtered_players.groupby("map")["kills"].sum().sort_values(ascending=False).index[0] if "map" in filtered_players.columns and not filtered_players.empty else "-"}</div>
                        </div>
                        <div class="identity-kv">
                            <div class="profile-label">Latest Event</div>
                            <div class="identity-kv-value">{first_row.get("competition", "-")}</div>
                        </div>
                    </div>
                </div>
                <div class="hero-grevscore">
                    <div class="hero-grevscore-label">GrevScore</div>
                    <div class="hero-grevscore-value">{metrics["grevscore"]:.2f}</div>
                    <div class="hero-grevscore-tier">{score_tier}</div>
                    <div class="gauge-wrap">
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
                    <div class="section-label">{competition_logo_html}{first_row.get("competition", "-")}</div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="panel-card"><div class="section-label">Core Performance</div><div class="stats-grid">', unsafe_allow_html=True)
    st.markdown("".join(stat_chips), unsafe_allow_html=True)
    st.markdown("</div></div>", unsafe_allow_html=True)

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
    player_ach = achievements_df[
        achievements_df["player"].astype(str).str.contains(selected_player, case=False, na=False)
    ].copy()
    if player_ach.empty:
        st.info("No achievements found for this player.")
    else:
        player_ach["achievement_image"] = player_ach.apply(
            lambda row: _find_achievement_image(
                image_index,
                row.get("achievement_link"),
                row.get("achievement_name"),
            ),
            axis=1,
        )
        ach_cols = st.columns(3)
        for i, (_, ach_row) in enumerate(player_ach.iterrows()):
            with ach_cols[i % 3]:
                st.markdown('<div class="panel-card">', unsafe_allow_html=True)
                ach_image = ach_row.get("achievement_image")
                if ach_image:
                    st.image(str(ach_image), use_container_width=True)
                st.markdown(
                    f"**{ach_row.get('achievement_name', 'Achievement')}**  \n"
                    f"Tier: `{ach_row.get('achievement_tier', '-')}`  \n"
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

    df = tactics_df.merge(
        player_df[["match_id", "tier"]].drop_duplicates(),
        on="match_id",
        how="left",
    )

    st.subheader("Tactics Filters")
    filter_cols = st.columns(4)
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

    if sides:
        df = df[df["side"].isin(sides)]
    if tiers:
        df = df[df["tier"].isin(tiers)]
    if comps:
        df = df[df["competition"].isin(comps)]
    if opps:
        df = df[df["opponent_team"].isin(opps)]

    if df.empty:
        st.warning("No tactics found for selected filters.")
        return

    summary = (
        df.groupby(["tactic_name", "side"], as_index=False)[["wins", "losses", "total_rounds"]]
        .sum()
        .assign(win_rate_pct=lambda d: (d["wins"] / (d["wins"] + d["losses"]).clip(lower=1) * 100).round(1))
        .sort_values(["win_rate_pct", "wins"], ascending=False)
    )
    image_index = _build_image_index()

    summary["competition_logo"] = (
        df.groupby("tactic_name")["competition"]
        .first()
        .map(lambda comp: _find_image(image_index, "competition", comp))
        .reindex(summary["tactic_name"])
        .values
    )
    summary["map_image"] = (
        df.groupby("tactic_name")["map"]
        .first()
        .map(lambda map_name: _find_image(image_index, "map", map_name))
        .reindex(summary["tactic_name"])
        .values
    )

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


def main() -> None:
    player_df, tactics_df, achievements_df = _load_data()

    if "page" not in st.session_state:
        st.session_state["page"] = "home"

    page = st.session_state["page"]
    if page == "profiles":
        _hltv_profile_view(player_df, tactics_df, achievements_df)
    elif page == "tactics":
        _teams_tactical_breakdown(tactics_df, player_df)
    else:
        _home()


if __name__ == "__main__":
    main()
