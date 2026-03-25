"""Grevs CPL pages built from local CSV data files.

Run:
    streamlit run streamlit_profiles_tactics_viewer.py
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="Grevs CPL Pages", layout="wide")

DATA_DIR = Path(__file__).parent / "data"
PLAYER_CSV = DATA_DIR / "PlayerDataMatser.csv"
TACTICS_CSV = DATA_DIR / "TacticsDataMaster.csv"
ACHIEVEMENTS_CSV = DATA_DIR / "Achievements.csv"


def _coerce_numeric(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    for col in columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    return df


@st.cache_data(show_spinner=False)
def _load_data() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    players = pd.read_csv(PLAYER_CSV)
    tactics = pd.read_csv(TACTICS_CSV)

    # Drop accidental empty trailing columns from CSV export.
    tactics = tactics.loc[:, ~tactics.columns.str.contains(r"^Unnamed")]
    tactics = tactics.loc[:, tactics.columns.astype(str).str.strip() != ""]

    achievements_raw = pd.read_csv(ACHIEVEMENTS_CSV)
    if len(achievements_raw.columns) == 1:
        split = achievements_raw.iloc[:, 0].astype(str).str.split("|", expand=True)
        split.columns = [
            "player",
            "achievement_name",
            "achievement_link",
            "achievement_tier",
            "season_name",
            "position",
        ]
        achievements = split.apply(lambda s: s.str.strip() if s.dtype == object else s)
    else:
        achievements = achievements_raw

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

    st.sidebar.header("Player Filters")
    tier_options = sorted(filtered_players["tier"].dropna().unique().tolist())
    selected_tiers = st.sidebar.multiselect("Tier of Team", tier_options, default=tier_options)

    event_options = sorted(filtered_players["competition"].dropna().unique().tolist())
    selected_events = st.sidebar.multiselect("Event", event_options, default=event_options)

    opp_options = sorted(filtered_players["opponent_team"].dropna().unique().tolist())
    selected_opp = st.sidebar.multiselect("Opponent", opp_options, default=opp_options)

    side_options = sorted(tactics_df["side"].dropna().unique().tolist()) if "side" in tactics_df else []
    selected_sides = st.sidebar.multiselect("Side (Red/Blue)", side_options, default=side_options)

    date_range = st.sidebar.date_input(
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

    players = sorted(player_df["player"].dropna().unique().tolist())
    selected_player = st.selectbox("Pick a player", players)

    filtered_players, filtered_tactics = _apply_shared_filters(player_df, tactics_df, selected_player)

    if filtered_players.empty:
        st.warning("No player rows match the current filters.")
        return

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
    player_ach = achievements_df[achievements_df["player"].astype(str).str.contains(selected_player, case=False, na=False)]
    if player_ach.empty:
        st.info("No achievements found for this player.")
    else:
        st.dataframe(player_ach, use_container_width=True, hide_index=True)

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

    st.sidebar.header("Tactics Filters")
    side_opts = sorted(df["side"].dropna().unique().tolist())
    sides = st.sidebar.multiselect("Side", side_opts, default=side_opts)
    tier_opts = sorted(df["tier"].dropna().unique().tolist())
    tiers = st.sidebar.multiselect("Tier", tier_opts, default=tier_opts)

    comp_opts = sorted(df["competition"].dropna().unique().tolist())
    comps = st.sidebar.multiselect("Event", comp_opts, default=comp_opts)

    opp_opts = sorted(df["opponent_team"].dropna().unique().tolist())
    opps = st.sidebar.multiselect("Opponent", opp_opts, default=opp_opts)

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

    st.subheader("Top Tactical Outcomes")
    st.dataframe(summary.head(30), use_container_width=True, hide_index=True)
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
