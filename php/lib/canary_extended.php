<?php
/**
 * Canary System - Extended for Whistleblower Haven
 * Dead man's switch, heartbeat monitoring, cascade release
 * Based on SPEC.md Section: WHISTLEBLOWER CANARY SYSTEM
 */

class CanarySystemExtended {
    private PDO $db;
    private string $node_key;
    
    public function __construct(string $db_path, string $node_key) {
        $this->db = new PDO('sqlite:' . $db_path);
        $this->db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $this->node_key = $node_key;
        $this->initSchema();
    }
    
    private function initSchema(): void {
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS canaries (
                canary_id TEXT PRIMARY KEY,
                author_key TEXT NOT NULL,
                message_encrypted TEXT NOT NULL,
                heartbeat_interval INTEGER DEFAULT 86400,
                last_heartbeat REAL,
                missed_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                compromised_signal TEXT,
                alternative_message TEXT,
                created_at REAL NOT NULL
            )
        ");
        
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS fragments (
                fragment_id TEXT PRIMARY KEY,
                canary_id TEXT NOT NULL,
                fragment_data TEXT NOT NULL,
                ring_level INTEGER NOT NULL,
                storage_type TEXT DEFAULT 'gig',
                storage_id TEXT,
                created_at REAL NOT NULL,
                FOREIGN KEY(canary_id) REFERENCES canaries(canary_id)
            )
        ");
        
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS heartbeats (
                heartbeat_id TEXT PRIMARY KEY,
                canary_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                method TEXT,
                FOREIGN KEY(canary_id) REFERENCES canaries(canary_id)
            )
        ");
        
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_canaries_status ON canaries(status)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_fragments_canary ON fragments(canary_id)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_heartbeats_canary ON heartbeats(canary_id, timestamp DESC)");
    }
    
