from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import streamlit as st

st.set_page_config(page_title="Grev Pets Playground", page_icon="🐾", layout="wide")

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "grev_pets_players.json"

PET_TYPES = {
    "Ember": {
        "color": "#ff7b5c",
        "accent": "#ffb36b",
        "weak": ["Tidal", "Stone"],
        "strong": ["Moss", "Frost"],
        "vibe": "fiery, energetic, and spiky",
        "traits": ["ember whiskers", "lava spots", "blazing tail"],
        "silhouette": "pointed horns",
    },
    "Moss": {
        "color": "#5ecf84",
        "accent": "#a8e06a",
        "weak": ["Ember", "Toxic"],
        "strong": ["Stone", "Tidal"],
        "vibe": "leafy, rounded, and earthy",
        "traits": ["moss mane", "seed crown", "vine tail"],
        "silhouette": "round ears",
    },
    "Zap": {
        "color": "#f8d94a",
        "accent": "#fff4aa",
        "weak": ["Stone", "Iron"],
        "strong": ["Tidal", "Lunar"],
        "vibe": "sharp, twitchy, and electric",
        "traits": ["spark fins", "zigzag cheeks", "battery tuft"],
        "silhouette": "lightning spikes",
    },
    "Tidal": {
        "color": "#4db6ff",
        "accent": "#9ee2ff",
        "weak": ["Zap", "Toxic"],
        "strong": ["Ember", "Stone"],
        "vibe": "smooth, aquatic, and fluid",
        "traits": ["wave crest", "bubble dots", "fin tail"],
        "silhouette": "sleek fins",
    },
    "Toxic": {
        "color": "#9af25f",
        "accent": "#d8ff8c",
        "weak": ["Frost", "Spirit"],
        "strong": ["Moss", "Lunar"],
        "vibe": "gooey, dangerous, and weird",
        "traits": ["ooze drips", "hazard freckles", "acid horns"],
        "silhouette": "droplet crest",
    },
    "Stone": {
        "color": "#b4a38f",
        "accent": "#ddd0c4",
        "weak": ["Moss", "Tidal"],
        "strong": ["Zap", "Iron"],
        "vibe": "sturdy, tanky, and grounded",
        "traits": ["slate plates", "quartz chin", "pebble paws"],
        "silhouette": "blocky brow",
    },
    "Frost": {
        "color": "#8fdfff",
        "accent": "#d8f3ff",
        "weak": ["Ember", "Iron"],
        "strong": ["Toxic", "Feral"],
        "vibe": "soft-cold, pale, and crystalline",
        "traits": ["snow tuft", "ice halo", "frost frill"],
        "silhouette": "crystal ears",
    },
    "Spirit": {
        "color": "#b789ff",
        "accent": "#e1c9ff",
        "weak": ["Lunar", "Glitch"],
        "strong": ["Toxic", "Feral"],
        "vibe": "mystic, floaty, and eerie",
        "traits": ["mist tail", "rune freckles", "echo horns"],
        "silhouette": "wisp mane",
    },
    "Iron": {
        "color": "#93a6be",
        "accent": "#d1dae7",
        "weak": ["Ember", "Stone"],
        "strong": ["Zap", "Frost"],
        "vibe": "mechanical, disciplined, and armored",
        "traits": ["bolt cheeks", "gear collar", "metal plating"],
        "silhouette": "helmet ridge",
    },
    "Lunar": {
        "color": "#7f90ff",
        "accent": "#b8c3ff",
        "weak": ["Zap", "Toxic"],
        "strong": ["Spirit", "Glitch"],
        "vibe": "calm, celestial, and elusive",
        "traits": ["moon mark", "star dust", "crescent tail"],
        "silhouette": "crescent horns",
    },
    "Glitch": {
        "color": "#ff6be8",
        "accent": "#7ff8ff",
        "weak": ["Lunar", "Iron"],
        "strong": ["Spirit", "Feral"],
        "vibe": "unstable, digital, and odd",
        "traits": ["pixel scars", "signal static", "broken halo"],
        "silhouette": "offset outline",
    },
    "Feral": {
        "color": "#ff9d66",
        "accent": "#ffd2a1",
        "weak": ["Frost", "Spirit"],
        "strong": ["Lunar", "Glitch"],
        "vibe": "wild, quick, and clawed",
        "traits": ["fang streak", "predator mask", "hunter tail"],
        "silhouette": "long ears",
    },
}

