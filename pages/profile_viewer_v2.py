from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import base64
import html
import math
import re

import pandas as pd
import streamlit as st


ROOT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT_DIR / "data"
PLAYER_MATCHES_CSV = DATA_DIR / "PlayerDataMatser.csv"
PLAYER_META_CSV_CANDIDATES = [
    DATA_DIR / "play.csv",
    DATA_DIR / "Play.csv",
    DATA_DIR / "players.csv",
]
ACHIEVEMENTS_CSV = DATA_DIR / "Achievements.csv"
PLAYER_PHOTO_DIR = ROOT_DIR / "player_photos"


@dataclass
class PlayerSnapshot:
    name: str
    team: str
    role: str
    country: str
    fame: int
    matches: int
    maps: int
    competitions: int
    avg_kills: float
    avg_deaths: float
    kpd: float
    hs_pct: float
    accuracy_pct: float
    avg_damage: float
    mvp_rate: float
    form_delta: float
    grevscore: float
    percentile: float


@st.cache_data(show_spinner=False)
def load_player_matches() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_MATCHES_CSV)
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    numeric_cols = ["kills", "deaths", "mvps", "kpd", "accuracy_pct", "hs_pct", "damage", "rounds_played"]
    for col in numeric_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["player", "date"]).copy()
    return df


@st.cache_data(show_spinner=False)
def load_player_meta() -> pd.DataFrame:
    for csv_path in PLAYER_META_CSV_CANDIDATES:
        if not csv_path.exists():
            continue
        raw = pd.read_csv(csv_path)
        if raw.empty:
            continue
        col = raw.columns[0]
        lines = raw[col].astype(str)
        records: list[dict[str, str | int]] = []
        for line in lines:
            tokens = re.findall(r'"([^"]*)"|(\S+)', line)
            flat = [a or b for a, b in tokens]
            if len(flat) < 5:
                continue
            player_id, name, country, role, fame = flat[0], flat[1], flat[2], flat[3], flat[4]
            try:
                fame_value = int(float(fame))
            except ValueError:
                fame_value = 0
            records.append(
                {
                    "player_id": player_id,
                    "name": name,
                    "country": country,
                    "role": role,
                    "fame": fame_value,
                }
            )
        if records:
            return pd.DataFrame(records)
    return pd.DataFrame(columns=["player_id", "name", "country", "role", "fame"])


@st.cache_data(show_spinner=False)
def load_achievements() -> pd.DataFrame:
    raw = pd.read_csv(ACHIEVEMENTS_CSV)
    if raw.empty:
        return pd.DataFrame(columns=["player", "achievement_name", "achievement_link", "achievement_tier", "season_name", "position"])
    col = raw.columns[0]
    split = raw[col].astype(str).str.split("|", expand=True)
    if split.shape[1] >= 7:
        ach = pd.DataFrame(
            {
                "player": split[0].fillna("").str.strip() + " | " + split[1].fillna("").str.strip(),
                "achievement_name": split[2],
                "achievement_link": split[3],
                "achievement_tier": split[4],
                "season_name": split[5],
                "position": split[6],
            }
        )
    else:
        ach = split.iloc[:, :6].copy()
        ach.columns = ["player", "achievement_name", "achievement_link", "achievement_tier", "season_name", "position"]
    return ach.fillna("")


def clean_player_key(name: str) -> str:
    key = re.sub(r"[^a-z0-9]+", "", name.lower())
    return key


def find_player_photo(player_name: str) -> Path | None:
    if not PLAYER_PHOTO_DIR.exists():
        return None
    key = clean_player_key(player_name)
    for file in PLAYER_PHOTO_DIR.iterdir():
        if file.is_file() and clean_player_key(file.stem).find(key) >= 0:
            return file
    for file in PLAYER_PHOTO_DIR.iterdir():
        if file.is_file() and key in clean_player_key(file.stem):
            return file
    return None


