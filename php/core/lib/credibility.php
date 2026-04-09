<?php
/**
 * Credibility flagging system - flag questionable content, seek more context.
 * Allows ring members to mark content for review without censoring.
 */

class CredibilityFlag {
    const NEEDS_VERIFICATION = 'needs_verification';
    const NEEDS_CONTEXT = 'needs_context';
    const DISPUTED = 'disputed';
    const CONFIRMED = 'confirmed';
}

class CredibilityManager {
    private SQLite3 $db;
    
    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->initialize();
    }
    
    private function initialize(): void {
        // Credibility flags table
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS credibility_flags (
                flag_id       INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash  TEXT NOT NULL,
                flagger_key   TEXT NOT NULL,
                flag_type     TEXT NOT NULL,
                reason        TEXT NOT NULL DEFAULT '',
                timestamp     REAL NOT NULL,
                resolved      INTEGER NOT NULL DEFAULT 0,
                resolved_at   REAL DEFAULT NULL,
                resolution    TEXT DEFAULT NULL
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_cred_content ON credibility_flags (content_hash)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_cred_resolved ON credibility_flags (resolved)");
        
        // Context contributions (ring members providing additional context)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS context_contributions (
                contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_hash    TEXT NOT NULL,
                contributor_key TEXT NOT NULL,
                context_text    TEXT NOT NULL,
                sources         TEXT NOT NULL DEFAULT '[]',
                timestamp       REAL NOT NULL,
                helpful_votes   INTEGER NOT NULL DEFAULT 0
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_context_content ON context_contributions (content_hash)");
    }
    
    /**
     * Flag content as needing verification/context.
     */
    public function flagContent(string $content_hash, string $flagger_key, string $flag_type, string $reason = ''): int {
        $stmt = $this->db->prepare("
            INSERT INTO credibility_flags (content_hash, flagger_key, flag_type, reason, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        $stmt->bindValue(2, $flagger_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $flag_type, SQLITE3_TEXT);
        $stmt->bindValue(4, $reason, SQLITE3_TEXT);
        $stmt->bindValue(5, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        return $this->db->lastInsertRowID();
    }
    
    /**
     * Add context/evidence to flagged content.
     */
    public function addContext(string $content_hash, string $contributor_key, string $context_text, array $sources = []): int {
        $stmt = $this->db->prepare("
            INSERT INTO context_contributions (content_hash, contributor_key, context_text, sources, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        $stmt->bindValue(2, $contributor_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $context_text, SQLITE3_TEXT);
        $stmt->bindValue(4, json_encode($sources), SQLITE3_TEXT);
        $stmt->bindValue(5, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        return $this->db->lastInsertRowID();
    }
    
    /**
     * Vote a context contribution as helpful.
     */
    public function voteContextHelpful(int $contribution_id): void {
        $stmt = $this->db->prepare("
            UPDATE context_contributions SET helpful_votes = helpful_votes + 1 WHERE contribution_id = ?
        ");
        $stmt->bindValue(1, $contribution_id, SQLITE3_INTEGER);
        $stmt->execute();
    }
    
    /**
     * Get all flags for a content item.
     */
    public function getFlags(string $content_hash): array {
        $stmt = $this->db->prepare("
            SELECT * FROM credibility_flags WHERE content_hash = ? ORDER BY timestamp DESC
        ");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $flags = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $flags[] = $row;
        }
        return $flags;
    }
    
    /**
     * Get context contributions for a content item.
     */
    public function getContext(string $content_hash): array {
        $stmt = $this->db->prepare("
            SELECT * FROM context_contributions WHERE content_hash = ? ORDER BY helpful_votes DESC, timestamp DESC
        ");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $contexts = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $row['sources'] = json_decode($row['sources'], true);
            $contexts[] = $row;
        }
        return $contexts;
    }
    
    /**
     * Get credibility score for content (0-100).
     * Based on: flag count (negative), context contributions (positive), resolution status.
     */
    public function getCredibilityScore(string $content_hash): int {
        $flags = $this->getFlags($content_hash);
        $contexts = $this->getContext($content_hash);
        
        if (empty($flags)) {
            return 100; // No flags = full credibility
        }
        
        // Count unresolved flags
        $unresolved_flags = array_filter($flags, fn($f) => !$f['resolved']);
        $flag_penalty = count($unresolved_flags) * 10;
        
        // Count helpful contexts
        $context_bonus = min(30, count($contexts) * 10);
        
        // Check if any flags are resolved as "confirmed"
        $confirmed = array_filter($flags, fn($f) => $f['resolved'] && $f['resolution'] === CredibilityFlag::CONFIRMED);
        if (!empty($confirmed)) {
            return 90 + $context_bonus; // Confirmed after review
        }
        
        $score = 100 - $flag_penalty + $context_bonus;
        return max(0, min(100, $score));
    }
    
    /**
     * Resolve a flag (mark as reviewed).
     */
    public function resolveFlag(int $flag_id, string $resolution): void {
        $stmt = $this->db->prepare("
            UPDATE credibility_flags SET resolved = 1, resolved_at = ?, resolution = ? WHERE flag_id = ?
        ");
        $stmt->bindValue(1, microtime(true), SQLITE3_FLOAT);
        $stmt->bindValue(2, $resolution, SQLITE3_TEXT);
        $stmt->bindValue(3, $flag_id, SQLITE3_INTEGER);
        $stmt->execute();
    }
}