    // Create new canary with message fragmentation
    public function createCanary(array $data): array {
        $canary_id = bin2hex(random_bytes(16));
        $message = $data['message'];
        $heartbeat_interval = $data['heartbeat_interval'] ?? 86400; // 24h default
        
        // Fragment the message using Reed-Solomon-like distribution
        $fragments = $this->fragmentMessage($message, $data['fragment_count'] ?? 100);
        
        // Store canary
        $stmt = $this->db->prepare("
            INSERT INTO canaries (
                canary_id, author_key, message_encrypted, heartbeat_interval,
                last_heartbeat, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ");
        
        $now = microtime(true);
        $stmt->execute([
            $canary_id,
            $data['author_key'],
            $data['encrypted_message'] ?? $message,
            $heartbeat_interval,
            $now,
            'active',
            $now
        ]);
        
        // Store fragments with ring distribution
        $this->distributeFragments($canary_id, $fragments);
        
        return [
            'canary_id' => $canary_id,
            'fragments' => count($fragments),
            'heartbeat_interval' => $heartbeat_interval,
            'next_heartbeat' => $now + $heartbeat_interval
        ];
    }
    
    // Fragment message for distributed storage
    private function fragmentMessage(string $message, int $count): array {
        $fragments = [];
        $chunk_size = (int)ceil(strlen($message) / $count * 1.6); // 60% redundancy
        
        for ($i = 0; $i < $count; $i++) {
            $offset = (int)floor($i * strlen($message) / $count);
            $chunk = substr($message, $offset, $chunk_size);
            
            $fragments[] = [
                'fragment_id' => bin2hex(random_bytes(8)),
                'sequence' => $i,
                'data' => base64_encode($chunk),
                'checksum' => hash('sha256', $chunk)
            ];
        }
        
        return $fragments;
    }
    
    // Distribute fragments across rings
    private function distributeFragments(string $canary_id, array $fragments): void {
        $ring_distribution = [
            0 => 0.30, // Ring 0: 30% of fragments
            1 => 0.40, // Ring 1: 40%
            2 => 0.30, // Ring 2: 30%
            3 => 0.20, // Ring 3: 20% (overlap intentional)
        ];
        
        $stmt = $this->db->prepare("
            INSERT INTO fragments (
                fragment_id, canary_id, fragment_data, ring_level,
                storage_type, created_at
            ) VALUES (?, ?, ?, ?, ?, ?)
        ");
        
        $total = count($fragments);
        $ring_index = 0;
        $cumulative = 0;
        
        foreach ($fragments as $i => $frag) {
            // Determine ring based on distribution
            $progress = $i / $total;
            foreach ($ring_distribution as $ring => $ratio) {
                $cumulative += $ratio;
                if ($progress < $cumulative) {
                    $ring_index = $ring;
                    break;
                }
            }
            
            $stmt->execute([
                $frag['fragment_id'],
                $canary_id,
                json_encode($frag),
                $ring_index,
                'direct', // Storage type: direct, gig, profile, spam
                microtime(true)
            ]);
        }
    }
    
    // Record heartbeat
    public function heartbeat(string $canary_id, string $method = 'manual'): bool {
        // Update last heartbeat
        $stmt = $this->db->prepare("
            UPDATE canaries 
            SET last_heartbeat = ?, missed_count = 0
            WHERE canary_id = ? AND status = 'active'
        ");
        
        $now = microtime(true);
        $stmt->execute([$now, $canary_id]);
        
        if ($stmt->rowCount() === 0) {
            return false;
        }
        
        // Log heartbeat
        $stmt = $this->db->prepare("
            INSERT INTO heartbeats (heartbeat_id, canary_id, timestamp, method)
            VALUES (?, ?, ?, ?)
        ");
        
        $stmt->execute([
            bin2hex(random_bytes(8)),
            $canary_id,
            $now,
            $method
        ]);
        
        return true;
    }
    
    // Check for missed heartbeats and trigger cascade if needed
    public function checkMissedHeartbeats(): array {
        $triggered = [];
        
        $stmt = $this->db->prepare("
            SELECT * FROM canaries 
            WHERE status = 'active'
        ");
        
        $stmt->execute();
        $canaries = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        $now = microtime(true);
        
        foreach ($canaries as $canary) {
            $elapsed = $now - $canary['last_heartbeat'];
            $expected = $canary['heartbeat_interval'];
            
            if ($elapsed > $expected) {
                $missed = (int)floor($elapsed / $expected);
                
                // Update missed count
                $update = $this->db->prepare("
                    UPDATE canaries 
                    SET missed_count = ? 
                    WHERE canary_id = ?
                ");
                $update->execute([$missed, $canary['canary_id']]);
                
                // Trigger cascade at different thresholds
                if ($missed >= 3) { // 72h default
                    $this->triggerCascade($canary['canary_id'], 'missed_heartbeat');
                    $triggered[] = $canary['canary_id'];
                }
            }
        }
        
        return $triggered;
    }
    
    // Signal compromised status
    public function signalCompromised(string $canary_id, string $signal): bool {
        $stmt = $this->db->prepare("
            UPDATE canaries 
            SET compromised_signal = ?,
                status = 'compromised'
            WHERE canary_id = ? AND status = 'active'
        ");
        
        $stmt->execute([$signal, $canary_id]);
        
        if ($stmt->rowCount() > 0) {
            // Immediate cascade on compromised signal
            $this->triggerCascade($canary_id, 'compromised');
            return true;
        }
        
        return false;
    }
    
    // Trigger cascade release
    private function triggerCascade(string $canary_id, string $reason): void {
        // Mark canary as triggered
        $stmt = $this->db->prepare("
            UPDATE canaries 
            SET status = 'triggered'
            WHERE canary_id = ?
        ");
        $stmt->execute([$canary_id]);
        
        // Get all fragments
        $stmt = $this->db->prepare("
            SELECT * FROM fragments 
            WHERE canary_id = ?
            ORDER BY ring_level, fragment_id
        ");
        $stmt->execute([$canary_id]);
        $fragments = $stmt->fetchAll(PDO::FETCH_ASSOC);
        
        // Initiate cascade: fragments become available for reconstruction
        // This would propagate through gossip protocol to all ring members
        // For now, we mark them as 'released'
        foreach ($fragments as $frag) {
            // Log cascade event (would trigger gossip in real implementation)
            error_log("CANARY CASCADE: {$canary_id} fragment {$frag['fragment_id']} released (reason: {$reason})");
        }
    }
    
    // Reconstruct message from available fragments
    public function reconstructMessage(string $canary_id): ?array {
        $stmt = $this->db->prepare("
            SELECT fragment_data FROM fragments 
            WHERE canary_id = ?
            ORDER BY fragment_id
        ");
        
        $stmt->execute([$canary_id]);
        $fragments = $stmt->fetchAll(PDO::FETCH_COLUMN);
        
        if (count($fragments) < 60) { // Need at least 60% for Reed-Solomon
            return [
                'status' => 'incomplete',
                'available' => count($fragments),
                'required' => 60
            ];
        }
        
        // Reconstruct (simplified - real implementation would use Reed-Solomon)
        $reconstructed = '';
        foreach ($fragments as $frag_json) {
            $frag = json_decode($frag_json, true);
            $reconstructed .= base64_decode($frag['data']);
        }
        
        return [
            'status' => 'complete',
            'message' => $reconstructed,
            'fragments_used' => count($fragments)
        ];
    }
    
    // Get canary status
    public function getStatus(string $canary_id): ?array {
        $stmt = $this->db->prepare("SELECT * FROM canaries WHERE canary_id = ?");
        $stmt->execute([$canary_id]);
        
        $canary = $stmt->fetch(PDO::FETCH_ASSOC);
        if (!$canary) {
            return null;
        }
        
        // Get fragment count
        $stmt = $this->db->prepare("SELECT COUNT(*) FROM fragments WHERE canary_id = ?");
        $stmt->execute([$canary_id]);
        $canary['fragment_count'] = $stmt->fetchColumn();
        
        // Get last heartbeat info
        $stmt = $this->db->prepare("
            SELECT * FROM heartbeats 
            WHERE canary_id = ? 
            ORDER BY timestamp DESC 
            LIMIT 1
        ");
        $stmt->execute([$canary_id]);
        $canary['last_heartbeat_info'] = $stmt->fetch(PDO::FETCH_ASSOC);
        
        return $canary;
    }
}
