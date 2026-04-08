<?php
/**
 * Bounty system - information requests with path-attributed rewards (Shapley values).
 * Rewards contributors based on their marginal contribution to the answer path.
 */

class Bounty {
    public string $bounty_id;
    public string $requester_key;
    public string $question;
    public int $reward_amount;
    public string $status; // 'open', 'answered', 'closed'
    public float $created_at;
    public float $expires_at;
}

class BountyManager {
    private SQLite3 $db;
    
    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->initialize();
    }
    
    private function initialize(): void {
        // Bounties table
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS bounties (
                bounty_id      TEXT PRIMARY KEY,
                requester_key  TEXT NOT NULL,
                question       TEXT NOT NULL,
                reward_amount  INTEGER NOT NULL,
                status         TEXT NOT NULL DEFAULT 'open',
                created_at     REAL NOT NULL,
                expires_at     REAL NOT NULL
            )
        ");
        
        // Contributions to bounties (information pieces)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS bounty_contributions (
                contribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bounty_id       TEXT NOT NULL,
                contributor_key TEXT NOT NULL,
                content_hash    TEXT NOT NULL,
                timestamp       REAL NOT NULL
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_contributions_bounty ON bounty_contributions (bounty_id)");
        
        // Answer paths (which contributions led to the answer)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS answer_paths (
                path_id         INTEGER PRIMARY KEY AUTOINCREMENT,
                bounty_id       TEXT NOT NULL,
                contribution_ids TEXT NOT NULL,
                accepted_at     REAL NOT NULL
            )
        ");
        
        // Reward distributions (Shapley value calculations)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS reward_distributions (
                distribution_id INTEGER PRIMARY KEY AUTOINCREMENT,
                bounty_id       TEXT NOT NULL,
                contributor_key TEXT NOT NULL,
                shapley_value   REAL NOT NULL,
                reward_share    INTEGER NOT NULL,
                distributed_at  REAL NOT NULL
            )
        ");
    }
    
    /**
     * Create a bounty (information request).
     */
    public function createBounty(string $requester_key, string $question, int $reward_amount, int $duration_seconds = 604800): string {
        $bounty_id = bin2hex(random_bytes(16));
        $now = microtime(true);
        $expires_at = $now + $duration_seconds;
        
        $stmt = $this->db->prepare("
            INSERT INTO bounties (bounty_id, requester_key, question, reward_amount, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $requester_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $question, SQLITE3_TEXT);
        $stmt->bindValue(4, $reward_amount, SQLITE3_INTEGER);
        $stmt->bindValue(5, $now, SQLITE3_FLOAT);
        $stmt->bindValue(6, $expires_at, SQLITE3_FLOAT);
        $stmt->execute();
        
        return $bounty_id;
    }
    
    /**
     * Contribute information to a bounty (link existing content).
     */
    public function contribute(string $bounty_id, string $contributor_key, string $content_hash): int {
        $stmt = $this->db->prepare("
            INSERT INTO bounty_contributions (bounty_id, contributor_key, content_hash, timestamp)
            VALUES (?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $contributor_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $content_hash, SQLITE3_TEXT);
        $stmt->bindValue(4, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        
        return $this->db->lastInsertRowID();
    }
    
    /**
     * Accept answer and mark path (which contributions were useful).
     */
    public function acceptAnswer(string $bounty_id, array $contribution_ids): bool {
        // Mark bounty as answered
        $stmt = $this->db->prepare("
            UPDATE bounties SET status = 'answered' WHERE bounty_id = ?
        ");
        $stmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $stmt->execute();
        
        // Record answer path
        $pathStmt = $this->db->prepare("
            INSERT INTO answer_paths (bounty_id, contribution_ids, accepted_at)
            VALUES (?, ?, ?)
        ");
        $pathStmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $pathStmt->bindValue(2, json_encode($contribution_ids), SQLITE3_TEXT);
        $pathStmt->bindValue(3, microtime(true), SQLITE3_FLOAT);
        $pathStmt->execute();
        
        // Calculate and distribute rewards
        return $this->distributeRewards($bounty_id, $contribution_ids);
    }
    
    /**
     * Calculate Shapley values for contributors.
     * Shapley value = average marginal contribution across all orderings.
     * 
     * For simplicity: equal split among path contributors (true Shapley requires exponential calc).
     * For production: implement proper Shapley value computation.
     */
    private function distributeRewards(string $bounty_id, array $contribution_ids): bool {
        // Get bounty reward
        $bountyStmt = $this->db->prepare("
            SELECT reward_amount FROM bounties WHERE bounty_id = ?
        ");
        $bountyStmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $res = $bountyStmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        if (!$row) return false;
        
        $total_reward = $row['reward_amount'];
        
        // Get contributors
        $contributors = [];
        foreach ($contribution_ids as $cid) {
            $stmt = $this->db->prepare("
                SELECT contributor_key FROM bounty_contributions WHERE contribution_id = ?
            ");
            $stmt->bindValue(1, $cid, SQLITE3_INTEGER);
            $res = $stmt->execute();
            $row = $res->fetchArray(SQLITE3_ASSOC);
            if ($row) {
                $contributors[$row['contributor_key']] = ($contributors[$row['contributor_key']] ?? 0) + 1;
            }
        }
        
        if (empty($contributors)) return false;
        
        // Simplified Shapley: equal split (proper implementation would weight by marginal contribution)
        $num_contributors = count($contributors);
        $shapley_value = 1.0 / $num_contributors;
        $reward_per_contributor = floor($total_reward / $num_contributors);
        
        // Record distributions
        foreach ($contributors as $key => $contribution_count) {
            $distStmt = $this->db->prepare("
                INSERT INTO reward_distributions (bounty_id, contributor_key, shapley_value, reward_share, distributed_at)
                VALUES (?, ?, ?, ?, ?)
            ");
            $distStmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
            $distStmt->bindValue(2, $key, SQLITE3_TEXT);
            $distStmt->bindValue(3, $shapley_value, SQLITE3_FLOAT);
            $distStmt->bindValue(4, $reward_per_contributor, SQLITE3_INTEGER);
            $distStmt->bindValue(5, microtime(true), SQLITE3_FLOAT);
            $distStmt->execute();
        }
        
        return true;
    }
    
    /**
     * Get bounty details with contributions.
     */
    public function getBounty(string $bounty_id): ?array {
        $stmt = $this->db->prepare("SELECT * FROM bounties WHERE bounty_id = ?");
        $stmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $res = $stmt->execute();
        $bounty = $res->fetchArray(SQLITE3_ASSOC);
        
        if (!$bounty) return null;
        
        // Get contributions
        $contribStmt = $this->db->prepare("
            SELECT * FROM bounty_contributions WHERE bounty_id = ? ORDER BY timestamp ASC
        ");
        $contribStmt->bindValue(1, $bounty_id, SQLITE3_TEXT);
        $contribRes = $contribStmt->execute();
        
        $contributions = [];
        while ($row = $contribRes->fetchArray(SQLITE3_ASSOC)) {
            $contributions[] = $row;
        }
        
        $bounty['contributions'] = $contributions;
        return $bounty;
    }
    
    /**
     * Get active bounties.
     */
    public function getActiveBounties(int $limit = 50): array {
        $now = microtime(true);
        $stmt = $this->db->prepare("
            SELECT * FROM bounties WHERE status = 'open' AND expires_at > ? ORDER BY reward_amount DESC LIMIT ?
        ");
        $stmt->bindValue(1, $now, SQLITE3_FLOAT);
        $stmt->bindValue(2, $limit, SQLITE3_INTEGER);
        
        $res = $stmt->execute();
        $bounties = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $bounties[] = $row;
        }
        return $bounties;
    }
    
    /**
     * Get rewards earned by a contributor.
     */
    public function getContributorRewards(string $contributor_key): array {
        $stmt = $this->db->prepare("
            SELECT * FROM reward_distributions WHERE contributor_key = ? ORDER BY distributed_at DESC
        ");
        $stmt->bindValue(1, $contributor_key, SQLITE3_TEXT);
        
        $res = $stmt->execute();
        $rewards = [];
        $total = 0;
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $rewards[] = $row;
            $total += $row['reward_share'];
        }
        
        return [
            'total_earned' => $total,
            'distributions' => $rewards,
        ];
    }
}
