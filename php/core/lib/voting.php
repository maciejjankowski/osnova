<?php
/**
 * Polls and Quadratic Voting system - per-ring democratic tools.
 * Quadratic voting: cost = votes^2 (prevents majority tyranny).
 */

class Poll {
    public string $poll_id;
    public string $creator_key;
    public string $question;
    public array $options;
    public string $voting_type; // 'simple' or 'quadratic'
    public string $ring_level;  // Who can vote: 'core', 'inner', 'middle', 'outer'
    public float $created_at;
    public float $expires_at;
    public bool $closed;
}

class VotingManager {
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
        // Polls table
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS polls (
                poll_id      TEXT PRIMARY KEY,
                creator_key  TEXT NOT NULL,
                question     TEXT NOT NULL,
                options      TEXT NOT NULL,
                voting_type  TEXT NOT NULL DEFAULT 'simple',
                ring_level   TEXT NOT NULL DEFAULT 'inner',
                created_at   REAL NOT NULL,
                expires_at   REAL NOT NULL,
                closed       INTEGER NOT NULL DEFAULT 0
            )
        ");
        
        // Votes table
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS votes (
                vote_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                poll_id     TEXT NOT NULL,
                voter_key   TEXT NOT NULL,
                option_id   INTEGER NOT NULL,
                vote_weight REAL NOT NULL DEFAULT 1.0,
                timestamp   REAL NOT NULL,
                UNIQUE(poll_id, voter_key, option_id)
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_votes_poll ON votes (poll_id)");
        
        // Quadratic voting credits (per voter, per poll)
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS qv_credits (
                poll_id        TEXT NOT NULL,
                voter_key      TEXT NOT NULL,
                total_credits  INTEGER NOT NULL DEFAULT 100,
                credits_spent  INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (poll_id, voter_key)
            )
        ");
    }
    
