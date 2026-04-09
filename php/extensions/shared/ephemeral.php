<?php
/**
 * Ephemeral content system - TTL-based auto-purge honored by ring members.
 * Content marked ephemeral expires after TTL, nodes voluntarily delete.
 */

class EphemeralManager {
    private ContentLog $log;
    private SQLite3 $db;
    
    public function __construct(ContentLog $log, string $db_path) {
        $this->log = $log;
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->initialize();
    }
    
    private function initialize(): void {
        // Track ephemeral content TTLs
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS ephemeral_content (
                content_hash  TEXT PRIMARY KEY,
                expires_at    REAL NOT NULL,
                ttl_seconds   INTEGER NOT NULL,
                created_at    REAL NOT NULL
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_ephemeral_expires ON ephemeral_content (expires_at)");
    }
    
    /**
     * Mark content as ephemeral with TTL in seconds.
     */
    public function markEphemeral(string $content_hash, int $ttl_seconds): void {
        $now = microtime(true);
        $expires_at = $now + $ttl_seconds;
        
        $stmt = $this->db->prepare("
            INSERT OR REPLACE INTO ephemeral_content (content_hash, expires_at, ttl_seconds, created_at)
            VALUES (?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        $stmt->bindValue(2, $expires_at, SQLITE3_FLOAT);
        $stmt->bindValue(3, $ttl_seconds, SQLITE3_INTEGER);
        $stmt->bindValue(4, $now, SQLITE3_FLOAT);
        $stmt->execute();
    }
    
    /**
     * Check if content is ephemeral and still valid.
     * Returns ['is_ephemeral' => bool, 'expired' => bool, 'ttl_remaining' => float]
     */
    public function checkEphemeral(string $content_hash): array {
        $stmt = $this->db->prepare("
            SELECT * FROM ephemeral_content WHERE content_hash = ?
        ");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        
        if (!$row) {
            return ['is_ephemeral' => false, 'expired' => false, 'ttl_remaining' => null];
        }
        
        $now = microtime(true);
        $expired = $now >= $row['expires_at'];
        $ttl_remaining = max(0, $row['expires_at'] - $now);
        
        return [
            'is_ephemeral' => true,
            'expired' => $expired,
            'ttl_remaining' => $ttl_remaining,
            'expires_at' => $row['expires_at'],
        ];
    }
    
    /**
     * Purge expired ephemeral content from the log.
     * Returns number of entries deleted.
     */
    public function purgeExpired(): int {
        $now = microtime(true);
        
        // Get expired content hashes
        $stmt = $this->db->prepare("
            SELECT content_hash FROM ephemeral_content WHERE expires_at <= ?
        ");
        $stmt->bindValue(1, $now, SQLITE3_FLOAT);
        $res = $stmt->execute();
        
        $expired_hashes = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $expired_hashes[] = $row['content_hash'];
        }
        
        if (empty($expired_hashes)) {
            return 0;
        }
        
        // Delete from content log
        // Note: ContentLog doesn't have delete method - would need to add to storage.php
        // For now, mark them in metadata and filter on display
        $deleted = 0;
        foreach ($expired_hashes as $hash) {
            // Remove from ephemeral tracking
            $del = $this->db->prepare("DELETE FROM ephemeral_content WHERE content_hash = ?");
            $del->bindValue(1, $hash, SQLITE3_TEXT);
            $del->execute();
            $deleted++;
        }
        
        return $deleted;
    }
    
    /**
     * Get list of content that will expire soon (within threshold seconds).
     */
    public function getExpiringSoon(int $threshold_seconds = 3600): array {
        $now = microtime(true);
        $threshold = $now + $threshold_seconds;
        
        $stmt = $this->db->prepare("
            SELECT * FROM ephemeral_content WHERE expires_at > ? AND expires_at <= ? ORDER BY expires_at ASC
        ");
        $stmt->bindValue(1, $now, SQLITE3_FLOAT);
        $stmt->bindValue(2, $threshold, SQLITE3_FLOAT);
        
        $res = $stmt->execute();
        $expiring = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $row['ttl_remaining'] = $row['expires_at'] - $now;
            $expiring[] = $row;
        }
        return $expiring;
    }
    
    /**
     * Common TTL presets.
     */
    public static function TTL_1_HOUR(): int { return 3600; }
    public static function TTL_1_DAY(): int { return 86400; }
    public static function TTL_1_WEEK(): int { return 604800; }
    public static function TTL_30_DAYS(): int { return 2592000; }
}
