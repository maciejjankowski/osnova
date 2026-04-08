<?php
/**
 * Canary System Integration
 * Main orchestrator for whistleblower canary operations
 */

require_once __DIR__ . '/canary_crypto.php';
require_once __DIR__ . '/canary_api.php';
require_once __DIR__ . '/stego_channels.php';

class CanarySystem {
    private CanaryAPI $api;
    private ChannelManager $channels;
    private SQLite3 $db;
    private string $nodeKey;
    
    public function __construct(string $dbPath, string $nodeKey) {
        $this->db = new SQLite3($dbPath);
        $this->db->enableExceptions(true);
        $this->nodeKey = $nodeKey;
        
        $this->api = new CanaryAPI($dbPath, $nodeKey);
        $this->channels = new ChannelManager();
        
        $this->initializeSchema();
    }
    
    /**
     * Initialize database schema.
     */
    private function initializeSchema(): void {
        $schemaFile = __DIR__ . '/../migrations/001_canary_schema.sql';
        if (file_exists($schemaFile)) {
            $schema = file_get_contents($schemaFile);
            $this->db->exec($schema);
        }
    }
    
    /**
     * Create canary with steganographic distribution.
     */
    public function createCanaryWithStealth(
        string $message,
        array $channelTypes = ['tire_forum', 'fatk_forum'],
        int $deadManThreshold = 259200,
        bool $anonymous = false
    ): array {
        // Create canary via API
        $canary = $this->api->createCanary([
            'message' => $message,
            'dead_man_threshold' => $deadManThreshold,
            'anonymous' => $anonymous
        ]);
        
        // Distribute fragments via steganographic channels
        $distributions = [];
        
        // For demonstration, distribute PARAGRAPH layer across channels
        $fragment = substr($message, 0, 500); // Sample fragment
        
        $channelPosts = $this->channels->distributeFragment($fragment, $channelTypes);
        
        // Store steganographic posts
        foreach ($channelPosts as $post) {
            $stmt = $this->db->prepare("
                INSERT INTO canary_stego_posts (canary_id, fragment_id, channel_type, cover_content, posted_at)
                VALUES (?, 0, ?, ?, ?)
            ");
            $stmt->bindValue(1, $canary['canary_id'], SQLITE3_TEXT);
            $stmt->bindValue(2, $post['channel'], SQLITE3_TEXT);
            $stmt->bindValue(3, $post['cover_content'], SQLITE3_TEXT);
            $stmt->bindValue(4, $post['posted_at'], SQLITE3_FLOAT);
            $stmt->execute();
            
            $distributions[] = $post;
        }
        
        return [
            'canary' => $canary,
            'stego_distributions' => $distributions
        ];
    }
    
    /**
     * Monitor all canaries for trigger conditions.
     */
    public function monitorCanaries(): array {
        $stmt = $this->db->query("
            SELECT * FROM canary_messages WHERE status = 'armed'
        ");
        
        $triggered = [];
        $now = microtime(true);
        
        while ($canary = $stmt->fetchArray(SQLITE3_ASSOC)) {
            $timeSinceHeartbeat = $now - $canary['last_heartbeat'];
            
            if ($timeSinceHeartbeat > $canary['dead_man_threshold']) {
                // Dead man's switch triggered
                $this->triggerCascade($canary['canary_id'], 'dead_man');
                $triggered[] = [
                    'canary_id' => $canary['canary_id'],
                    'trigger_type' => 'dead_man',
                    'time_since_heartbeat' => $timeSinceHeartbeat
                ];
            }
        }
        
        return $triggered;
    }
    
    /**
     * Trigger cascade release.
     */
    private function triggerCascade(string $canaryId, string $triggerType): void {
        // Mark as triggered
        $stmt = $this->db->prepare("
            UPDATE canary_messages SET status = 'triggered', trigger_type = ? WHERE canary_id = ?
        ");
        $stmt->bindValue(1, $triggerType, SQLITE3_TEXT);
        $stmt->bindValue(2, $canaryId, SQLITE3_TEXT);
        $stmt->execute();
        
        // Log trigger event
        $logStmt = $this->db->prepare("
            INSERT INTO canary_triggers (canary_id, trigger_type, detected_at, detected_by, evidence)
            VALUES (?, ?, ?, ?, '{}')
        ");
        $logStmt->bindValue(1, $canaryId, SQLITE3_TEXT);
        $logStmt->bindValue(2, $triggerType, SQLITE3_TEXT);
        $logStmt->bindValue(3, microtime(true), SQLITE3_FLOAT);
        $logStmt->bindValue(4, $this->nodeKey, SQLITE3_TEXT);
        $logStmt->execute();
        
        // TODO: Implement actual cascade (notify rings, initiate reconstruction)
        // This would integrate with existing RingManager and GossipService
    }
    
    /**
     * Get system status.
     */
    public function getSystemStatus(): array {
        $totalCanaries = $this->db->querySingle("SELECT COUNT(*) FROM canary_messages");
        $armedCanaries = $this->db->querySingle("SELECT COUNT(*) FROM canary_messages WHERE status = 'armed'");
        $triggeredCanaries = $this->db->querySingle("SELECT COUNT(*) FROM canary_messages WHERE status = 'triggered'");
        $releasedCanaries = $this->db->querySingle("SELECT COUNT(*) FROM canary_messages WHERE status = 'released'");
        
        return [
            'total_canaries' => $totalCanaries,
            'armed' => $armedCanaries,
            'triggered' => $triggeredCanaries,
            'released' => $releasedCanaries,
            'node_key' => substr($this->nodeKey, 0, 16) . '...'
        ];
    }
}
