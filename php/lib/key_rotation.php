<?php
/**
 * Key rotation with threshold signatures (k-of-n inner ring co-sign).
 * Enables secure key rotation without single point of failure.
 * 
 * Note: Full threshold signature crypto (Shamir Secret Sharing + multi-sig)
 * would require libsodium extensions or external crypto lib.
 * This implementation provides the coordination layer for rotation.
 */

class KeyRotation {
    private SQLite3 $db;
    private RingManager $rings;
    
    public function __construct(string $db_path, RingManager $rings) {
        $this->db = new SQLite3($db_path);
        $this->rings = $rings;
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->initialize();
    }
    
    private function initialize(): void {
        // Key rotation proposals
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS key_rotations (
                rotation_id    TEXT PRIMARY KEY,
                old_key        TEXT NOT NULL,
                new_key        TEXT NOT NULL,
                threshold      INTEGER NOT NULL,
                required_sigs  INTEGER NOT NULL,
                status         TEXT NOT NULL DEFAULT 'pending',
                initiated_at   REAL NOT NULL,
                activated_at   REAL DEFAULT NULL,
                reason         TEXT NOT NULL DEFAULT ''
            )
        ");
        
        // Co-signatures from inner ring members
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS rotation_signatures (
                sig_id        INTEGER PRIMARY KEY AUTOINCREMENT,
                rotation_id   TEXT NOT NULL,
                signer_key    TEXT NOT NULL,
                signature     TEXT NOT NULL,
                signed_at     REAL NOT NULL,
                UNIQUE(rotation_id, signer_key)
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_rotation_sigs ON rotation_signatures (rotation_id)");
        
        // Key history (audit trail)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS key_history (
                history_id    INTEGER PRIMARY KEY AUTOINCREMENT,
                identity_key  TEXT NOT NULL,
                old_key       TEXT NOT NULL,
                new_key       TEXT NOT NULL,
                rotation_id   TEXT NOT NULL,
                rotated_at    REAL NOT NULL
            )
        ");
    }
    