def image_to_data_uri(path: Path | None) -> str:
    if path is None or not path.exists():
        return ""
    suffix = path.suffix.lower().replace(".", "") or "png"
    data = base64.b64encode(path.read_bytes()).decode("utf-8")
    return f"data:image/{suffix};base64,{data}"


def build_player_snapshot(player_name: str, player_frame: pd.DataFrame, base_frame: pd.DataFrame, meta: pd.DataFrame) -> PlayerSnapshot:
    player_df = player_frame[player_frame["player"] == player_name].sort_values("date")
    if player_df.empty:
        return PlayerSnapshot(player_name, "-", "-", "-", 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 50, 0)

    last_n = min(5, len(player_df))
    recent = player_df.tail(last_n)

    long_kpd = player_df["kpd"].mean()
    recent_kpd = recent["kpd"].mean()
    form_delta = recent_kpd - long_kpd

    score_components = [
        min(100, max(0, recent["kpd"].mean() * 42)),
        min(100, max(0, recent["accuracy_pct"].mean())),
        min(100, max(0, recent["hs_pct"].mean())),
        min(100, max(0, recent["mvps"].mean() * 9)),
    ]
    grevscore = sum(score_components) / len(score_components)

    meta_row = meta[meta["name"] == player_name]
    role = meta_row.iloc[0]["role"] if not meta_row.empty else "Unknown"
    country = meta_row.iloc[0]["country"] if not meta_row.empty else "Unknown"
    fame = int(meta_row.iloc[0]["fame"]) if not meta_row.empty else 0

    all_player_scores = (
        base_frame.groupby("player")
        .agg(kpd=("kpd", "mean"), hs=("hs_pct", "mean"), acc=("accuracy_pct", "mean"), mvp=("mvps", "mean"))
        .fillna(0)
    )
    all_player_scores["score"] = (
        all_player_scores["kpd"].clip(0, 2.5) * 32
        + all_player_scores["hs"].clip(0, 100) * 0.16
        + all_player_scores["acc"].clip(0, 100) * 0.16
        + all_player_scores["mvp"].clip(0, 10) * 2.4
    )
    rank = all_player_scores["score"].rank(pct=True).to_dict().get(player_name, 0.5)

    return PlayerSnapshot(
        name=player_name,
        team=str(player_df["my_team"].mode().iloc[0]),
        role=str(role),
        country=str(country),
        fame=fame,
        matches=player_df["match_id"].nunique(),
        maps=player_df["map"].nunique(),
        competitions=player_df["competition"].nunique(),
        avg_kills=float(player_df["kills"].mean()),
        avg_deaths=float(player_df["deaths"].mean()),
        kpd=float(player_df["kpd"].mean()),
        hs_pct=float(player_df["hs_pct"].mean()),
        accuracy_pct=float(player_df["accuracy_pct"].mean()),
        avg_damage=float(player_df["damage"].mean()),
        mvp_rate=float((player_df["mvps"] > 0).mean() * 100),
        form_delta=float(form_delta),
        grevscore=float(grevscore),
        percentile=float(rank * 100),
    )


