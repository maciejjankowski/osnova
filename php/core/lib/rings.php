<?php
/**
 * RingManager - Dunbar-capped trust rings backed by SQLite.
 */
class RingManager {
    private SQLite3 $db;

    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->initialize();
    }

    private function initialize(): void {
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS peers (
                public_key   TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                ring_level   TEXT NOT NULL,
                endpoint     TEXT NOT NULL,
                added_at     REAL NOT NULL,
                last_seen    REAL NOT NULL DEFAULT 0.0
            )
        ");
    }

    /** Add a peer to a ring. Returns false if at capacity or duplicate. */
    public function addPeer(array $peer): bool {
        $level = $peer['ring_level'];
        $caps = RING_CAPS;
        if (!isset($caps[$level])) return false;
        if ($this->countRing($level) >= $caps[$level]) return false;

        try {
            $stmt = $this->db->prepare("
                INSERT INTO peers (public_key, display_name, ring_level, endpoint, added_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            ");
            $stmt->bindValue(1, $peer['public_key'],   SQLITE3_TEXT);
            $stmt->bindValue(2, $peer['display_name'], SQLITE3_TEXT);
            $stmt->bindValue(3, $level,                SQLITE3_TEXT);
            $stmt->bindValue(4, $peer['endpoint'],     SQLITE3_TEXT);
            $stmt->bindValue(5, $peer['added_at'] ?? microtime(true), SQLITE3_FLOAT);
            $stmt->bindValue(6, $peer['last_seen'] ?? 0.0,            SQLITE3_FLOAT);
            $stmt->execute();
            return true;
        } catch (\Exception) {
            return false; // UNIQUE constraint violation
        }
    }

    /** Remove a peer. Returns false if not found. */
    public function removePeer(string $public_key): bool {
        $stmt = $this->db->prepare("DELETE FROM peers WHERE public_key = ?");
        $stmt->bindValue(1, $public_key, SQLITE3_TEXT);
        $stmt->execute();
        return $this->db->changes() > 0;
    }

    /** Get a single peer by public key. */
    public function getPeer(string $public_key): ?array {
        $stmt = $this->db->prepare("SELECT * FROM peers WHERE public_key = ?");
        $stmt->bindValue(1, $public_key, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        return $row ? $this->rowToPeer($row) : null;
    }

    /** All peers in a ring level. */
    public function getPeersByRing(string $ring_level): array {
        $stmt = $this->db->prepare("SELECT * FROM peers WHERE ring_level = ? ORDER BY added_at");
        $stmt->bindValue(1, $ring_level, SQLITE3_TEXT);
        $res = $stmt->execute();
        $peers = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $peers[] = $this->rowToPeer($row);
        }
        return $peers;
    }

    /** All peers across all rings. */
    public function getAllPeers(): array {
        $res = $this->db->query("SELECT * FROM peers ORDER BY ring_level, added_at");
        $peers = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $peers[] = $this->rowToPeer($row);
        }
        return $peers;
    }

    /** CORE + INNER + MIDDLE peers (for gossip sync). */
    public function getSyncPeers(): array {
        $res = $this->db->query("
            SELECT * FROM peers
            WHERE ring_level IN ('core', 'inner', 'middle')
            ORDER BY ring_level, added_at
        ");
        $peers = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $peers[] = $this->rowToPeer($row);
        }
        return $peers;
    }

    /** Promote or demote a peer to a new ring level. */
    public function setPeerRing(string $public_key, string $new_level): bool {
        $caps = RING_CAPS;
        if (!isset($caps[$new_level])) return false;
        $peer = $this->getPeer($public_key);
        if (!$peer) return false;
        if ($peer['ring_level'] !== $new_level && $this->countRing($new_level) >= $caps[$new_level]) return false;

        $stmt = $this->db->prepare("UPDATE peers SET ring_level = ? WHERE public_key = ?");
        $stmt->bindValue(1, $new_level,  SQLITE3_TEXT);
        $stmt->bindValue(2, $public_key, SQLITE3_TEXT);
        $stmt->execute();
        return $this->db->changes() > 0;
    }

    /** Update last_seen timestamp for a peer. */
    public function updateLastSeen(string $public_key, float $timestamp): void {
        $stmt = $this->db->prepare("UPDATE peers SET last_seen = ? WHERE public_key = ?");
        $stmt->bindValue(1, $timestamp,  SQLITE3_FLOAT);
        $stmt->bindValue(2, $public_key, SQLITE3_TEXT);
        $stmt->execute();
    }

    /** Ring stats: count per level + total. */
    public function getRingStats(): array {
        $res = $this->db->query("SELECT ring_level, COUNT(*) as cnt FROM peers GROUP BY ring_level");
        $counts = ['core' => 0, 'inner' => 0, 'middle' => 0, 'outer' => 0];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $counts[$row['ring_level']] = (int)$row['cnt'];
        }
        $counts['total'] = array_sum($counts);
        return $counts;
    }

    // -----------------------------------------------------------------------
    private function countRing(string $level): int {
        $stmt = $this->db->prepare("SELECT COUNT(*) FROM peers WHERE ring_level = ?");
        $stmt->bindValue(1, $level, SQLITE3_TEXT);
        $res = $stmt->execute();
        return (int)$res->fetchArray(SQLITE3_NUM)[0];
    }

    private function rowToPeer(array $row): array {
        return [
            'public_key'   => $row['public_key'],
            'display_name' => $row['display_name'],
            'ring_level'   => $row['ring_level'],
            'endpoint'     => $row['endpoint'],
            'added_at'     => (float)$row['added_at'],
            'last_seen'    => (float)$row['last_seen'],
        ];
    }
}
