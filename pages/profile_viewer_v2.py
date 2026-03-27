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
    DATA_DIR / "profile.csv",
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
        normalized_cols = {str(c).strip().lower(): c for c in raw.columns}

        def pick_col(candidates: list[str]) -> str | None:
            for candidate in candidates:
                if candidate in normalized_cols:
                    return normalized_cols[candidate]
            return None

        name_col = pick_col(["name", "player", "player_name"])
        nation_col = pick_col(["nation", "country"])
        role_col = pick_col(["role", "position"])
        fame_col = pick_col(["fame"])
        id_col = pick_col(["playerid", "player_id", "id"])

        if all([name_col, nation_col, role_col, fame_col]):
            meta = pd.DataFrame(
                {
                    "player_id": raw[id_col].astype(str) if id_col else "",
                    "name": raw[name_col].astype(str).str.strip().str.strip('"'),
                    "country": raw[nation_col].astype(str).str.strip().str.strip('"'),
                    "role": raw[role_col].astype(str).str.strip().str.strip('"'),
                    "fame": pd.to_numeric(raw[fame_col], errors="coerce").fillna(0).astype(int),
                }
            )
            meta["fame"] = meta["fame"].clip(0, 5)
            if not meta.empty:
                return meta

        col = raw.columns[0]
        lines = raw[col].astype(str)
        records: list[dict[str, str | int]] = []
        for line in lines:
            tokens = re.findall(r'"([^"]*)"|(\S+)', line)
            flat = [a or b for a, b in tokens]
            if len(flat) < 5:
                continue
            player_id, name, country, role, fame = flat[0], flat[1], flat[2], flat[3], flat[4]
            records.append(
                {
                    "player_id": player_id,
                    "name": str(name).strip('"'),
                    "country": str(country).strip('"'),
                    "role": str(role).strip('"'),
                    "fame": int(pd.to_numeric(fame, errors="coerce") or 0),
                }
            )
        if records:
            meta = pd.DataFrame(records)
            meta["fame"] = pd.to_numeric(meta["fame"], errors="coerce").fillna(0).astype(int).clip(0, 5)
            return meta
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


def role_icon(role: str) -> str:
    role_lower = (role or "").strip().lower()
    if "snip" in role_lower:
        return "🎯"
    if "entry" in role_lower:
        return "🚀"
    if "support" in role_lower:
        return "🛡️"
    if "igl" in role_lower or "lead" in role_lower:
        return "🧠"
    if "lurker" in role_lower:
        return "🥷"
    return "🎮"


