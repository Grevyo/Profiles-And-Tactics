-- Grev Pets Playground additive upgrade schema
-- Stores explorer avatar layers, typed pets, starter state, and profile summary.

CREATE TABLE IF NOT EXISTS grev_pets_profiles (
    user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    explorer_title TEXT NOT NULL DEFAULT 'Rookie Tamer',
    zone TEXT NOT NULL DEFAULT 'Home Camp',
    trainer_level INTEGER NOT NULL DEFAULT 1,
    xp INTEGER NOT NULL DEFAULT 0,
    favourite_type TEXT,
    battle_wins INTEGER NOT NULL DEFAULT 0,
    battle_losses INTEGER NOT NULL DEFAULT 0,
    race_wins INTEGER NOT NULL DEFAULT 0,
    race_losses INTEGER NOT NULL DEFAULT 0,
    starter_selected INTEGER NOT NULL DEFAULT 0,
    starter_pet_id TEXT,
    starter_pet_name TEXT,
    active_pet_id TEXT,
    avatar_json TEXT NOT NULL,
    position_x INTEGER NOT NULL DEFAULT 2,
    position_y INTEGER NOT NULL DEFAULT 2,
    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grev_pets_creatures (
    pet_id TEXT PRIMARY KEY,
    owner_user_id TEXT NOT NULL,
    pet_name TEXT NOT NULL,
    rarity TEXT NOT NULL DEFAULT 'Common',
    role_style TEXT NOT NULL DEFAULT 'Balanced',
    primary_type TEXT NOT NULL,
    secondary_type TEXT,
    visual_seed TEXT,
    features_json TEXT,
    stats_json TEXT,
    is_starter INTEGER NOT NULL DEFAULT 0,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (owner_user_id) REFERENCES grev_pets_profiles(user_id)
);

CREATE INDEX IF NOT EXISTS idx_grev_pets_creatures_owner ON grev_pets_creatures(owner_user_id);
CREATE INDEX IF NOT EXISTS idx_grev_pets_creatures_types ON grev_pets_creatures(primary_type, secondary_type);
