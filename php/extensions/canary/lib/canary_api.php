<?php
/**
 * Canary API Module
 * REST endpoints for whistleblower canary operations
 */

require_once __DIR__ . '/canary_crypto.php';

class CanaryAPI {
    private SQLite3 $db;
    private string $nodeKey;
    
    public function __construct(string $dbPath, string $nodeKey) {
        $this->db = new SQLite3($dbPath);
        $this->db->enableExceptions(true);
        $this->nodeKey = $nodeKey;
    }
    
    /**
     * Create new canary message.
     * POST /api/canary/create
     */
    public function createCanary(array $request): array {
        $message = $request['message'] ?? throw new InvalidArgumentException('message required');
        $deadManThreshold = $request['dead_man_threshold'] ?? 259200; // 72 hours
        $anonymous = $request['anonymous'] ?? false;
        
        // Generate canary ID
        $canaryId = bin2hex(random_bytes(16));
        
        // Create PARDES layers
        $layers = $this->generatePardesLayers($message);
        
        // Fragment each layer (Shamir Secret Sharing)
        $thresholds = [
            'seed' => [3, 5],       // 3-of-5 CORE
            'paragraph' => [7, 15],  // 7-of-15 INNER
            'page' => [25, 50],      // 25-of-50 MIDDLE
            'document' => [48, 95]   // 48-of-95 OUTER
        ];
        
        $fragments = [];
        foreach ($layers as $layer => $content) {
            [$k, $n] = $thresholds[$layer];
            $fragments[$layer] = CanaryCrypto::shamirSplit($content, $k, $n);
        }
        
        // Store canary message
        $stmt = $this->db->prepare("
            INSERT INTO canary_messages 
            (canary_id, creator_key, created_at, trigger_type, dead_man_threshold, last_heartbeat, anonymous)
            VALUES (?, ?, ?, 'dead_man', ?, ?, ?)
        ");
        $now = microtime(true);
        $stmt->bindValue(1, $canaryId, SQLITE3_TEXT);
        $stmt->bindValue(2, $anonymous ? 'anonymous' : $this->nodeKey, SQLITE3_TEXT);
        $stmt->bindValue(3, $now, SQLITE3_FLOAT);
        $stmt->bindValue(4, $deadManThreshold, SQLITE3_INTEGER);
        $stmt->bindValue(5, $now, SQLITE3_FLOAT);
        $stmt->bindValue(6, $anonymous ? 1 : 0, SQLITE3_INTEGER);
        $stmt->execute();
        
        return [
            'canary_id' => $canaryId,
            'status' => 'armed',
            'layers' => array_keys($layers),
            'fragments_per_layer' => array_map(fn($f) => count($f), $fragments),
            'dead_man_threshold' => $deadManThreshold
        ];
    }
    
    /**
     * Send heartbeat (keep canary alive).
     * POST /api/canary/heartbeat
     */
    public function sendHeartbeat(string $canaryId, ?string $nonce = null): array {
        $stmt = $this->db->prepare("
            UPDATE canary_messages SET last_heartbeat = ? WHERE canary_id = ?
        ");
        $now = microtime(true);
        $stmt->bindValue(1, $now, SQLITE3_FLOAT);
        $stmt->bindValue(2, $canaryId, SQLITE3_TEXT);
        $stmt->execute();
        
        // Log heartbeat
        $logStmt = $this->db->prepare("
            INSERT INTO canary_heartbeats (canary_id, timestamp, sender_key, nonce)
            VALUES (?, ?, ?, ?)
        ");
        $logStmt->bindValue(1, $canaryId, SQLITE3_TEXT);
        $logStmt->bindValue(2, $now, SQLITE3_FLOAT);
        $logStmt->bindValue(3, $this->nodeKey, SQLITE3_TEXT);
        $logStmt->bindValue(4, $nonce, SQLITE3_TEXT);
        $logStmt->execute();
        
        // Check time remaining
        $canary = $this->getCanary($canaryId);
        $timeRemaining = $canary['dead_man_threshold'] - ($now - $canary['last_heartbeat']);
        
        return [
            'canary_id' => $canaryId,
            'heartbeat_received' => true,
            'time_remaining' => max(0, $timeRemaining),
            'next_heartbeat_by' => $now + $canary['dead_man_threshold']
        ];
    }
    
    /**
     * Trigger voluntary eject.
     * POST /api/canary/eject
     */
    public function ejectCanary(string $canaryId, string $goodbyeMessage, string $signature): array {
        // Verify signature
        $canary = $this->getCanary($canaryId);
        if (!CanaryCrypto::verifySignature($goodbyeMessage, $signature, $canary['creator_key'])) {
            throw new RuntimeException('Invalid signature');
        }
        
        // Mark as triggered
        $stmt = $this->db->prepare("
            UPDATE canary_messages SET status = 'triggered', trigger_type = 'eject' WHERE canary_id = ?
        ");
        $stmt->bindValue(1, $canaryId, SQLITE3_TEXT);
        $stmt->execute();
        
        // Log trigger
        $this->logTrigger($canaryId, 'eject', ['goodbye_message' => $goodbyeMessage]);
        
        return [
            'canary_id' => $canaryId,
            'status' => 'triggered',
            'trigger_type' => 'eject',
            'cascade_initiated' => true
        ];
    }
    
    /**
     * Signal compromise (duress).
     * POST /api/canary/compromise
     */
    public function signalCompromise(string $canaryId, string $duressMessage, string $signature): array {
        // Detect duress markers
        $isDuress = CanaryCrypto::isDuressSignal($duressMessage);
        
        if ($isDuress) {
            // Mark as compromised, trigger release of TRUTH (not duress message)
            $stmt = $this->db->prepare("
                UPDATE canary_messages SET status = 'triggered', trigger_type = 'compromise' WHERE canary_id = ?
            ");
            $stmt->bindValue(1, $canaryId, SQLITE3_TEXT);
            $stmt->execute();
            
            $this->logTrigger($canaryId, 'compromise', [
                'duress_message' => $duressMessage,
                'gematria' => CanaryCrypto::calculateGematria($duressMessage)
            ]);
            
            return [
                'canary_id' => $canaryId,
                'duress_detected' => true,
                'releasing_original_truth' => true,
                'ignoring_duress_message' => true
            ];
        }
        
        return ['duress_detected' => false];
    }
    
    /**
     * Get canary status.
     * GET /api/canary/status/{canary_id}
     */
    public function getCanaryStatus(string $canaryId): array {
        $canary = $this->getCanary($canaryId);
        $now = microtime(true);
        
        $timeRemaining = $canary['dead_man_threshold'] - ($now - $canary['last_heartbeat']);
        $willTriggerAt = $canary['last_heartbeat'] + $canary['dead_man_threshold'];
        
        return [
            'canary_id' => $canary['canary_id'],
            'status' => $canary['status'],
            'trigger_type' => $canary['trigger_type'],
            'created_at' => $canary['created_at'],
            'last_heartbeat' => $canary['last_heartbeat'],
            'time_remaining' => max(0, $timeRemaining),
            'will_trigger_at' => $willTriggerAt,
            'anonymous' => (bool)$canary['anonymous']
        ];
    }
    
    private function getCanary(string $canaryId): array {
        $stmt = $this->db->prepare("SELECT * FROM canary_messages WHERE canary_id = ?");
        $stmt->bindValue(1, $canaryId, SQLITE3_TEXT);
        $res = $stmt->execute();
        $canary = $res->fetchArray(SQLITE3_ASSOC);
        
        if (!$canary) {
            throw new RuntimeException("Canary not found: $canaryId");
        }
        
        return $canary;
    }
    
    private function logTrigger(string $canaryId, string $triggerType, array $evidence): void {
        $stmt = $this->db->prepare("
            INSERT INTO canary_triggers (canary_id, trigger_type, detected_at, detected_by, evidence)
            VALUES (?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $canaryId, SQLITE3_TEXT);
        $stmt->bindValue(2, $triggerType, SQLITE3_TEXT);
        $stmt->bindValue(3, microtime(true), SQLITE3_FLOAT);
        $stmt->bindValue(4, $this->nodeKey, SQLITE3_TEXT);
        $stmt->bindValue(5, json_encode($evidence), SQLITE3_TEXT);
        $stmt->execute();
    }
    
    private function generatePardesLayers(string $message): array {
        // Extract PARDES layers from full message
        $sentences = array_filter(explode('.', $message), fn($s) => trim($s));
        
        return [
            'seed' => $sentences[0] ?? $message,  // First sentence
            'paragraph' => implode('. ', array_slice($sentences, 0, 5)),  // First 5 sentences
            'page' => strlen($message) > 3000 ? substr($message, 0, 3000) : $message,
            'document' => $message  // Full message
        ];
    }
}