def gauge_html(score: float) -> str:
    score = max(0.0, min(100.0, score))
    angle = (score / 100) * 180 - 90
    rad = math.radians(angle)
    x = 50 + 40 * math.cos(rad)
    y = 50 + 40 * math.sin(rad)
    return f"""
    <svg viewBox=\"0 0 100 60\" class=\"gauge\">
      <path d=\"M10 50 A40 40 0 0 1 90 50\" fill=\"none\" stroke=\"#2a3550\" stroke-width=\"10\"/>
      <path d=\"M10 50 A40 40 0 0 1 90 50\" fill=\"none\" stroke=\"url(#grad)\" stroke-width=\"10\" stroke-dasharray=\"{2.51*score} 999\"/>
      <defs>
        <linearGradient id=\"grad\" x1=\"0\" y1=\"0\" x2=\"1\" y2=\"0\">
          <stop offset=\"0%\" stop-color=\"#ff6b6b\"/>
          <stop offset=\"50%\" stop-color=\"#ffd166\"/>
          <stop offset=\"100%\" stop-color=\"#4bf0a1\"/>
        </linearGradient>
      </defs>
      <line x1=\"50\" y1=\"50\" x2=\"{x:.1f}\" y2=\"{y:.1f}\" stroke=\"#f0f5ff\" stroke-width=\"2.5\" />
      <circle cx=\"50\" cy=\"50\" r=\"2.6\" fill=\"#f0f5ff\" />
    </svg>
    """


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        .stApp { background: radial-gradient(circle at 10% 0%, #172236 0%, #080c14 38%, #060910 100%); color: #e7edf7; }
        .block-container { max-width: 1180px; margin: 0 auto; padding-top: 1.2rem; }
        .v2-title { font-size: 1.65rem; font-weight: 800; margin-bottom: .2rem; }
        .v2-sub { color: #9caad0; margin-bottom: 1rem; font-size: .92rem; }
        .card-grid { display:grid; grid-template-columns: 1.3fr 1fr 1fr; gap: 12px; margin: 8px 0 16px 0; align-items: stretch; }
        .v2-card { background: linear-gradient(160deg, rgba(18,25,40,.95), rgba(9,14,24,.96)); border:1px solid rgba(126,151,194,.28); border-radius:14px; padding:14px; box-shadow: 0 10px 24px rgba(0,0,0,.35); min-height: 228px; }
        .player-card { display:flex; flex-direction:column; }
        .player-wrap { display:grid; grid-template-columns: 92px minmax(0, 1fr); gap:13px; align-items: start; height:100%; }
        .headshot { width:92px; height:92px; object-fit:cover; border-radius:12px; border:1px solid rgba(176,198,240,.35); }
        .player-core { display:flex; flex-direction:column; gap:8px; min-width:0; }
        .p-name { font-size:1.25rem; font-weight:800; color:#f6f9ff; margin:0; }
        .p-meta { color:#96a7cb; font-size:.8rem; margin:.08rem 0 .12rem; line-height:1.25; }
        .mini-facts { display:grid; grid-template-columns: repeat(2, minmax(96px, 1fr)); gap:8px; margin-top:1px; }
        .fact { border:1px solid rgba(130,153,193,.3); border-radius:9px; padding:7px 9px; background:rgba(13,19,31,.72); min-width:0; }
        .fact-k { color:#8fa5d3; font-size:.66rem; line-height:1.05; margin-bottom:2px; white-space:nowrap; }
        .fact-v { color:#f2f7ff; font-size:.84rem; font-weight:700; line-height:1.15; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .achievements { margin-top:12px; padding-top:10px; border-top:1px solid rgba(130,153,193,.2); display:flex; flex-direction:column; gap:6px; }
        .ach-title { color:#9fb3dd; font-size:.68rem; letter-spacing:.06em; text-transform:uppercase; font-weight:700; }
        .ach-line { font-size:.74rem; color:#c4d2ef; line-height:1.2; }
        .big-score { font-size:2.2rem; font-weight:900; line-height:1; }
        .status { font-size:.85rem; color:#8ce6b4; font-weight:700; }
        .muted { color:#97a7cc; font-size:.78rem; }
        .score-card { display:flex; flex-direction:column; align-items:flex-start; height:100%; }
        .score-top { display:flex; flex-direction:column; gap:4px; }
        .score-meta { margin-top:4px; line-height:1.25; }
        .gauge-wrap { width:100%; margin-top:2px; margin-bottom:2px; }
        .gauge { width:100%; height:68px; }
        .headline-title { margin-bottom:10px; }
        .headline { display:grid; grid-template-columns:1fr 1fr; gap:10px; align-content:start; }
        .stat { border:1px solid rgba(130,153,193,.25); border-radius:10px; padding:9px 10px; background:rgba(13,19,31,.75); min-height:64px; display:flex; flex-direction:column; justify-content:space-between; }
        .stat-k { color:#8fa5d3; font-size:.72rem; }
        .stat-v { color:#f6f9ff; font-size:1.05rem; font-weight:800; }
        .section { background: linear-gradient(160deg, rgba(13,18,29,.96), rgba(9,12,20,.97)); border:1px solid rgba(126,151,194,.22); border-radius:14px; padding:14px; margin-bottom:12px; }
        .split2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        @media (max-width:1000px) { .card-grid,.split2{grid-template-columns:1fr;} .player-wrap{grid-template-columns:86px 1fr;} .headshot{width:86px;height:86px;} .v2-card{min-height:unset;} }
        </style>
        """,
        unsafe_allow_html=True,
    )


def build_recent_form_series(player_df: pd.DataFrame) -> pd.DataFrame:
    data = player_df.sort_values("date").copy()
    data["label"] = data["date"].dt.strftime("%b %d") + " · " + data["map"].astype(str)
    return data.tail(12)


def render_top_cards(snapshot: PlayerSnapshot, achievements: pd.DataFrame, player_name: str) -> None:
    photo_uri = image_to_data_uri(find_player_photo(player_name))
    ach_rows = achievements[achievements["player"] == player_name].head(3)
    ach_html = "".join(
        f"<div class='ach-line'>🏆 {html.escape(r['season_name'])}: {html.escape(r['achievement_name'])} ({html.escape(r['position'])})</div>"
        for _, r in ach_rows.iterrows()
    ) or "<div class='ach-line muted'>No achievements recorded in source data.</div>"

    if snapshot.grevscore >= 75:
        status = "Elite Impact"
    elif snapshot.grevscore >= 58:
        status = "Stable Core"
    else:
        status = "Needs Lift"

    st.markdown(
        f"""
        <div class=\"card-grid\">
          <section class=\"v2-card player-card\">
            <div class=\"player-wrap\">
              <img class=\"headshot\" src=\"{photo_uri}\" alt=\"player photo\" />
              <div class=\"player-core\">
                <p class=\"p-name\">{html.escape(snapshot.name)}</p>
                <div class=\"p-meta\">{html.escape(snapshot.team)} · {html.escape(snapshot.role)} · {html.escape(snapshot.country)}</div>
                <div class=\"mini-facts\">
                  <div class=\"fact\"><div class=\"fact-k\">Fame</div><div class=\"fact-v\">{snapshot.fame}</div></div>
                  <div class=\"fact\"><div class=\"fact-k\">Matches</div><div class=\"fact-v\">{snapshot.matches}</div></div>
                  <div class=\"fact\"><div class=\"fact-k\">Maps</div><div class=\"fact-v\">{snapshot.maps}</div></div>
                  <div class=\"fact\"><div class=\"fact-k\">Competitions</div><div class=\"fact-v\">{snapshot.competitions}</div></div>
                </div>
                <div class=\"achievements\">
                  <div class=\"ach-title\">Achievement Cabinet</div>
                  {ach_html}
                </div>
              </div>
            </div>
          </section>

          <section class=\"v2-card\">
            <div class=\"score-card\">
              <div class=\"score-top\">
                <div class=\"muted\">GREVScore Feature</div>
                <div class=\"big-score\">{snapshot.grevscore:.1f}</div>
                <div class=\"status\">{status}</div>
              </div>
              <div class=\"gauge-wrap\">{gauge_html(snapshot.grevscore)}</div>
              <div class=\"muted score-meta\">Top {max(1, 100 - snapshot.percentile):.0f}% percentile band · Form Δ {snapshot.form_delta:+.2f} KPD</div>
            </div>
          </section>

          <section class=\"v2-card\">
            <div class=\"muted headline-title\">Headline Stats</div>
            <div class=\"headline\">
              <div class=\"stat\"><div class=\"stat-k\">KPD</div><div class=\"stat-v\">{snapshot.kpd:.2f}</div></div>
              <div class=\"stat\"><div class=\"stat-k\">Avg K / D</div><div class=\"stat-v\">{snapshot.avg_kills:.1f} / {snapshot.avg_deaths:.1f}</div></div>
              <div class=\"stat\"><div class=\"stat-k\">Accuracy</div><div class=\"stat-v\">{snapshot.accuracy_pct:.1f}%</div></div>
              <div class=\"stat\"><div class=\"stat-k\">Headshot</div><div class=\"stat-v\">{snapshot.hs_pct:.1f}%</div></div>
            </div>
          </section>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_bottom_sections(player_df: pd.DataFrame) -> None:
    metrics = {
        "Total Kills": int(player_df["kills"].sum()),
        "Total Deaths": int(player_df["deaths"].sum()),
        "Total Damage": int(player_df["damage"].sum()),
        "MVPs": int(player_df["mvps"].sum()),
        "Rounds": int(player_df["rounds_played"].sum()),
        "Best Map KPD": f"{player_df.groupby('map')['kpd'].mean().sort_values(ascending=False).head(1).iloc[0]:.2f}",
    }

    col_a, col_b = st.columns([1, 1])
    with col_a:
        st.markdown("<section class='section'><h4>Core Performance</h4></section>", unsafe_allow_html=True)
        st.dataframe(
            pd.DataFrame([metrics]).T.rename(columns={0: "Value"}),
            use_container_width=True,
            height=250,
        )

    with col_b:
        st.markdown("<section class='section'><h4>Form (Last 5)</h4></section>", unsafe_allow_html=True)
        recent = player_df.sort_values("date").tail(5)
        form_table = recent[["date", "map", "kills", "deaths", "kpd", "accuracy_pct", "hs_pct"]].copy()
        form_table["date"] = form_table["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(form_table, use_container_width=True, height=250)

    st.markdown("<section class='section'><h4>Recent Form Graph</h4></section>", unsafe_allow_html=True)
    series = build_recent_form_series(player_df)
    st.line_chart(series.set_index("label")[["kpd", "kills", "deaths"]], use_container_width=True)



def main() -> None:
    st.set_page_config(page_title="Profile Viewer V2", layout="wide")
    inject_styles()

    matches = load_player_matches()
    player_meta = load_player_meta()
    achievements = load_achievements()

    st.markdown("<div class='v2-title'>Player Profile Viewer V2</div>", unsafe_allow_html=True)
    st.markdown(
        "<div class='v2-sub'>Fresh rebuild using direct CSV sources only (PlayerDataMatser.csv, players/play metadata, Achievements.csv).</div>",
        unsafe_allow_html=True,
    )

    left, mid, right = st.columns([1.4, 1, 1])
    with left:
        player_options = sorted(matches["player"].dropna().unique().tolist())
        chosen_player = st.selectbox("Player", player_options)
    with mid:
        maps = ["All"] + sorted(matches["map"].dropna().unique().tolist())
        chosen_map = st.selectbox("Map Filter", maps)
    with right:
        competitions = ["All"] + sorted(matches["competition"].dropna().unique().tolist())
        chosen_comp = st.selectbox("Competition Filter", competitions)

    filtered = matches[matches["player"] == chosen_player].copy()
    if chosen_map != "All":
        filtered = filtered[filtered["map"] == chosen_map]
    if chosen_comp != "All":
        filtered = filtered[filtered["competition"] == chosen_comp]

    if filtered.empty:
        st.warning("No rows match your filter combination.")
        return

    snapshot = build_player_snapshot(chosen_player, filtered, matches, player_meta)
    render_top_cards(snapshot, achievements, chosen_player)
    render_bottom_sections(filtered)


if __name__ == "__main__":
    main()