def country_flag(country: str) -> str:
    normalized = (country or "").strip().lower()
    known = {
        "greece": "🇬🇷",
        "poland": "🇵🇱",
        "france": "🇫🇷",
        "germany": "🇩🇪",
        "spain": "🇪🇸",
        "italy": "🇮🇹",
        "sweden": "🇸🇪",
        "denmark": "🇩🇰",
        "norway": "🇳🇴",
        "finland": "🇫🇮",
        "united kingdom": "🇬🇧",
        "uk": "🇬🇧",
        "usa": "🇺🇸",
        "united states": "🇺🇸",
        "canada": "🇨🇦",
        "brazil": "🇧🇷",
        "argentina": "🇦🇷",
        "turkey": "🇹🇷",
        "serbia": "🇷🇸",
        "romania": "🇷🇴",
        "portugal": "🇵🇹",
        "netherlands": "🇳🇱",
        "belgium": "🇧🇪",
    }
    return known.get(normalized, "🌍")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
          --surface-1:#0f1728;
          --surface-2:#121d33;
          --surface-3:#0d1526;
          --border:rgba(151,176,219,.28);
          --text-soft:#9fb3dd;
          --teal:#2de1be;
          --amber:#ffb85c;
          --rose:#ff6f9f;
        }
        .stApp { background: radial-gradient(circle at 8% -8%, #22395d 0%, #0b1220 35%, #070b14 100%); color: #e7edf7; }
        .block-container { max-width: 1480px; margin: 0 auto; padding-top: 1.35rem; padding-left: 2rem; padding-right: 2rem; }
        .v2-title { font-size: 1.65rem; font-weight: 800; margin-bottom: .2rem; }
        .v2-sub { color: #9fb0d3; margin-bottom: 1rem; font-size: .92rem; }
        .card-grid { display:grid; grid-template-columns: 1.6fr 1fr 1fr; gap: 14px; margin: 10px 0 18px 0; align-items: stretch; }
        .v2-card { background: linear-gradient(155deg, rgba(18,29,50,.96), rgba(10,16,29,.96)); border:1px solid var(--border); border-radius:18px; padding:16px; box-shadow: 0 14px 34px rgba(0,0,0,.42); min-height: 236px; }
        .player-card { background:
            radial-gradient(70% 80% at 0% 0%, rgba(45,225,190,.18), transparent 68%),
            radial-gradient(65% 65% at 100% 100%, rgba(255,184,92,.12), transparent 68%),
            linear-gradient(165deg, rgba(18,31,52,.98), rgba(10,17,30,.98));
        }
        .grev-card { background:
            radial-gradient(90% 90% at 90% 10%, rgba(45,225,190,.18), transparent 66%),
            radial-gradient(90% 90% at 0% 100%, rgba(255,184,92,.12), transparent 70%),
            linear-gradient(165deg, rgba(16,31,53,.98), rgba(10,17,29,.98));
        }
        .stats-card { background:
            radial-gradient(65% 65% at 10% 0%, rgba(255,184,92,.11), transparent 60%),
            linear-gradient(165deg, rgba(24,33,53,.98), rgba(10,17,29,.98));
        }
        .player-card { display:flex; flex-direction:column; gap:12px; }
        .player-top { display:grid; grid-template-columns: minmax(0, 1.35fr) minmax(170px, 1fr); gap:12px; align-items:stretch; }
        .player-main { display:grid; grid-template-columns: 112px minmax(0,1fr); gap:12px; align-items:start; }
        .headshot { width:112px; height:112px; object-fit:cover; border-radius:14px; border:1px solid rgba(153,188,255,.35); box-shadow:0 0 0 4px rgba(45,225,190,.09); }
        .player-core { display:flex; flex-direction:column; gap:8px; min-width:0; }
        .p-name { font-size:1.34rem; font-weight:850; color:#f6f9ff; margin:0; letter-spacing:.01em; }
        .team-label { color:#c3d3f2; font-size:.82rem; margin-top:-2px; margin-bottom:2px; }
        .identity-stack { display:flex; flex-direction:column; gap:6px; }
        .icon-line { display:flex; align-items:center; gap:7px; color:#d9e6ff; font-size:.79rem; }
        .icon-line .subtle { color:#95add6; min-width:67px; font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; }
        .fame-row { display:flex; gap:5px; align-items:center; }
        .fame-dot { width:8px; height:8px; border-radius:999px; background:rgba(157,180,219,.28); box-shadow:0 0 0 1px rgba(110,140,180,.45); }
        .fame-dot.on { background:linear-gradient(180deg, #ffe29b, #ffb85c); box-shadow:0 0 10px rgba(255,184,92,.45); }
        .quick-facts { display:grid; grid-template-columns:repeat(2,minmax(80px,1fr)); gap:8px; }
        .fact { border:1px solid rgba(133,170,219,.32); border-radius:12px; padding:8px 7px; background:rgba(11,20,35,.75); min-width:0; text-align:center; }
        .fact-k { color:#96b0e0; font-size:.64rem; line-height:1.08; margin-bottom:2px; text-transform:uppercase; letter-spacing:.06em; }
        .fact-v { color:#f2f7ff; font-size:.9rem; font-weight:780; line-height:1.15; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; }
        .achievements { border-top:1px solid rgba(130,153,193,.23); padding-top:10px; }
        .ach-head { display:flex; align-items:center; justify-content:space-between; gap:8px; margin-bottom:8px; }
        .ach-title { color:#f3c679; font-size:.68rem; letter-spacing:.08em; text-transform:uppercase; font-weight:800; }
        .ach-sub { color:#9db4de; font-size:.68rem; }
        .ach-strip { display:flex; gap:9px; overflow-x:auto; padding-bottom:3px; scrollbar-width:thin; scrollbar-color: rgba(143,163,198,.55) rgba(7,13,24,.3); }
        .ach-item { flex:0 0 200px; border:1px solid rgba(129,154,199,.34); border-radius:12px; background:linear-gradient(165deg, rgba(15,28,45,.92), rgba(9,17,30,.92)); padding:9px; }
        .ach-season { color:#8ec8ff; font-size:.62rem; text-transform:uppercase; letter-spacing:.07em; margin-bottom:4px; }
        .ach-name { color:#f3f7ff; font-size:.74rem; font-weight:760; line-height:1.2; min-height:34px; }
        .ach-foot { display:flex; justify-content:space-between; align-items:center; margin-top:6px; font-size:.66rem; }
        .ach-tier { color:#ffd39a; }
        .ach-pos { color:#9df5e1; font-weight:700; }
        .ach-empty { color:#a3b6de; font-size:.75rem; padding:8px 0 2px; }
        .big-score { font-size:2.4rem; font-weight:900; line-height:1; letter-spacing:.01em; }
        .score-chip { font-size:.73rem; font-weight:700; letter-spacing:.03em; padding:4px 8px; border-radius:999px; width:fit-content; border:1px solid transparent; text-transform:uppercase; }
        .status { font-size:.9rem; font-weight:800; }
        .grev-excellent .big-score, .grev-excellent .status { color:var(--teal); text-shadow:0 0 14px rgba(45,225,190,.18); }
        .grev-excellent .score-chip { color:#93f8e4; border-color:rgba(45,225,190,.45); background:rgba(22,55,51,.42); }
        .grev-average .big-score, .grev-average .status { color:var(--amber); text-shadow:0 0 12px rgba(255,184,92,.22); }
        .grev-average .score-chip { color:#ffd69b; border-color:rgba(255,184,92,.45); background:rgba(70,44,22,.4); }
        .grev-poor .big-score, .grev-poor .status { color:var(--rose); text-shadow:0 0 12px rgba(255,111,159,.22); }
        .grev-poor .score-chip { color:#ffc3d8; border-color:rgba(255,111,159,.5); background:rgba(76,25,46,.42); }
        .muted { color:#9eb2dc; font-size:.78rem; }
        .score-card { display:flex; flex-direction:column; align-items:stretch; height:100%; gap:8px; }
        .score-top { display:flex; flex-direction:column; gap:5px; }
        .score-meta { margin-top:4px; line-height:1.25; }
        .quality-track { width:100%; height:11px; border-radius:999px; background:linear-gradient(90deg, rgba(255,111,159,.45) 0%, rgba(255,184,92,.5) 42%, rgba(45,225,190,.56) 100%); border:1px solid rgba(158,181,219,.31); overflow:hidden; margin:4px 0 6px; position:relative; }
        .quality-fill { height:100%; background:linear-gradient(90deg, rgba(255,255,255,.08), rgba(255,255,255,.6)); }
        .quality-marker { position:absolute; top:-2px; width:2px; height:14px; background:#f4fbff; box-shadow:0 0 10px rgba(255,255,255,.45); }
        .gauge-wrap { width:100%; margin-top:0; margin-bottom:0; }
        .gauge { width:100%; height:68px; }
        .grev-meta-grid { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px; margin-top:3px; }
        .meta-pill { border:1px solid rgba(138,166,206,.32); border-radius:10px; background:rgba(9,19,33,.68); padding:8px 6px; text-align:center; }
        .meta-k { color:#9db5de; font-size:.62rem; text-transform:uppercase; letter-spacing:.06em; margin-bottom:2px; }
        .meta-v { color:#f5f9ff; font-size:.83rem; font-weight:760; }
        .headline-title { margin-bottom:10px; }
        .headline { display:grid; grid-template-columns:1fr 1fr; gap:10px; align-content:start; }
        .stat { border:1px solid rgba(133,170,219,.26); border-radius:12px; padding:9px 10px; background:rgba(11,20,35,.76); min-height:64px; display:flex; flex-direction:column; justify-content:center; text-align:center; }
        .stat-k { color:#9eb4df; font-size:.7rem; text-transform:uppercase; letter-spacing:.06em; margin-bottom:3px; }
        .stat-v { color:#f6f9ff; font-size:1.03rem; font-weight:800; }
        .tone-pos .stat-k { color:#8ff6dc; } .tone-pos .stat-v { color:#b4ffe9; }
        .tone-mid .stat-k { color:#ffd08c; } .tone-mid .stat-v { color:#ffe2b5; }
        .tone-neg .stat-k { color:#ff9dc2; } .tone-neg .stat-v { color:#ffc0d7; }
        .section { background: linear-gradient(160deg, rgba(14,22,37,.96), rgba(10,14,24,.97)); border:1px solid rgba(126,151,194,.24); border-radius:14px; padding:14px; margin-bottom:12px; }
        .section h4 { margin:.1rem 0 .25rem; color:#dff0ff; }
        .split2 { display:grid; grid-template-columns:1fr 1fr; gap:12px; }
        .table-caption { color:#8fcce0; font-size:.76rem; margin:-2px 0 10px 0; }
        .section-accent { color:#88d8ff; }
        .section-accent.warm { color:#ffcc85; }
        @media (max-width:1100px) { .card-grid,.split2{grid-template-columns:1fr;} .player-top{grid-template-columns:1fr;} .player-main{grid-template-columns:94px 1fr;} .headshot{width:94px;height:94px;} .v2-card{min-height:unset;} }
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
    ach_rows = achievements[achievements["player"] == player_name].head(8)
    ach_html = "".join(
        (
            "<article class='ach-item'>"
            f"<div class='ach-season'>{html.escape(r['season_name'])}</div>"
            f"<div class='ach-name'>{html.escape(r['achievement_name'])}</div>"
            "<div class='ach-foot'>"
            f"<span class='ach-tier'>{html.escape(r['achievement_tier'])}</span>"
            f"<span class='ach-pos'>#{html.escape(str(r['position']))}</span>"
            "</div></article>"
        )
        for _, r in ach_rows.iterrows()
    ) or "<div class='ach-empty'>No achievements recorded in source data.</div>"

    if snapshot.grevscore >= 75:
        status = "Elite Impact"
        grev_class = "grev-excellent"
    elif snapshot.grevscore >= 58:
        status = "Stable Core"
        grev_class = "grev-average"
    else:
        status = "Needs Lift"
        grev_class = "grev-poor"

    fame_level = max(0, min(5, int(snapshot.fame)))
    fame_html = "".join(f"<span class='fame-dot {'on' if i < fame_level else ''}'></span>" for i in range(5))
    role_with_icon = f"{role_icon(snapshot.role)} {html.escape(snapshot.role)}"
    country_with_icon = f"{country_flag(snapshot.country)} {html.escape(snapshot.country)}"
    top_band = max(1, round(100 - snapshot.percentile))

    kpd_tone = "tone-pos" if snapshot.kpd >= 1.02 else "tone-mid" if snapshot.kpd >= 0.9 else "tone-neg"
    acc_tone = "tone-pos" if snapshot.accuracy_pct >= 42 else "tone-mid" if snapshot.accuracy_pct >= 35 else "tone-neg"
    hs_tone = "tone-pos" if snapshot.hs_pct >= 45 else "tone-mid" if snapshot.hs_pct >= 36 else "tone-neg"

    st.markdown(
        f"""
        <div class="card-grid">
          <section class="v2-card player-card">
            <div class="player-top">
              <div class="player-main">
                <img class="headshot" src="{photo_uri}" alt="player photo" />
                <div class="player-core">
                  <p class="p-name">{html.escape(snapshot.name)}</p>
                  <div class="team-label">{html.escape(snapshot.team)}</div>
                  <div class="identity-stack">
                    <div class="icon-line"><span class="subtle">Role</span><span>{role_with_icon}</span></div>
                    <div class="icon-line"><span class="subtle">Nation</span><span>{country_with_icon}</span></div>
                    <div class="icon-line"><span class="subtle">Fame</span><span class="fame-row" title="Fame {fame_level}/5">{fame_html}</span><span>{fame_level}/5</span></div>
                  </div>
                </div>
              </div>
              <div class="quick-facts">
                <div class="fact"><div class="fact-k">Matches</div><div class="fact-v">{snapshot.matches}</div></div>
                <div class="fact"><div class="fact-k">Maps</div><div class="fact-v">{snapshot.maps}</div></div>
                <div class="fact"><div class="fact-k">Events</div><div class="fact-v">{snapshot.competitions}</div></div>
                <div class="fact"><div class="fact-k">MVP Rate</div><div class="fact-v">{snapshot.mvp_rate:.0f}%</div></div>
              </div>
            </div>
            <div class="achievements">
              <div class="ach-head">
                <div class="ach-title">Achievement Strip</div>
                <div class="ach-sub">Swipe →</div>
              </div>
              <div class="ach-strip">
                {ach_html}
              </div>
            </div>
          </section>

          <section class="v2-card grev-card">
            <div class="score-card {grev_class}">
              <div class="score-top">
                <div class="muted">GREVScore Feature</div>
                <div class="score-chip">Quality Index</div>
                <div class="big-score">{snapshot.grevscore:.1f}</div>
                <div class="status">{status}</div>
              </div>
              <div class="quality-track">
                <div class="quality-fill" style="width:{snapshot.grevscore:.1f}%"></div>
                <div class="quality-marker" style="left: calc({snapshot.grevscore:.1f}% - 1px);"></div>
              </div>
              <div class="gauge-wrap">{gauge_html(snapshot.grevscore)}</div>
              <div class="grev-meta-grid">
                <div class="meta-pill"><div class="meta-k">Percentile</div><div class="meta-v">Top {top_band}%</div></div>
                <div class="meta-pill"><div class="meta-k">Form Delta</div><div class="meta-v">{snapshot.form_delta:+.2f} KPD</div></div>
                <div class="meta-pill"><div class="meta-k">Avg Damage</div><div class="meta-v">{snapshot.avg_damage:.0f}</div></div>
              </div>
              <div class="muted score-meta">Polished rating scale calibrated across KPD, accuracy, headshot share, and MVP consistency.</div>
            </div>
          </section>

          <section class="v2-card stats-card">
            <div class="muted headline-title">Headline Stats</div>
            <div class="headline">
              <div class="stat {kpd_tone}"><div class="stat-k">KPD</div><div class="stat-v">{snapshot.kpd:.2f}</div></div>
              <div class="stat tone-mid"><div class="stat-k">Avg K / D</div><div class="stat-v">{snapshot.avg_kills:.1f} / {snapshot.avg_deaths:.1f}</div></div>
              <div class="stat {acc_tone}"><div class="stat-k">Accuracy</div><div class="stat-v">{snapshot.accuracy_pct:.1f}%</div></div>
              <div class="stat {hs_tone}"><div class="stat-k">Headshot</div><div class="stat-v">{snapshot.hs_pct:.1f}%</div></div>
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
        st.markdown(
            "<section class='section'><h4 class='section-accent'>Core Performance</h4><div class='table-caption'>Expanded totals with stronger contrast for quick scanning.</div></section>",
            unsafe_allow_html=True,
        )
        st.dataframe(
            pd.DataFrame([metrics]).T.rename(columns={0: "Value"}),
            use_container_width=True,
            height=250,
        )

    with col_b:
        st.markdown(
            "<section class='section'><h4 class='section-accent warm'>Form (Last 5)</h4><div class='table-caption'>Recent map-by-map trend with efficiency indicators.</div></section>",
            unsafe_allow_html=True,
        )
        recent = player_df.sort_values("date").tail(5)
        form_table = recent[["date", "map", "kills", "deaths", "kpd", "accuracy_pct", "hs_pct"]].copy()
        form_table["date"] = form_table["date"].dt.strftime("%Y-%m-%d")
        st.dataframe(form_table, use_container_width=True, height=250)

    st.markdown(
        "<section class='section'><h4 class='section-accent'>Recent Form Graph</h4><div class='table-caption'>KPD, kills, and deaths over the most recent maps.</div></section>",
        unsafe_allow_html=True,
    )
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