    /**
     * Create a poll.
     */
    public function createPoll(string $creator_key, string $question, array $options, string $voting_type = 'simple', string $ring_level = 'inner', int $duration_seconds = 604800): string {
        $poll_id = bin2hex(random_bytes(16));
        $now = microtime(true);
        $expires_at = $now + $duration_seconds;
        
        $stmt = $this->db->prepare("
            INSERT INTO polls (poll_id, creator_key, question, options, voting_type, ring_level, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $creator_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $question, SQLITE3_TEXT);
        $stmt->bindValue(4, json_encode($options), SQLITE3_TEXT);
        $stmt->bindValue(5, $voting_type, SQLITE3_TEXT);
        $stmt->bindValue(6, $ring_level, SQLITE3_TEXT);
        $stmt->bindValue(7, $now, SQLITE3_FLOAT);
        $stmt->bindValue(8, $expires_at, SQLITE3_FLOAT);
        $stmt->execute();
        
        return $poll_id;
    }
    
    /**
     * Cast a vote (simple or quadratic).
     */
    public function vote(string $poll_id, string $voter_key, int $option_id, int $vote_count = 1): bool {
        $poll = $this->getPoll($poll_id);
        if (!$poll || $poll['closed'] || microtime(true) > $poll['expires_at']) {
            return false; // Poll closed or expired
        }
        
        // Check voter eligibility (ring level)
        $peer = $this->rings->getPeer($voter_key);
        if (!$peer || !$this->isEligible($peer['ring_level'], $poll['ring_level'])) {
            return false; // Not in eligible ring
        }
        
        if ($poll['voting_type'] === 'quadratic') {
            return $this->voteQuadratic($poll_id, $voter_key, $option_id, $vote_count);
        } else {
            return $this->voteSimple($poll_id, $voter_key, $option_id);
        }
    }
    
    private function voteSimple(string $poll_id, string $voter_key, int $option_id): bool {
        // One vote per option, can vote multiple options
        $stmt = $this->db->prepare("
            INSERT OR REPLACE INTO votes (poll_id, voter_key, option_id, vote_weight, timestamp)
            VALUES (?, ?, ?, 1.0, ?)
        ");
        $stmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $voter_key, SQLITE3_TEXT);
        $stmt->bindValue(3, $option_id, SQLITE3_INTEGER);
        $stmt->bindValue(4, microtime(true), SQLITE3_FLOAT);
        $stmt->execute();
        return true;
    }
    
    private function voteQuadratic(string $poll_id, string $voter_key, int $option_id, int $vote_count): bool {
        // Quadratic cost: cost = votes^2
        $cost = $vote_count * $vote_count;
        
        // Initialize credits if first vote
        $this->db->exec("
            INSERT OR IGNORE INTO qv_credits (poll_id, voter_key, total_credits, credits_spent)
            VALUES ('$poll_id', '$voter_key', 100, 0)
        ");
        
        // Check available credits
        $stmt = $this->db->prepare("
            SELECT total_credits, credits_spent FROM qv_credits WHERE poll_id = ? AND voter_key = ?
        ");
        $stmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $stmt->bindValue(2, $voter_key, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        
        if (!$row) return false;
        
        $available = $row['total_credits'] - $row['credits_spent'];
        if ($available < $cost) return false; // Not enough credits
        
        // Record vote
        $voteStmt = $this->db->prepare("
            INSERT OR REPLACE INTO votes (poll_id, voter_key, option_id, vote_weight, timestamp)
            VALUES (?, ?, ?, ?, ?)
        ");
        $voteStmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $voteStmt->bindValue(2, $voter_key, SQLITE3_TEXT);
        $voteStmt->bindValue(3, $option_id, SQLITE3_INTEGER);
        $voteStmt->bindValue(4, (float)$vote_count, SQLITE3_FLOAT);
        $voteStmt->bindValue(5, microtime(true), SQLITE3_FLOAT);
        $voteStmt->execute();
        
        // Deduct credits
        $updateStmt = $this->db->prepare("
            UPDATE qv_credits SET credits_spent = credits_spent + ? WHERE poll_id = ? AND voter_key = ?
        ");
        $updateStmt->bindValue(1, $cost, SQLITE3_INTEGER);
        $updateStmt->bindValue(2, $poll_id, SQLITE3_TEXT);
        $updateStmt->bindValue(3, $voter_key, SQLITE3_TEXT);
        $updateStmt->execute();
        
        return true;
    }
    
    /**
     * Get poll results.
     */
    public function getResults(string $poll_id): array {
        $poll = $this->getPoll($poll_id);
        if (!$poll) return [];
        
        $options = json_decode($poll['options'], true);
        $results = array_fill(0, count($options), 0);
        
        $stmt = $this->db->prepare("
            SELECT option_id, SUM(vote_weight) as total FROM votes WHERE poll_id = ? GROUP BY option_id
        ");
        $stmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $res = $stmt->execute();
        
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $results[$row['option_id']] = (float)$row['total'];
        }
        
        return [
            'poll' => $poll,
            'options' => $options,
            'results' => $results,
            'total_voters' => $this->getVoterCount($poll_id),
        ];
    }
    
    private function getPoll(string $poll_id): ?array {
        $stmt = $this->db->prepare("SELECT * FROM polls WHERE poll_id = ?");
        $stmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $res = $stmt->execute();
        return $res->fetchArray(SQLITE3_ASSOC) ?: null;
    }
    
    private function getVoterCount(string $poll_id): int {
        $stmt = $this->db->prepare("SELECT COUNT(DISTINCT voter_key) as count FROM votes WHERE poll_id = ?");
        $stmt->bindValue(1, $poll_id, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        return $row['count'] ?? 0;
    }
    
    private function isEligible(string $voter_ring, string $required_ring): bool {
        $hierarchy = ['core' => 4, 'inner' => 3, 'middle' => 2, 'outer' => 1];
        return ($hierarchy[$voter_ring] ?? 0) >= ($hierarchy[$required_ring] ?? 0);
    }
}
