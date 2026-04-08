<?php
/**
 * Triangulated Content Discovery
 *
 * Creates message/countermessage/challenge triads so content location
 * requires ring context to resolve (machines see two equally valid candidates).
 *
 * Ported from osnova/discovery/triangulation.py.
 */

// ---------------------------------------------------------------------------
// Core functions
// ---------------------------------------------------------------------------

/**
 * Create a discovery triad for a piece of content.
 *
 * Returns a serializable array representing the DiscoveryTriad.
 */
function discovery_create_triad(
    string $content_hash,
    string $author_key,
    string $real_holder_key,
    string $decoy_key
): array {
    $triad_id = hash('sha256', $content_hash . $author_key . microtime(true));
    $salt     = bin2hex(random_bytes(16));

    // MESSAGE key: points toward the real holder
    $message_fragment = derive_candidate_fragment($content_hash, $real_holder_key, $salt, 'message');
    $message_key = [
        'key_id'         => hash('sha256', $triad_id . 'message'),
        'signal_type'    => 'message',
        'fragment'       => $message_fragment,
        'candidate_key'  => $real_holder_key,
        'created_at'     => microtime(true),
    ];

    // COUNTERMESSAGE key: structurally identical but points to the decoy
    $counter_fragment = derive_candidate_fragment($content_hash, $decoy_key, $salt, 'countermessage');
    $counter_key = [
        'key_id'        => hash('sha256', $triad_id . 'countermessage'),
        'signal_type'   => 'countermessage',
        'fragment'      => $counter_fragment,
        'candidate_key' => $decoy_key,
        'created_at'    => microtime(true),
    ];

    // CHALLENGE key: the resolution test
    $challenge_fragment = derive_challenge_fragment($content_hash, $real_holder_key, $decoy_key, $salt);
    $challenge_key = [
        'key_id'        => hash('sha256', $triad_id . 'challenge'),
        'signal_type'   => 'challenge',
        'fragment'      => $challenge_fragment,
        'candidate_key' => '',
        'created_at'    => microtime(true),
    ];

    return [
        'triad_id'        => $triad_id,
        'content_hash'    => $content_hash,
        'author_key'      => $author_key,
        'message'         => $message_key,
        'countermessage'  => $counter_key,
        'challenge'       => $challenge_key,
        'real_holder_key' => $real_holder_key,
        'decoy_key'       => $decoy_key,
        'salt'            => $salt,
        'created_at'      => microtime(true),
    ];
}

/**
 * Verify that a chosen candidate resolves the challenge correctly.
 * Only ring members with context can pass this.
 */
function discovery_verify_resolution(array $triad, string $chosen_candidate, string $content_hash): bool {
    if ($content_hash !== $triad['content_hash']) return false;
    return $chosen_candidate === $triad['real_holder_key'];
}

/**
 * Derive a fragment for a message or countermessage key.
 */
function derive_candidate_fragment(string $content_hash, string $candidate_key, string $salt, string $role): string {
    return hash_hmac('sha256', $content_hash . ':' . $candidate_key . ':' . $role, $salt);
}

/**
 * Derive the challenge fragment (combines both candidates).
 */
function derive_challenge_fragment(string $content_hash, string $real_key, string $decoy_key, string $salt): string {
    $combined = $real_key . ':' . $decoy_key;
    return hash_hmac('sha256', $content_hash . ':' . $combined, $salt);
}

/**
 * Select a decoy from the peer list (not self, deterministic from content hash).
 * Returns null if no peers available.
 */
function discovery_select_decoy(array $peers, string $self_key, string $content_hash): ?string {
    $candidates = array_filter($peers, fn($p) => ($p['public_key'] ?? '') !== $self_key);
    $candidates = array_values($candidates);
    if (empty($candidates)) return null;
    // Deterministic selection
    $index = hexdec(substr(hash('sha256', $content_hash . $self_key), 0, 8)) % count($candidates);
    return $candidates[$index]['public_key'];
}

// ---------------------------------------------------------------------------
// SQLite store for triads
// ---------------------------------------------------------------------------
class TriadStore {
    private SQLite3 $db;

    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS triads (
                triad_id   TEXT PRIMARY KEY,
                data       TEXT NOT NULL,
                created_at REAL NOT NULL
            )
        ");
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS received_keys (
                key_id      TEXT PRIMARY KEY,
                data        TEXT NOT NULL,
                received_at REAL NOT NULL
            )
        ");
    }

    public function save(array $triad): void {
        $stmt = $this->db->prepare("INSERT OR REPLACE INTO triads (triad_id, data, created_at) VALUES (?, ?, ?)");
        $stmt->bindValue(1, $triad['triad_id'], SQLITE3_TEXT);
        $stmt->bindValue(2, json_encode($triad), SQLITE3_TEXT);
        $stmt->bindValue(3, $triad['created_at'] ?? microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
    }

    public function find(string $triad_id): ?array {
        $stmt = $this->db->prepare("SELECT data FROM triads WHERE triad_id = ?");
        $stmt->bindValue(1, $triad_id, SQLITE3_TEXT);
        $res  = $stmt->execute();
        $row  = $res->fetchArray(SQLITE3_NUM);
        return $row ? json_decode($row[0], true) : null;
    }

    public function listAll(): array {
        $res   = $this->db->query("SELECT data FROM triads ORDER BY created_at DESC");
        $items = [];
        while ($row = $res->fetchArray(SQLITE3_NUM)) {
            $items[] = json_decode($row[0], true);
        }
        return $items;
    }

    public function saveKey(array $key): void {
        $stmt = $this->db->prepare("INSERT OR REPLACE INTO received_keys (key_id, data, received_at) VALUES (?, ?, ?)");
        $stmt->bindValue(1, $key['key_id'], SQLITE3_TEXT);
        $stmt->bindValue(2, json_encode($key), SQLITE3_TEXT);
        $stmt->bindValue(3, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
    }
}
