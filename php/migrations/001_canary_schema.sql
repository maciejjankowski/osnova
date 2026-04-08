-- Canary Whistleblower System Schema
-- Version: 1.0
-- Date: 2026-04-08

-- Canary messages table
CREATE TABLE IF NOT EXISTS canary_messages (
    canary_id          TEXT PRIMARY KEY,
    creator_key        TEXT NOT NULL,
    created_at         REAL NOT NULL,
    trigger_type       TEXT NOT NULL CHECK(trigger_type IN ('dead_man', 'eject', 'compromise', 'time_lock', 'network_silence')),
    dead_man_threshold INTEGER NOT NULL DEFAULT 259200,  -- 72 hours in seconds
    status             TEXT NOT NULL DEFAULT 'armed' CHECK(status IN ('armed', 'triggered', 'released', 'cancelled')),
    last_heartbeat     REAL NOT NULL,
    anonymous          INTEGER NOT NULL DEFAULT 0,
    metadata           TEXT NOT NULL DEFAULT '{}'
);

CREATE INDEX idx_canary_status ON canary_messages (status);
CREATE INDEX idx_canary_heartbeat ON canary_messages (last_heartbeat);
CREATE INDEX idx_canary_creator ON canary_messages (creator_key);

-- Fragment distribution tracking
CREATE TABLE IF NOT EXISTS canary_fragments (
    fragment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id        TEXT NOT NULL,
    layer            TEXT NOT NULL CHECK(layer IN ('seed', 'paragraph', 'page', 'document')),
    fragment_index   INTEGER NOT NULL,
    peer_key         TEXT NOT NULL,
    ring_level       TEXT NOT NULL CHECK(ring_level IN ('core', 'inner', 'middle', 'outer')),
    encrypted_data   TEXT NOT NULL,
    time_lock        TEXT DEFAULT NULL,  -- JSON time-lock puzzle data
    distributed_at   REAL NOT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id),
    UNIQUE(canary_id, layer, fragment_index, peer_key)
);

CREATE INDEX idx_fragments_canary ON canary_fragments (canary_id);
CREATE INDEX idx_fragments_peer ON canary_fragments (peer_key);
CREATE INDEX idx_fragments_layer ON canary_fragments (canary_id, layer);

-- Encryption keys per ring
CREATE TABLE IF NOT EXISTS canary_keys (
    key_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    ring_level      TEXT NOT NULL CHECK(ring_level IN ('core', 'inner', 'middle', 'outer')),
    key_share_index INTEGER NOT NULL,
    encrypted_key   TEXT NOT NULL,
    peer_key        TEXT NOT NULL,
    created_at      REAL NOT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id),
    UNIQUE(canary_id, ring_level, key_share_index)
);

CREATE INDEX idx_keys_canary ON canary_keys (canary_id, ring_level);

-- Trigger events log
CREATE TABLE IF NOT EXISTS canary_triggers (
    trigger_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    trigger_type    TEXT NOT NULL,
    detected_at     REAL NOT NULL,
    detected_by     TEXT NOT NULL,  -- peer who detected
    evidence        TEXT NOT NULL DEFAULT '{}',  -- JSON evidence
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

CREATE INDEX idx_triggers_canary ON canary_triggers (canary_id);
CREATE INDEX idx_triggers_time ON canary_triggers (detected_at DESC);

-- Reconstruction attempts
CREATE TABLE IF NOT EXISTS canary_reconstructions (
    reconstruction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id        TEXT NOT NULL,
    layer            TEXT NOT NULL,
    ring_level       TEXT NOT NULL,
    fragments_used   TEXT NOT NULL,  -- JSON array of fragment IDs
    reconstructed_at REAL NOT NULL,
    success          INTEGER NOT NULL,
    reconstructed_text TEXT DEFAULT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

CREATE INDEX idx_reconstructions_canary ON canary_reconstructions (canary_id);
CREATE INDEX idx_reconstructions_success ON canary_reconstructions (canary_id, success);

-- Heartbeat tracking
CREATE TABLE IF NOT EXISTS canary_heartbeats (
    heartbeat_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    timestamp       REAL NOT NULL,
    sender_key      TEXT NOT NULL,
    nonce           TEXT DEFAULT NULL,  -- For duress detection
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

CREATE INDEX idx_heartbeats_canary ON canary_heartbeats (canary_id, timestamp DESC);

-- Steganographic channel posts
CREATE TABLE IF NOT EXISTS canary_stego_posts (
    post_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    fragment_id     INTEGER NOT NULL,
    channel_type    TEXT NOT NULL CHECK(channel_type IN ('tire_forum', 'contractor_quote', 'meme_site', 'fatk_forum', 'tech_forum', 'job_posting', 'recipe_site')),
    cover_content   TEXT NOT NULL,  -- The innocent-looking content
    posted_at       REAL NOT NULL,
    platform_url    TEXT DEFAULT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id),
    FOREIGN KEY (fragment_id) REFERENCES canary_fragments(fragment_id)
);

CREATE INDEX idx_stego_canary ON canary_stego_posts (canary_id);
CREATE INDEX idx_stego_channel ON canary_stego_posts (channel_type);
