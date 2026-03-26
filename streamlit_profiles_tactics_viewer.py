"""Grevs CPL pages built from local CSV data files.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

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
            background: linear-gradient(145deg, #131722 0%, #0e1118 100%);
            border: 1px solid rgba(151, 166, 195, 0.35);
            border-radius: 14px;
            padding: 16px 18px;
            margin-bottom: 12px;
            box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
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
            gap: 8px;
            margin-top: 8px;
        }
        .stat-chip {
            border: 1px solid rgba(151, 166, 195, 0.35);
            border-radius: 10px;
            padding: 8px 10px;
            background: rgba(18, 25, 40, 0.8);
        }
        .stat-label { color: #9da7bd; font-size: 0.78rem; }
        .stat-value { color: #f5f7fb; font-size: 1rem; font-weight: 650; }
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
    selected = st.multiselect(label, options, default=options, key=key)
    if not selected:
        st.caption(f"Selected {label}: None")
        return []
    if len(selected) == len(options):
        st.caption(f"Selected {label}: All")
    else:
        st.caption(f"Selected {label}: {', '.join(selected)}")
    return selected


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

    impact = (kd * 45.0) + (kpm * 35.0) + (acc * 0.2) + (win_rate * 0.2)
    grevscore = min(max((impact + (dpm / 60.0)) / 2.0, 0.0), 100.0)
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
        "grevscore": grevscore,
    }


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

    st.subheader("Player Filters")
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

    filtered_players, filtered_tactics = _apply_shared_filters(player_df, tactics_df, selected_player)
    image_index = _build_image_index()

    if filtered_players.empty:
        st.warning("No player rows match the current filters.")
        return

    first_row = filtered_players.sort_values("date", ascending=False).iloc[0]

    header_cols = st.columns([1, 2, 2, 2])
    player_image = _find_image(image_index, "player", selected_player)
    with header_cols[0]:
        if player_image:
            st.image(str(player_image), caption=selected_player, use_container_width=True)
    with header_cols[1]:
        team_logo = _find_image(image_index, "team", first_row.get("my_team"))
        if team_logo:
            st.image(str(team_logo), caption=str(first_row.get("my_team", "")), use_container_width=True)
    with header_cols[2]:
        competition_logo = _find_image(image_index, "competition", first_row.get("competition"))
        if competition_logo:
            st.image(str(competition_logo), caption=str(first_row.get("competition", "")), use_container_width=True)
    with header_cols[3]:
        map_image = _find_image(image_index, "map", first_row.get("map"))
        if map_image:
            st.image(str(map_image), caption=str(first_row.get("map", "")), use_container_width=True)

    metrics = _calc_player_card_metrics(filtered_players, filtered_tactics)
    kills = int(metrics["kills"])
    deaths = int(metrics["deaths"])
    assists = int(metrics["assists"])
    damage = int(filtered_players["damage"].sum())
    rounds = int(filtered_players["rounds_played"].sum())
    avg_acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0
    avg_hs = float(filtered_players["hs_pct"].mean()) if not filtered_players.empty else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if not filtered_players.empty else 0.0

    card_col1, card_col2 = st.columns([1, 4])
    with card_col1:
        if player_image:
            st.image(str(player_image), use_container_width=True)
    with card_col2:
        st.markdown(
            f"""
            <div class="panel-card">
                <div class="panel-muted">Player card</div>
                <div class="panel-title">{selected_player}</div>
                <div class="stats-grid">
                    <div class="stat-chip"><div class="stat-label">Matches</div><div class="stat-value">{int(metrics["matches"])}</div></div>
                    <div class="stat-chip"><div class="stat-label">K/D</div><div class="stat-value">{metrics["kd"]:.2f}</div></div>
                    <div class="stat-chip"><div class="stat-label">KDA</div><div class="stat-value">{metrics["kda"]:.2f}</div></div>
                    <div class="stat-chip"><div class="stat-label">K / D / A</div><div class="stat-value">{kills}/{deaths}/{assists}</div></div>
                    <div class="stat-chip"><div class="stat-label">DPM</div><div class="stat-value">{metrics["dpm"]:.1f}</div></div>
                    <div class="stat-chip"><div class="stat-label">Acc%</div><div class="stat-value">{metrics["acc"]:.1f}%</div></div>
                    <div class="stat-chip"><div class="stat-label">KPM</div><div class="stat-value">{metrics["kpm"]:.2f}</div></div>
                    <div class="stat-chip"><div class="stat-label">Impact</div><div class="stat-value">{metrics["impact"]:.1f}</div></div>
                    <div class="stat-chip"><div class="stat-label">Grevscore</div><div class="stat-value">{metrics["grevscore"]:.1f}</div></div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
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