STARTER_CHOICES = [
    {
        "name": "Cindlet",
        "primary_type": "Ember",
        "secondary_type": "Feral",
        "role": "Speedy",
        "description": "Tiny furnace fox that sprints before opponents can blink.",
        "stats": {"Power": 58, "Guard": 37, "Agility": 86, "Trick": 62},
    },
    {
        "name": "Budgloop",
        "primary_type": "Moss",
        "secondary_type": "Tidal",
        "role": "Balanced",
        "description": "Marsh buddy that heals allies while soaking pressure.",
        "stats": {"Power": 49, "Guard": 71, "Agility": 52, "Trick": 61},
    },
    {
        "name": "Voltimp",
        "primary_type": "Zap",
        "secondary_type": "Glitch",
        "role": "Tricky",
        "description": "Hyper gremlin who chains sparks and confuses rivals.",
        "stats": {"Power": 63, "Guard": 42, "Agility": 79, "Trick": 84},
    },
    {
        "name": "Cragoon",
        "primary_type": "Stone",
        "secondary_type": "Iron",
        "role": "Tanky",
        "description": "Loyal wall beast that protects the party frontline.",
        "stats": {"Power": 56, "Guard": 88, "Agility": 31, "Trick": 43},
    },
]

AVATAR_DEFAULT = {
    "skin_tone": "#f2c9a8",
    "hair_style": "Short",
    "hair_color": "#533725",
    "eye_style": "Round",
    "top": "Scout Jacket",
    "top_color": "#70a5ff",
    "bottom": "Trail Pants",
    "bottom_color": "#4a5f8a",
    "accessory": "Neck Charm",
    "hat": "None",
    "body_type": "Standard",
}


@dataclass
class PlayerProfile:
    username: str
    title: str
    zone: str
    level: int
    xp: int
    favourite_type: str
    battle_wins: int
    battle_losses: int
    race_wins: int
    race_losses: int
    avatar: dict[str, Any]
    pets: list[dict[str, Any]]
    active_pet_id: str | None
    starter_selected: bool
    starter_pet_name: str | None
    position_x: int
    position_y: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "username": self.username,
            "title": self.title,
            "zone": self.zone,
            "level": self.level,
            "xp": self.xp,
            "favourite_type": self.favourite_type,
            "battle_wins": self.battle_wins,
            "battle_losses": self.battle_losses,
            "race_wins": self.race_wins,
            "race_losses": self.race_losses,
            "avatar": self.avatar,
            "pets": self.pets,
            "active_pet_id": self.active_pet_id,
            "starter_selected": self.starter_selected,
            "starter_pet_name": self.starter_pet_name,
            "position_x": self.position_x,
            "position_y": self.position_y,
        }


def _load_db() -> dict[str, Any]:
    if not DATA_PATH.exists():
        DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
        DATA_PATH.write_text(json.dumps({"players": {}}, indent=2), encoding="utf-8")
    try:
        return json.loads(DATA_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"players": {}}


def _save_db(db: dict[str, Any]) -> None:
    DATA_PATH.write_text(json.dumps(db, indent=2), encoding="utf-8")


def _new_profile(username: str) -> PlayerProfile:
    return PlayerProfile(
        username=username,
        title="Rookie Tamer",
        zone="Home Camp",
        level=1,
        xp=0,
        favourite_type="Ember",
        battle_wins=0,
        battle_losses=0,
        race_wins=0,
        race_losses=0,
        avatar=AVATAR_DEFAULT.copy(),
        pets=[],
        active_pet_id=None,
        starter_selected=False,
        starter_pet_name=None,
        position_x=2,
        position_y=2,
    )


def _get_profile(db: dict[str, Any], username: str) -> PlayerProfile:
    players = db.setdefault("players", {})
    raw = players.get(username)
    if raw is None:
        profile = _new_profile(username)
        players[username] = profile.to_dict()
        _save_db(db)
        return profile

    return PlayerProfile(
        username=raw.get("username", username),
        title=raw.get("title", "Rookie Tamer"),
        zone=raw.get("zone", "Home Camp"),
        level=int(raw.get("level", 1)),
        xp=int(raw.get("xp", 0)),
        favourite_type=raw.get("favourite_type", "Ember"),
        battle_wins=int(raw.get("battle_wins", 0)),
        battle_losses=int(raw.get("battle_losses", 0)),
        race_wins=int(raw.get("race_wins", 0)),
        race_losses=int(raw.get("race_losses", 0)),
        avatar={**AVATAR_DEFAULT, **raw.get("avatar", {})},
        pets=list(raw.get("pets", [])),
        active_pet_id=raw.get("active_pet_id"),
        starter_selected=bool(raw.get("starter_selected", False)),
        starter_pet_name=raw.get("starter_pet_name"),
        position_x=int(raw.get("position_x", 2)),
        position_y=int(raw.get("position_y", 2)),
    )


