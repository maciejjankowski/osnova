<?php
/**
 * SignalStore - persistent storage for adversarial signals and discovery triads.
 * Previously in-memory, now SQLite-backed for persistence across restarts.
 */

class SignalStore {
    private SQLite3 $db;
    
    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->initialize();
    }
    
    private function initialize(): void {
        // Signals table
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS signals (
                signal_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_type   TEXT NOT NULL,
                author_key    TEXT NOT NULL,
                message       TEXT NOT NULL DEFAULT '',
                timestamp     REAL NOT NULL,
                signature     TEXT NOT NULL DEFAULT '',
                severity      TEXT NOT NULL DEFAULT 'critical',
                metadata      TEXT NOT NULL DEFAULT '{}'
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals (timestamp DESC)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_signals_type ON signals (signal_type)");
        
        // Triads table (discovery keys split into three parts)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS triads (
                triad_id      INTEGER PRIMARY KEY AUTOINCREMENT,
                message_peer  TEXT NOT NULL,
                counter_peer  TEXT NOT NULL,
                challenge_peer TEXT NOT NULL,
                target_key    TEXT NOT NULL,
                created_at    REAL NOT NULL,
                resolved      INTEGER NOT NULL DEFAULT 0,
                resolved_at   REAL DEFAULT NULL
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_triads_target ON triads (target_key)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_triads_resolved ON triads (resolved)");
    }
    
    /**
     * Store a signal (canary, eject, etc).
     */
    public function storeSignal(array $signal): int {
        $stmt = $this->db->prepare("
            INSERT INTO signals (signal_type, author_key, message, timestamp, signature, severity, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $signal['signal_type'], SQLITE3_TEXT);
        $stmt->bindValue(2, $signal['author_key'], SQLITE3_TEXT);
        $stmt->bindValue(3, $signal['message'] ?? '', SQLITE3_TEXT);
        $stmt->bindValue(4, (float)$signal['timestamp'], SQLITE3_FLOAT);
        $stmt->bindValue(5, $signal['signature'] ?? '', SQLITE3_TEXT);
        $stmt->bindValue(6, $signal['severity'] ?? 'critical', SQLITE3_TEXT);
        $stmt->bindValue(7, json_encode($signal['metadata'] ?? []), SQLITE3_TEXT);
        $stmt->execute();
        return $this->db->lastInsertRowID();
    }
    
    /**
     * Get recent signals of a specific type.
     */
    public function getSignals(string $type, int $limit = 50): array {
        $stmt = $this->db->prepare("
            SELECT * FROM signals WHERE signal_type = ? ORDER BY timestamp DESC LIMIT ?
        ");
        $stmt->bindValue(1, $type, SQLITE3_TEXT);
        $stmt->bindValue(2, $limit, SQLITE3_INTEGER);
        
        $res = $stmt->execute();
        $signals = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $row['metadata'] = json_decode($row['metadata'], true);
            $signals[] = $row;
        }
        return $signals;
    }
    
    /**
     * Store a discovery triad.
     */
    public function storeTriad(string $message_peer, string $counter_peer, string $challenge_peer, string $target_key): int {
        $stmt = $this->db->prepare("
            INSERT INTO triads (message_peer, counter_peer, challenge_peer, target_key, created_at)
            VALUES (?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $message_peer, SQLITE3_TEXT);
        $stmt->bindValue(2, $counter_peer, SQLITE3_TEXT);
        $stmt->bindValue(3, $challenge_peer, SQLITE3_TEXT);
        $stmt->bindValue(4, $target_key, SQLITE3_TEXT);
        $stmt->bindValue(5, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        return $this->db->lastInsertRowID();
    }
    
    /**
     * Get unresolved triads for a target key.
     */
    public function getUnresolvedTriads(string $target_key): array {
        $stmt = $this->db->prepare("
            SELECT * FROM triads WHERE target_key = ? AND resolved = 0 ORDER BY created_at DESC
        ");
        $stmt->bindValue(1, $target_key, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $triads = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $triads[] = $row;
        }
        return $triads;
    }
    
    /**
     * Mark a triad as resolved.
     */
    public function resolveTriad(int $triad_id): void {
        $stmt = $this->db->prepare("
            UPDATE triads SET resolved = 1, resolved_at = ? WHERE triad_id = ?
        ");
        $stmt->bindValue(1, microtime(true), SQLITE3_FLOAT);
        $stmt->bindValue(2, $triad_id, SQLITE3_INTEGER);
        $stmt->execute();
    }
    
    /**
     * Get all triads (for debugging/admin).
     */
    public function getAllTriads(int $limit = 100): array {
        $stmt = $this->db->prepare("
            SELECT * FROM triads ORDER BY created_at DESC LIMIT ?
        ");
        $stmt->bindValue(1, $limit, SQLITE3_INTEGER);
        
        $res = $stmt->execute();
        $triads = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $triads[] = $row;
        }
        return $triads;
    }
}
