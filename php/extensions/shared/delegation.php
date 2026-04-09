<?php
/**
 * Liquid delegation system - delegative voting within trust rings.
 * Delegate your vote to a trusted peer, who can further delegate (transitive).
 */

class DelegationManager {
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
        // Delegations table
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS delegations (
                delegation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                delegator_key TEXT NOT NULL,
                delegate_key  TEXT NOT NULL,
                scope         TEXT NOT NULL DEFAULT 'all',
                created_at    REAL NOT NULL,
                revoked_at    REAL DEFAULT NULL,
                UNIQUE(delegator_key, scope)
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_delegations_delegator ON delegations (delegator_key)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_delegations_delegate ON delegations (delegate_key)");
    }
    
    /**
     * Delegate voting power to another peer.
     * Scope can be 'all', 'poll:{poll_id}', or 'topic:{topic}'.
     */
    public function delegate(string $delegator_key, string $delegate_key, string $scope = 'all'): bool {
        // Validate: can't delegate to self
        if ($delegator_key === $delegate_key) return false;
        
        // Validate: delegate must be in ring
        $peer = $this->rings->getPeer($delegate_key);
        if (!$peer) return false;
        
        // Check for delegation cycles
        if ($this->wouldCreateCycle($delegator_key, $delegate_key, $scope)) {
            return false;
        }
        
        // Revoke existing delegation for this scope
        $this->revokeDelegation($delegator_key, $scope);
        
        // Create new delegation
        $stmt = $this->db->prepare("
            INSERT INTO delegations (delegator_key, delegate_key, scope, created_at)
            VALUES (?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $delegator_key, SQLITE3_TEXT);
        $stmt->bindValue(2, $delegate_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $scope, SQLITE3_TEXT);
        $stmt->bindValue(4, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        
        return true;
    }
    
    /**
     * Revoke a delegation.
     */
    public function revokeDelegation(string $delegator_key, string $scope = 'all'): void {
        $stmt = $this->db->prepare("
            UPDATE delegations SET revoked_at = ? WHERE delegator_key = ? AND scope = ? AND revoked_at IS NULL
        ");
        $stmt->bindValue(1, microtime(true), SQLITE3_FLOAT);
        $stmt->bindValue(2, $delegator_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $scope, SQLITE3_TEXT);
        $stmt->execute();
    }
    
    /**
     * Get effective delegate for a voter in a scope (follows transitive delegations).
     * Returns final delegate key or null if no delegation.
     */
    public function getEffectiveDelegate(string $voter_key, string $scope = 'all', int $max_depth = 10): ?string {
        $visited = [];
        $current = $voter_key;
        $depth = 0;
        
        while ($depth < $max_depth) {
            if (in_array($current, $visited)) {
                // Cycle detected - break
                return null;
            }
            $visited[] = $current;
            
            // Find active delegation
            $stmt = $this->db->prepare("
                SELECT delegate_key FROM delegations 
                WHERE delegator_key = ? AND (scope = ? OR scope = 'all') AND revoked_at IS NULL
                ORDER BY scope DESC, created_at DESC LIMIT 1
            ");
            $stmt->bindValue(1, $current, SQLITE3_TEXT);
            $stmt->bindValue(2, $scope, SQLITE3_TEXT);
            $res = $stmt->execute();
            $row = $res->fetchArray(SQLITE3_ASSOC);
            
            if (!$row) {
                // No further delegation - this is the final delegate
                return $current === $voter_key ? null : $current;
            }
            
            $current = $row['delegate_key'];
            $depth++;
        }
        
        // Max depth reached - return current
        return $current === $voter_key ? null : $current;
    }
    
    /**
     * Get vote weight for a delegate (how many people delegated to them).
     */
    public function getDelegateWeight(string $delegate_key, string $scope = 'all'): int {
        $delegators = $this->getDelegators($delegate_key, $scope);
        return count($delegators) + 1; // +1 for delegate's own vote
    }
    
    /**
     * Get all direct delegators for a delegate.
     */
    public function getDelegators(string $delegate_key, string $scope = 'all'): array {
        $stmt = $this->db->prepare("
            SELECT delegator_key FROM delegations 
            WHERE delegate_key = ? AND (scope = ? OR scope = 'all') AND revoked_at IS NULL
        ");
        $stmt->bindValue(1, $delegate_key, SQLITE3_TEXT);
        $stmt->bindValue(2, $scope, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $delegators = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $delegators[] = $row['delegator_key'];
        }
        return $delegators;
    }
    
    /**
     * Check if delegation would create a cycle.
     */
    private function wouldCreateCycle(string $delegator_key, string $delegate_key, string $scope): bool {
        // Walk delegation chain from delegate_key - if we find delegator_key, it's a cycle
        $effective = $this->getEffectiveDelegate($delegate_key, $scope);
        
        // Check transitive chain
        $current = $delegate_key;
        $visited = [];
        $max_depth = 10;
        
        while ($max_depth-- > 0) {
            if ($current === $delegator_key) return true;
            if (in_array($current, $visited)) return false;
            $visited[] = $current;
            
            $stmt = $this->db->prepare("
                SELECT delegate_key FROM delegations 
                WHERE delegator_key = ? AND (scope = ? OR scope = 'all') AND revoked_at IS NULL
                ORDER BY scope DESC LIMIT 1
            ");
            $stmt->bindValue(1, $current, SQLITE3_TEXT);
            $stmt->bindValue(2, $scope, SQLITE3_TEXT);
            $res = $stmt->execute();
            $row = $res->fetchArray(SQLITE3_ASSOC);
            
            if (!$row) return false;
            $current = $row['delegate_key'];
        }
        
        return false;
    }
    
    /**
     * Get delegation chain for a voter (for transparency).
     */
    public function getDelegationChain(string $voter_key, string $scope = 'all'): array {
        $chain = [$voter_key];
        $current = $voter_key;
        $max_depth = 10;
        
        while ($max_depth-- > 0) {
            $stmt = $this->db->prepare("
                SELECT delegate_key FROM delegations 
                WHERE delegator_key = ? AND (scope = ? OR scope = 'all') AND revoked_at IS NULL
                ORDER BY scope DESC LIMIT 1
            ");
            $stmt->bindValue(1, $current, SQLITE3_TEXT);
            $stmt->bindValue(2, $scope, SQLITE3_TEXT);
            $res = $stmt->execute();
            $row = $res->fetchArray(SQLITE3_ASSOC);
            
            if (!$row) break;
            
            $current = $row['delegate_key'];
            if (in_array($current, $chain)) break; // Cycle
            $chain[] = $current;
        }
        
        return $chain;
    }
}