def _save_profile(db: dict[str, Any], profile: PlayerProfile) -> None:
    db.setdefault("players", {})[profile.username] = profile.to_dict()
    _save_db(db)


def _type_badge(type_name: str) -> str:
    color = PET_TYPES[type_name]["color"]
    return f"<span class='type-badge' style='--badge:{color}'>{type_name}</span>"


def _avatar_svg(avatar: dict[str, Any], *, size: int = 160, small: bool = False) -> str:
    body_scale = {"Compact": 0.86, "Standard": 1.0, "Tall": 1.12}.get(avatar["body_type"], 1.0)
    eye_shape = {
        "Round": "<circle cx='78' cy='72' r='4' fill='#12233d'/><circle cx='112' cy='72' r='4' fill='#12233d'/>",
        "Sharp": "<ellipse cx='78' cy='72' rx='5.5' ry='2.8' fill='#12233d'/><ellipse cx='112' cy='72' rx='5.5' ry='2.8' fill='#12233d'/>",
        "Sleepy": "<path d='M73 72 Q78 69 83 72' stroke='#12233d' stroke-width='3' fill='none'/><path d='M107 72 Q112 69 117 72' stroke='#12233d' stroke-width='3' fill='none'/>",
    }.get(avatar["eye_style"])
    hair_path = {
        "Short": "M56 55 C70 25 118 25 133 55 L133 67 L56 67 Z",
        "Wavy": "M54 57 C66 25 120 23 134 57 C128 62 121 58 115 64 C102 59 88 60 74 66 C66 60 58 61 54 57",
        "Puff": "M52 58 C61 22 124 21 136 58 C124 68 111 71 92 70 C72 70 61 66 52 58",
        "Mohawk": "M88 20 L102 20 L108 62 L82 62 Z",
    }.get(avatar["hair_style"])
    hat = ""
    if avatar["hat"] == "Beanie":
        hat = "<ellipse cx='95' cy='43' rx='44' ry='15' fill='#263248'/><rect x='52' y='43' width='86' height='14' rx='7' fill='#1c2638'/>"
    elif avatar["hat"] == "Explorer Cap":
        hat = "<path d='M52 49 Q95 25 138 49 L138 61 L52 61 Z' fill='#5a4d89'/><rect x='52' y='57' width='86' height='9' rx='4' fill='#3e3561'/>"
    accessory = ""
    if avatar["accessory"] == "Neck Charm":
        accessory = "<circle cx='95' cy='111' r='6' fill='#ffe08b'/><circle cx='95' cy='111' r='2' fill='#987313'/>"
    elif avatar["accessory"] == "Holo Goggles":
        accessory = "<rect x='66' y='63' width='24' height='12' rx='5' fill='rgba(122,250,255,.4)' stroke='#5ac8d8'/><rect x='100' y='63' width='24' height='12' rx='5' fill='rgba(122,250,255,.4)' stroke='#5ac8d8'/><rect x='90' y='67' width='10' height='4' fill='#5ac8d8'/>"
    elif avatar["accessory"] == "Bandana":
        accessory = "<rect x='60' y='84' width='70' height='11' rx='5' fill='#d7628c'/>"

    zoom_class = "mini-avatar" if small else "full-avatar"
    return f"""
    <div class='avatar-shell {zoom_class}' style='width:{size}px;height:{size}px'>
      <svg viewBox='0 0 190 190' role='img' aria-label='Explorer avatar'>
        <defs>
          <linearGradient id='bgGlow' x1='0%' y1='0%' x2='100%' y2='100%'>
            <stop offset='0%' stop-color='#1f2d53'/>
            <stop offset='100%' stop-color='#111a31'/>
          </linearGradient>
        </defs>
        <rect x='8' y='8' width='174' height='174' rx='24' fill='url(#bgGlow)'/>
        <g transform='translate(0,{20 - ((body_scale - 1) * 24):.1f}) scale(1,{body_scale:.2f})'>
          <rect x='66' y='112' width='58' height='48' rx='12' fill='{avatar['top_color']}'/>
          <rect x='69' y='155' width='22' height='28' rx='8' fill='{avatar['bottom_color']}'/>
          <rect x='100' y='155' width='22' height='28' rx='8' fill='{avatar['bottom_color']}'/>
          <circle cx='95' cy='76' r='34' fill='{avatar['skin_tone']}'/>
          <path d='{hair_path}' fill='{avatar['hair_color']}'/>
          {hat}
          {eye_shape}
          <path d='M82 90 Q95 99 108 90' stroke='#914b37' stroke-width='3' fill='none' stroke-linecap='round'/>
          {accessory}
        </g>
      </svg>
    </div>
    """