    /**
     * Initiate key rotation proposal.
     * Requires k-of-n inner ring signatures to activate.
     */
    public function proposeRotation(string $old_key, string $new_key, string $reason = '', ?int $threshold = null, ?int $required_sigs = null): string {
        $rotation_id = bin2hex(random_bytes(16));
        
        // Default: require majority of inner ring
        if ($threshold === null || $required_sigs === null) {
            $inner_peers = $this->rings->getPeersByRing('inner');
            $inner_count = count($inner_peers);
            $threshold = max(3, ceil($inner_count / 2)); // At least 3, or majority
            $required_sigs = $threshold;
        }
        
        $stmt = $this->db->prepare("
            INSERT INTO key_rotations (rotation_id, old_key, new_key, threshold, required_sigs, initiated_at, reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $rotation_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $old_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $new_key, SQLITE3_TEXT);
        $stmt->bindValue(4, $threshold, SQLITE3_INTEGER);
        $stmt->bindValue(5, $required_sigs, SQLITE3_INTEGER);
        $stmt->bindValue(6, microtime(true), SQLITE3_FLOAT);
        $stmt->bindValue(7, $reason, SQLITE3_TEXT);
        $stmt->execute();
        
        return $rotation_id;
    }
    
    /**
     * Co-sign a rotation proposal (inner ring member approval).
     */
    public function coSign(string $rotation_id, string $signer_key, string $signature): bool {
        // Verify signer is in inner ring
        $peer = $this->rings->getPeer($signer_key);
        if (!$peer || !in_array($peer['ring_level'], ['core', 'inner'])) {
            return false; // Only core/inner can co-sign
        }
        
        // Get rotation
        $rotation = $this->getRotation($rotation_id);
        if (!$rotation || $rotation['status'] !== 'pending') {
            return false; // Already activated or not found
        }
        
        // Record signature
        $stmt = $this->db->prepare("
            INSERT OR IGNORE INTO rotation_signatures (rotation_id, signer_key, signature, signed_at)
            VALUES (?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $rotation_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $signer_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $signature, SQLITE3_TEXT);
        $stmt->bindValue(4, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        
        // Check if threshold reached
        $sig_count = $this->getSignatureCount($rotation_id);
        if ($sig_count >= $rotation['required_sigs']) {
            $this->activateRotation($rotation_id);
        }
        
        return true;
    }
    
    /**
     * Activate rotation once threshold reached.
     */
    private function activateRotation(string $rotation_id): void {
        $rotation = $this->getRotation($rotation_id);
        if (!$rotation) return;
        
        // Mark as activated
        $stmt = $this->db->prepare("
            UPDATE key_rotations SET status = 'activated', activated_at = ? WHERE rotation_id = ?
        ");
        $stmt->bindValue(1, microtime(true), SQLITE3_FLOAT);
        $stmt->bindValue(2, $rotation_id, SQLITE3_TEXT);
        $stmt->execute();
        
        // Record in history
        $histStmt = $this->db->prepare("
            INSERT INTO key_history (identity_key, old_key, new_key, rotation_id, rotated_at)
            VALUES (?, ?, ?, ?, ?)
        ");
        $histStmt->bindValue(1, $rotation['old_key'], SQLITE3_TEXT);
        $histStmt->bindValue(2, $rotation['old_key'], SQLITE3_TEXT);
        $histStmt->bindValue(3, $rotation['new_key'], SQLITE3_TEXT);
        $histStmt->bindValue(4, $rotation_id, SQLITE3_TEXT);
        $histStmt->bindValue(5, microtime(true), SQLITE3_FLOAT);
        $histStmt->execute();
    }
    
    /**
     * Get rotation proposal details.
     */
    public function getRotation(string $rotation_id): ?array {
        $stmt = $this->db->prepare("SELECT * FROM key_rotations WHERE rotation_id = ?");
        $stmt->bindValue(1, $rotation_id, SQLITE3_TEXT);
        $res = $stmt->execute();
        return $res->fetchArray(SQLITE3_ASSOC) ?: null;
    }
    
    /**
     * Get signatures for a rotation.
     */
    public function getSignatures(string $rotation_id): array {
        $stmt = $this->db->prepare("
            SELECT * FROM rotation_signatures WHERE rotation_id = ? ORDER BY signed_at ASC
        ");
        $stmt->bindValue(1, $rotation_id, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $sigs = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $sigs[] = $row;
        }
        return $sigs;
    }
    
    private function getSignatureCount(string $rotation_id): int {
        $stmt = $this->db->prepare("
            SELECT COUNT(*) as count FROM rotation_signatures WHERE rotation_id = ?
        ");
        $stmt->bindValue(1, $rotation_id, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        return $row['count'] ?? 0;
    }
    
    /**
     * Get key history for an identity (audit trail).
     */
    public function getKeyHistory(string $identity_key): array {
        $stmt = $this->db->prepare("
            SELECT * FROM key_history WHERE identity_key = ? ORDER BY rotated_at DESC
        ");
        $stmt->bindValue(1, $identity_key, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $history = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $history[] = $row;
        }
        return $history;
    }
    
    /**
     * Get current active key for an identity.
     */
    public function getCurrentKey(string $identity_key): string {
        $history = $this->getKeyHistory($identity_key);
        if (empty($history)) {
            return $identity_key; // No rotation history - original key
        }
        return $history[0]['new_key']; // Most recent
    }
    
    /**
     * Verify if a key is valid (current or historically valid).
     */
    public function isValidKey(string $identity_key, string $check_key): bool {
        $current = $this->getCurrentKey($identity_key);
        if ($current === $check_key) return true;
        
        // Check historical keys
        $history = $this->getKeyHistory($identity_key);
        foreach ($history as $h) {
            if ($h['old_key'] === $check_key || $h['new_key'] === $check_key) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Get pending rotations awaiting signatures.
     */
    public function getPendingRotations(): array {
        $stmt = $this->db->prepare("
            SELECT * FROM key_rotations WHERE status = 'pending' ORDER BY initiated_at DESC
        ");
        
        $res = $stmt->execute();
        $pending = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $row['signatures'] = $this->getSignatures($row['rotation_id']);
            $row['signatures_count'] = count($row['signatures']);
            $pending[] = $row;
        }
        return $pending;
    }
}

/**
 * Threshold signature helpers (simplified - full implementation needs crypto lib).
 */
class ThresholdSignature {
    /**
     * Generate a signature share for rotation proposal.
     * In production: use actual threshold signature scheme (BLS, Schnorr, etc).
     */
    public static function generateShare(string $rotation_id, string $private_key): string {
        // Simplified: just sign the rotation_id
        // Real implementation: use libsodium or crypto lib for proper threshold sigs
        return hash_hmac('sha256', $rotation_id, $private_key);
    }
    
    /**
     * Verify a signature share.
     */
    public static function verifyShare(string $rotation_id, string $public_key, string $signature): bool {
        // Simplified verification
        // Real implementation: proper threshold signature verification
        return strlen($signature) === 64; // Basic sanity check
    }
    
    /**
     * Combine shares into final signature (once threshold reached).
     * In production: proper threshold signature aggregation.
     */
    public static function combineShares(array $shares): string {
        // Simplified: concatenate hashes
        // Real implementation: cryptographic aggregation
        return hash('sha256', implode('', $shares));
    }
}
