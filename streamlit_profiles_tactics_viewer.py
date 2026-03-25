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
        folder = DATA_DIR / folder_name
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
    selected_tiers = filter_cols[0].multiselect("Tier of Team", tier_options, default=tier_options)

    event_options = sorted(filtered_players["competition"].dropna().unique().tolist())
    selected_events = filter_cols[1].multiselect("Event", event_options, default=event_options)

    opp_options = sorted(filtered_players["opponent_team"].dropna().unique().tolist())
    selected_opp = filter_cols[2].multiselect("Opponent", opp_options, default=opp_options)

    side_options = sorted(tactics_df["side"].dropna().unique().tolist()) if "side" in tactics_df else []
    selected_sides = filter_cols[3].multiselect("Side (Red/Blue)", side_options, default=side_options)

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

    kills = int(filtered_players["kills"].sum())
    deaths = int(filtered_players["deaths"].sum())
    mvps = int(filtered_players["mvps"].sum())
    damage = int(filtered_players["damage"].sum())
    rounds = int(filtered_players["rounds_played"].sum())
    kd_ratio = (kills / deaths) if deaths else 0.0
    avg_acc = float(filtered_players["accuracy_pct"].mean()) if not filtered_players.empty else 0.0
    avg_hs = float(filtered_players["hs_pct"].mean()) if not filtered_players.empty else 0.0
    avg_kpd = float(filtered_players["kpd"].mean()) if not filtered_players.empty else 0.0

    stat_cols = st.columns(6)
    stat_cols[0].metric("Matches", filtered_players["match_id"].nunique())
    stat_cols[1].metric("Kills", kills)
    stat_cols[2].metric("Deaths", deaths)
    stat_cols[3].metric("K/D", f"{kd_ratio:.2f}")
    stat_cols[4].metric("MVPs", mvps)
    stat_cols[5].metric("Damage", f"{damage:,}")

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
        st.dataframe(
            player_ach,
            use_container_width=True,
            hide_index=True,
            column_config={
                "achievement_image": st.column_config.ImageColumn("Achievement"),
            },
        )

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
    sides = filter_cols[0].multiselect("Side", side_opts, default=side_opts)
    tier_opts = sorted(df["tier"].dropna().unique().tolist())
    tiers = filter_cols[1].multiselect("Tier", tier_opts, default=tier_opts)

    comp_opts = sorted(df["competition"].dropna().unique().tolist())
    comps = filter_cols[2].multiselect("Event", comp_opts, default=comp_opts)

    opp_opts = sorted(df["opponent_team"].dropna().unique().tolist())
    opps = filter_cols[3].multiselect("Opponent", opp_opts, default=opp_opts)

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