def _pet_render_html(pet: dict[str, Any], *, compact: bool = False) -> str:
    p_type = pet["primary_type"]
    s_type = pet.get("secondary_type")
    type_data = PET_TYPES[p_type]
    accent = PET_TYPES[s_type]["accent"] if s_type else type_data["accent"]
    traits = ", ".join(pet.get("features", type_data["traits"][:2]))
    return f"""
    <div class='pet-card {'pet-compact' if compact else ''}' style='--pet-main:{type_data['color']};--pet-accent:{accent}'>
        <div class='pet-art'>
            <div class='pet-body'></div>
            <div class='pet-ear pet-ear-left'></div>
            <div class='pet-ear pet-ear-right'></div>
            <div class='pet-eye pet-eye-left'></div>
            <div class='pet-eye pet-eye-right'></div>
            <div class='pet-mouth'></div>
            <div class='pet-tail'></div>
        </div>
        <div class='pet-meta'>
            <div class='pet-name'>{pet['name']}</div>
            <div class='pet-types'>{_type_badge(p_type)} {(_type_badge(s_type) if s_type else '')}</div>
            <div class='pet-vibe'>{type_data['vibe']}; silhouette: {type_data['silhouette']}.</div>
            <div class='pet-traits'>{traits}</div>
        </div>
    </div>
    """


def _gen_pet(name: str, primary_type: str, secondary_type: str | None, role: str, from_starter: bool = False) -> dict[str, Any]:
    type_data = PET_TYPES[primary_type]
    base_stats = {
        "Power": random.randint(35, 82),
        "Guard": random.randint(35, 82),
        "Agility": random.randint(35, 82),
        "Trick": random.randint(35, 82),
    }
    if role == "Tanky":
        base_stats["Guard"] = min(95, base_stats["Guard"] + 14)
    if role == "Speedy":
        base_stats["Agility"] = min(95, base_stats["Agility"] + 14)
    if role == "Tricky":
        base_stats["Trick"] = min(95, base_stats["Trick"] + 14)

    return {
        "id": f"pet_{random.randint(10000, 99999)}",
        "name": name,
        "primary_type": primary_type,
        "secondary_type": secondary_type,
        "role": role,
        "rarity": "Starter" if from_starter else random.choice(["Common", "Rare", "Epic"]),
        "features": random.sample(type_data["traits"], k=2),
        "stats": base_stats,
    }


def _inject_style() -> None:
    st.markdown(
        """
    <style>
    :root {
        --bg0:#090f1a;
        --bg1:#121b2f;
        --card:#121d34;
        --ink:#eaf2ff;
        --muted:#9caecd;
        --line:rgba(166,185,223,.2);
        --gold:#ffd468;
        --cyan:#65e7ff;
        --pink:#ff85ce;
    }
    .stApp {background: radial-gradient(circle at 10% 0%, #1f2b49 0%, #0b1220 34%, #080d18 100%); color:var(--ink);}
    .hub-card {
        border:1px solid var(--line);
        border-radius:18px;
        padding:18px;
        background:linear-gradient(165deg, rgba(20,30,53,.88), rgba(12,18,33,.92));
        box-shadow:0 10px 28px rgba(0,0,0,.28);
        height:100%;
    }
    .hero {
        border-radius:22px;
        border:1px solid rgba(148,173,229,.25);
        padding:26px;
        margin-bottom:14px;
        background: linear-gradient(135deg, rgba(41,68,128,.65) 0%, rgba(23,38,70,.8) 42%, rgba(20,27,52,.88) 100%);
        position:relative;
        overflow:hidden;
    }
    .hero:after {
        content:"";
        position:absolute;
        right:-110px;
        top:-110px;
        width:280px;
        height:280px;
        border-radius:50%;
        background: radial-gradient(circle, rgba(102,249,255,.26), rgba(102,249,255,0));
    }
    .hero h1 {font-size:2.05rem; margin:0 0 .35rem; letter-spacing:.02em;}
    .hero p {color:#ccdaf6; margin:.2rem 0;}
    .step-row {display:flex; flex-wrap:wrap; gap:8px; margin-top:12px;}
    .step-pill {background:rgba(255,255,255,.08); border:1px solid rgba(161,181,223,.3); padding:6px 10px; border-radius:999px; font-size:.82rem;}

    .type-badge {
        display:inline-block; padding:2px 8px; border-radius:999px; border:1px solid var(--badge);
        color:#eef6ff; background:color-mix(in srgb, var(--badge) 22%, transparent); font-size:.72rem; margin-right:4px;
    }
    .avatar-shell {border:1px solid rgba(172,189,231,.23); border-radius:18px; overflow:hidden; background:#0f1629; box-shadow: inset 0 0 0 1px rgba(255,255,255,.04);}
    .mini-avatar {border-radius:10px;}

    .pet-card {border:1px solid rgba(169,189,237,.2); border-radius:14px; padding:12px; background:rgba(12,19,35,.9);}   
    .pet-art {position:relative; height:120px; border-radius:12px; background:linear-gradient(160deg, color-mix(in srgb, var(--pet-main) 26%, #101b34), #0f172c); margin-bottom:10px; overflow:hidden;}
    .pet-body {position:absolute; width:86px; height:70px; background:var(--pet-main); left:50%; top:32px; transform:translateX(-50%); border-radius:44px 44px 36px 36px; box-shadow:0 0 24px color-mix(in srgb, var(--pet-main) 50%, transparent);}
    .pet-ear {position:absolute; width:23px; height:32px; background:var(--pet-accent); top:15px; border-radius:18px 18px 6px 6px;}
    .pet-ear-left {left:52px; transform:rotate(-16deg);} .pet-ear-right {right:52px; transform:rotate(16deg);}   
    .pet-eye {position:absolute; width:9px; height:11px; background:#11182a; border-radius:50%; top:58px;} 
    .pet-eye-left {left:81px;} .pet-eye-right {right:81px;}
    .pet-mouth {position:absolute; width:18px; height:8px; border-bottom:3px solid #1b2f53; border-radius:50%; top:82px; left:50%; transform:translateX(-50%);} 
    .pet-tail {position:absolute; width:28px; height:20px; right:52px; top:88px; border-radius:0 16px 16px 0; background:var(--pet-accent);} 
    .pet-name {font-weight:800; font-size:1.03rem;}
    .pet-vibe,.pet-traits {color:var(--muted); font-size:.75rem; margin-top:4px;}

    .starter-option {border:1px solid rgba(175,193,235,.22); border-radius:16px; padding:14px; background:rgba(16,25,45,.88); transition:.2s transform,.2s border-color;}
    .starter-option:hover {transform:translateY(-2px); border-color:rgba(255,212,104,.62);} 
    .metric-grid {display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:8px;}
    .metric {border:1px solid rgba(167,183,221,.2); border-radius:10px; padding:9px; background:rgba(9,14,26,.85);}    
    .metric .k {font-size:.7rem; color:var(--muted);} 
    .metric .v {font-weight:700;}

    .zone-grid {display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px;}
    .zone {border:1px solid rgba(171,188,229,.2); border-radius:14px; padding:12px; background:rgba(14,20,36,.92);} 
    .zone h5 {margin:0;} .zone p {margin:.35rem 0 0; color:var(--muted); font-size:.76rem;}

    .overworld {
      position:relative; height:270px; border-radius:16px; border:1px solid rgba(165,184,226,.24);
      background:linear-gradient(180deg,#162749 0%,#0f1d35 45%,#0a1528 100%); overflow:hidden;
    }
    .tile {position:absolute; width:70px; height:70px; border:1px solid rgba(163,181,224,.16); border-radius:10px; background:rgba(146,186,255,.05);} 
    .player-dot {position:absolute; width:58px; height:58px; transition:.2s ease all;}
    .badge-mini {position:absolute; right:12px; top:12px; background:rgba(255,255,255,.08); border-radius:999px; border:1px solid rgba(168,188,229,.3); padding:4px 10px; font-size:.72rem;}
    </style>
    """,
        unsafe_allow_html=True,
    )


def _active_pet(profile: PlayerProfile) -> dict[str, Any] | None:
    if not profile.pets:
        return None
    if profile.active_pet_id:
        for pet in profile.pets:
            if pet["id"] == profile.active_pet_id:
                return pet
    return profile.pets[0]


def _win_pct(wins: int, losses: int) -> int:
    total = wins + losses
    return int((wins / total) * 100) if total else 0


def _render_profile_hub(db: dict[str, Any], profile: PlayerProfile) -> PlayerProfile:
    st.subheader("Explorer Profile Hub")
    left, right = st.columns([1.1, 1])

    with left:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("#### Explorer Identity")
        st.markdown(_avatar_svg(profile.avatar, size=210), unsafe_allow_html=True)
        with st.expander("Edit Explorer Avatar", expanded=not profile.starter_selected):
            skin = st.color_picker("Skin tone", profile.avatar["skin_tone"])
            hair_color = st.color_picker("Hair color", profile.avatar["hair_color"])
            top_color = st.color_picker("Top color", profile.avatar["top_color"])
            bottom_color = st.color_picker("Bottom color", profile.avatar["bottom_color"])
            hair_style = st.selectbox("Hair style", ["Short", "Wavy", "Puff", "Mohawk"], index=["Short", "Wavy", "Puff", "Mohawk"].index(profile.avatar["hair_style"]))
            eye_style = st.selectbox("Eye style", ["Round", "Sharp", "Sleepy"], index=["Round", "Sharp", "Sleepy"].index(profile.avatar["eye_style"]))
            top = st.selectbox("Outfit top", ["Scout Jacket", "Raid Hoodie", "Arena Jersey"])
            bottom = st.selectbox("Trousers", ["Trail Pants", "Tech Joggers", "Cargo Shorts"])
            accessory = st.selectbox("Accessory", ["Neck Charm", "Holo Goggles", "Bandana", "None"])
            hat = st.selectbox("Hat / headwear", ["None", "Beanie", "Explorer Cap"])
            body_type = st.selectbox("Body type", ["Compact", "Standard", "Tall"], index=["Compact", "Standard", "Tall"].index(profile.avatar["body_type"]))
            if st.button("Save Avatar", use_container_width=True):
                profile.avatar = {
                    "skin_tone": skin,
                    "hair_style": hair_style,
                    "hair_color": hair_color,
                    "eye_style": eye_style,
                    "top": top,
                    "top_color": top_color,
                    "bottom": bottom,
                    "bottom_color": bottom_color,
                    "accessory": accessory,
                    "hat": hat,
                    "body_type": body_type,
                }
                _save_profile(db, profile)
                st.success("Explorer avatar updated.")
                st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    with right:
        active = _active_pet(profile)
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown(f"### {profile.username}")
        st.caption(profile.title)
        c1, c2, c3 = st.columns(3)
        c1.metric("Zone", profile.zone)
        c2.metric("Pets Owned", len(profile.pets))
        c3.metric("Trainer Level", profile.level)
        c4, c5, c6 = st.columns(3)
        c4.metric("Battle Record", f"{profile.battle_wins}-{profile.battle_losses}")
        c5.metric("Race Record", f"{profile.race_wins}-{profile.race_losses}")
        c6.metric("Favourite Type", profile.favourite_type)
        if active:
            st.markdown("#### Active Pet")
            st.markdown(_pet_render_html(active, compact=True), unsafe_allow_html=True)
        st.markdown("Quick Links: **Stable** • **Overworld** • **Event Room**")
        st.markdown("</div>", unsafe_allow_html=True)
    return profile


def _render_starter_flow(db: dict[str, Any], profile: PlayerProfile) -> PlayerProfile:
    st.markdown("## Choose Your First Grev Pet")
    st.caption("Your first bond defines your playground style. Pick carefully, then confirm adoption.")
    options = st.columns(4)

    for idx, choice in enumerate(STARTER_CHOICES):
        with options[idx]:
            st.markdown("<div class='starter-option'>", unsafe_allow_html=True)
            preview_pet = {
                "name": choice["name"],
                "primary_type": choice["primary_type"],
                "secondary_type": choice["secondary_type"],
                "features": PET_TYPES[choice["primary_type"]]["traits"][:2],
            }
            st.markdown(_pet_render_html(preview_pet, compact=True), unsafe_allow_html=True)
            st.write(f"**Role:** {choice['role']}")
            st.caption(choice["description"])
            stat_line = " | ".join([f"{k} {v}" for k, v in choice["stats"].items()])
            st.caption(stat_line)
            if st.button(f"Select {choice['name']}", key=f"starter_{idx}", use_container_width=True):
                st.session_state["pending_starter"] = choice
            st.markdown("</div>", unsafe_allow_html=True)

    pending = st.session_state.get("pending_starter")
    if pending and not profile.starter_selected:
        st.warning(f"Confirm adoption: **{pending['name']}** ({pending['primary_type']}/{pending['secondary_type']})")
        c1, c2 = st.columns([1, 1])
        if c1.button("Confirm Adoption", use_container_width=True):
            pet = _gen_pet(
                pending["name"],
                pending["primary_type"],
                pending["secondary_type"],
                pending["role"],
                from_starter=True,
            )
            pet["stats"] = pending["stats"]
            profile.pets.append(pet)
            profile.active_pet_id = pet["id"]
            profile.starter_selected = True
            profile.starter_pet_name = pet["name"]
            profile.favourite_type = pending["primary_type"]
            profile.xp += 80
            _save_profile(db, profile)
            st.success(f"{pet['name']} joined your stable. Welcome to Grev Pets Playground!")
            st.session_state.pop("pending_starter", None)
            st.rerun()
        if c2.button("Keep Browsing", use_container_width=True):
            st.session_state.pop("pending_starter", None)
            st.rerun()

    if profile.starter_selected:
        st.success(f"Starter adopted: {profile.starter_pet_name}. You can now explore zones and events.")
    return profile


def _render_landing(db: dict[str, Any], profile: PlayerProfile) -> PlayerProfile:
    active = _active_pet(profile)
    st.markdown(
        f"""
        <section class='hero'>
            <h1>Grev Pets Playground</h1>
            <p>A collectible creature social hub with typed companions, races, and battles.</p>
            <div class='step-row'>
              <span class='step-pill'>1. Customise Explorer</span>
              <span class='step-pill'>2. Choose First Pet</span>
              <span class='step-pill'>3. Enter Overworld</span>
              <span class='step-pill'>4. Expand Stable</span>
              <span class='step-pill'>5. Battle + Race Events</span>
            </div>
        </section>
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns([1.2, 1, 1])
    with row1[0]:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("### Explorer Summary")
        st.markdown(_avatar_svg(profile.avatar, size=172), unsafe_allow_html=True)
        st.write(f"**{profile.username}** • {profile.title}")
        st.caption(f"Zone: {profile.zone} | Level {profile.level} | XP {profile.xp}")
        st.markdown("<span class='step-pill'>Edit Avatar in Profile Hub ↓</span>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with row1[1]:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("### Active Pet Spotlight")
        if active:
            st.markdown(_pet_render_html(active, compact=True), unsafe_allow_html=True)
        else:
            st.info("No active pet yet. Claim your starter below.")
        st.markdown("</div>", unsafe_allow_html=True)

    with row1[2]:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("### Progression")
        st.metric("Trainer Level", profile.level)
        st.metric("Total Pets", len(profile.pets))
        st.metric("Battle Win %", f"{_win_pct(profile.battle_wins, profile.battle_losses)}%")
        st.metric("Race Win %", f"{_win_pct(profile.race_wins, profile.race_losses)}%")
        st.markdown("</div>", unsafe_allow_html=True)

    row2 = st.columns(3)
    with row2[0]:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("### Recent Stable")
        if profile.pets:
            for pet in profile.pets[-3:][::-1]:
                st.markdown(_pet_render_html(pet, compact=True), unsafe_allow_html=True)
        else:
            st.caption("Your stable is empty. Adopt your first pet to start collecting.")
        st.markdown("</div>", unsafe_allow_html=True)
    with row2[1]:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("### World Zones Preview")
        st.markdown(
            """
            <div class='zone-grid'>
              <div class='zone'><h5>Bloom Burrows</h5><p>Moss + Tidal nests, beginner races.</p></div>
              <div class='zone'><h5>Sparkrail</h5><p>Zap duels and obstacle sprints.</p></div>
              <div class='zone'><h5>Obsidian Rim</h5><p>Ember, Stone, and Iron tank events.</p></div>
              <div class='zone'><h5>Null Arcade</h5><p>Glitch/Lunar anomalies and rare spawns.</p></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)

    with row2[2]:
        st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
        st.markdown("### Battle + Race Overview")
        st.caption("Battle advantages come from type matchups. Races reward agility and trick stats.")
        st.markdown(
            "- **Arena Clash:** type advantages, combo timing, pet role synergy\n"
            "- **Speed Tracks:** route memory + agility boosts\n"
            "- **Event Room:** rotating bosses, dual-type tournaments"
        )
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='hub-card'>", unsafe_allow_html=True)
    st.markdown("### Typing Guide Teaser")
    type_cols = st.columns(4)
    for idx, t in enumerate(PET_TYPES.keys()):
        with type_cols[idx % 4]:
            info = PET_TYPES[t]
            st.markdown(f"{_type_badge(t)}", unsafe_allow_html=True)
            st.caption(f"Strong vs {', '.join(info['strong'])} • Weak vs {', '.join(info['weak'])}")
    st.markdown("</div>", unsafe_allow_html=True)

    return profile


def _render_stable_manager(db: dict[str, Any], profile: PlayerProfile) -> PlayerProfile:
    st.subheader("Stable")
    st.caption("Type-influenced generation creates pets with distinct silhouettes, palettes, and trait rolls.")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gen_name = st.text_input("Pet name", value=f"Wildling-{random.randint(10,99)}")
    with c2:
        gen_type = st.selectbox("Primary type", list(PET_TYPES.keys()))
    with c3:
        second_type_opts = ["None"] + list(PET_TYPES.keys())
        gen_secondary = st.selectbox("Secondary type", second_type_opts)
    with c4:
        gen_role = st.selectbox("Role", ["Balanced", "Speedy", "Tanky", "Tricky"])
    if st.button("Generate New Encounter", use_container_width=True):
        pet = _gen_pet(gen_name, gen_type, None if gen_secondary == "None" else gen_secondary, gen_role)
        profile.pets.append(pet)
        profile.xp += 25
        if profile.active_pet_id is None:
            profile.active_pet_id = pet["id"]
        _save_profile(db, profile)
        st.success(f"Encounter complete: {pet['name']} was added to your stable.")
        st.rerun()

    if not profile.pets:
        st.info("No pets in stable yet.")
        return profile

    cols = st.columns(3)
    for idx, pet in enumerate(profile.pets):
        with cols[idx % 3]:
            st.markdown(_pet_render_html(pet), unsafe_allow_html=True)
            if st.button(f"Set Active: {pet['name']}", key=f"active_{pet['id']}", use_container_width=True):
                profile.active_pet_id = pet["id"]
                _save_profile(db, profile)
                st.rerun()
    return profile


def _render_overworld(db: dict[str, Any], profile: PlayerProfile) -> PlayerProfile:
    st.subheader("Overworld")
    st.caption("Explorer marker now uses your custom avatar model, with lightweight mini rendering for movement.")

    step = 1
    left, right, up, down = st.columns(4)
    if left.button("⬅️", use_container_width=True):
        profile.position_x = max(0, profile.position_x - step)
    if right.button("➡️", use_container_width=True):
        profile.position_x = min(5, profile.position_x + step)
    if up.button("⬆️", use_container_width=True):
        profile.position_y = max(0, profile.position_y - step)
    if down.button("⬇️", use_container_width=True):
        profile.position_y = min(2, profile.position_y + step)

    _save_profile(db, profile)

    tiles = []
    for y in range(3):
        for x in range(6):
            tiles.append(f"<div class='tile' style='left:{x*72+12}px; top:{y*84+12}px;'></div>")

    mini = _avatar_svg(profile.avatar, size=58, small=True)
    px = profile.position_x * 72 + 18
    py = profile.position_y * 84 + 16
    st.markdown(
        f"""
        <div class='overworld'>
          {''.join(tiles)}
          <div class='badge-mini'>Zone: {profile.zone}</div>
          <div class='player-dot' style='left:{px}px; top:{py}px'>{mini}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return profile


def main() -> None:
    _inject_style()
    st.title("🐾 Grev Pets Playground")

    db = _load_db()
    with st.sidebar:
        st.header("Session")
        username = st.text_input("Explorer handle", value=st.session_state.get("gp_user", "guest_explorer")).strip() or "guest_explorer"
        st.session_state["gp_user"] = username

    profile = _get_profile(db, username)

    tabs = st.tabs([
        "Landing Hub",
        "Profile Hub",
        "Starter Collection",
        "Stable",
        "Overworld",
    ])

    with tabs[0]:
        profile = _render_landing(db, profile)
    with tabs[1]:
        profile = _render_profile_hub(db, profile)
    with tabs[2]:
        profile = _render_starter_flow(db, profile)
    with tabs[3]:
        profile = _render_stable_manager(db, profile)
    with tabs[4]:
        profile = _render_overworld(db, profile)

    _save_profile(db, profile)


if __name__ == "__main__":
    main()
