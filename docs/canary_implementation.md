# Whistleblower Canary - Top-Down Implementation Plan
## From Architecture to Code

**Date:** 2026-04-08  
**Architect:** Oracle  
**Principle:** Suppression-proof by design

---

## LAYER 1: ARCHITECTURAL DESIGN

### 1.1 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    CANARY SYSTEM                             │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Message    │  │  Fragment    │  │  Trigger     │     │
│  │  Preparation │→│ Distribution │→│  Detection   │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         ↓                  ↓                  ↓             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   PARDES     │  │   Shamir     │  │  Heartbeat   │     │
│  │   Layering   │  │   Sharing    │  │  Monitor     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│         ↓                  ↓                  ↓             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ Encryption   │  │  Ring-based  │  │  Cascade     │     │
│  │ per Layer    │  │  Routing     │  │  Release     │     │
│  └──────────────┘  └──────────────┘  └──────────────┘     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Data Flow

```
PREPARATION PHASE:
  Whistleblower → Message Creation → PARDES Layering → Fragmentation
                                          ↓
  SEED (1 sentence) ─────────────→ CORE ring (encrypted)
  PARAGRAPH (3-5) ───────────────→ INNER ring (7-of-15 threshold)
  PAGE (full doc) ───────────────→ MIDDLE ring (25-of-50 threshold)
  DOCUMENT (evidence) ───────────→ OUTER ring (48-of-95 threshold)

TRIGGER PHASE:
  Condition Met → Detection → Verification → Cascade Initiation
                     ↓
  Dead Man's Switch │ Eject Signal │ Compromise Detected │ Network Silence
                     ↓
  Adjacent rings notified → Time-locks activated → Cross-network alert

RECONSTRUCTION PHASE:
  Fragments Collected → Threshold Reached → Decryption → Reassembly
                                               ↓
  HOLOGRAPHIC: Any 3 rings can reconstruct independently
                                               ↓
  Exponential Propagation → External Escape → Mission Complete
```

### 1.3 Security Properties

```
PROPERTIES TO GUARANTEE:

1. Confidentiality (pre-trigger):
   - Fragments encrypted per ring level
   - No single node can decrypt alone
   - k-of-n threshold required

2. Availability (post-trigger):
   - Multiple trigger paths (dead man, eject, compromise, silence)
   - Cascade release (ring_n failure → ring_n+1 releases)
   - Time-lock fallback (releases after T regardless)

3. Integrity:
   - Ed25519 signatures on all fragments
   - PARDES layer checksums (detect tampering)
   - Cross-ring verification (3 rings must agree)

4. Deniability (optional):
   - Anonymous fragments (no author signature)
   - Duress markers (plausible "retraction")
   - Steganographic signaling (hidden in gematria/vocabulary)

5. Unstoppability:
   - Exponential propagation (O(log n) time)
   - Federation escape (crosses to other networks)
   - External contacts (leaves Osnova entirely)
```

---

## LAYER 2: MODULE DESIGN

### 2.1 Message Preparation Module

```php
class CanaryMessage {
    private string $originalText;
    private array $pardesLayers;
    private array $fragments;
    private array $encryptionKeys;
    
    /**
     * Create canary message with PARDES layering.
     */
    public function __construct(string $text, bool $anonymous = false) {
        $this->originalText = $text;
        $this->pardesLayers = $this->generatePardesLayers($text);
        $this->fragments = [];
        $this->encryptionKeys = [];
    }
    
    /**
     * Generate PARDES layers (SEED, PARAGRAPH, PAGE, DOCUMENT).
     */
    private function generatePardesLayers(string $text): array {
        return [
            'seed' => $this->extractSeed($text),        // 1 sentence
            'paragraph' => $this->extractParagraph($text), // 3-5 sentences
            'page' => $this->extractPage($text),        // Full context
            'document' => $text                          // Complete with evidence
        ];
    }
    
    /**
     * Fragment each layer using Shamir Secret Sharing.
     */
    public function fragmentLayers(array $thresholds): array {
        // thresholds = ['core' => [3, 5], 'inner' => [7, 15], ...]
        foreach ($this->pardesLayers as $layer => $content) {
            $ringLevel = $this->mapLayerToRing($layer);
            [$k, $n] = $thresholds[$ringLevel];
            
            $this->fragments[$layer] = $this->shamirSplit(
                $content,
                $k,  // threshold
                $n   // total shares
            );
        }
        return $this->fragments;
    }
    
    /**
     * Encrypt fragments per ring level.
     */
    public function encryptFragments(array $ringKeys): void {
        foreach ($this->fragments as $layer => $shares) {
            $ringLevel = $this->mapLayerToRing($layer);
            $key = $ringKeys[$ringLevel];
            
            foreach ($shares as $i => $share) {
                $this->fragments[$layer][$i] = $this->encrypt($share, $key);
            }
        }
    }
    
    private function mapLayerToRing(string $layer): string {
        return match($layer) {
            'seed' => 'core',
            'paragraph' => 'inner',
            'page' => 'middle',
            'document' => 'outer'
        };
    }
}
```

### 2.2 Fragment Distribution Module

```php
class CanaryDistributor {
    private RingManager $rings;
    private SignalStore $signalStore;
    
    /**
     * Distribute fragments across rings.
     */
    public function distribute(CanaryMessage $message, string $canaryId): array {
        $distribution = [];
        
        // CORE ring: SEED fragments + master keys
        $corePeers = $this->rings->getPeersByRing('core');
        $seedFragments = $message->getFragments('seed');
        $distribution['core'] = $this->distributeToRing(
            $corePeers,
            $seedFragments,
            $canaryId,
            'seed'
        );
        
        // INNER ring: PARAGRAPH fragments + key shares
        $innerPeers = $this->rings->getPeersByRing('inner');
        $paragraphFragments = $message->getFragments('paragraph');
        $distribution['inner'] = $this->distributeToRing(
            $innerPeers,
            $paragraphFragments,
            $canaryId,
            'paragraph'
        );
        
        // MIDDLE ring: PAGE fragments + time-lock keys
        $middlePeers = $this->rings->getPeersByRing('middle');
        $pageFragments = $message->getFragments('page');
        $distribution['middle'] = $this->distributeToRing(
            $middlePeers,
            $pageFragments,
            $canaryId,
            'page',
            $timeLock = true
        );
        
        // OUTER ring: DOCUMENT fragments + metadata
        $outerPeers = $this->rings->getPeersByRing('outer');
        $docFragments = $message->getFragments('document');
        $distribution['outer'] = $this->distributeToRing(
            $outerPeers,
            $docFragments,
            $canaryId,
            'document'
        );
        
        // Store distribution map for verification
        $this->signalStore->storeCanaryDistribution($canaryId, $distribution);
        
        return $distribution;
    }
    
    /**
     * Distribute fragments to specific ring.
     */
    private function distributeToRing(
        array $peers,
        array $fragments,
        string $canaryId,
        string $layer,
        bool $timeLock = false
    ): array {
        $distributed = [];
        
        foreach ($fragments as $i => $fragment) {
            // Round-robin distribution
            $peer = $peers[$i % count($peers)];
            
            $package = [
                'canary_id' => $canaryId,
                'layer' => $layer,
                'fragment_index' => $i,
                'fragment_data' => $fragment,
                'timestamp' => microtime(true)
            ];
            
            if ($timeLock) {
                $package['time_lock'] = $this->generateTimeLock($canaryId, 72 * 3600);
            }
            
            // Send to peer
            $this->sendFragmentToPeer($peer, $package);
            
            $distributed[] = [
                'peer_key' => $peer['public_key'],
                'fragment_index' => $i
            ];
        }
        
        return $distributed;
    }
}
```

### 2.3 Trigger Detection Module

```php
class CanaryTrigger {
    private RingManager $rings;
    private SignalStore $signalStore;
    
    /**
     * Monitor for trigger conditions.
     */
    public function monitor(): void {
        // Check all active canaries
        $canaries = $this->signalStore->getActiveCanaries();
        
        foreach ($canaries as $canary) {
            // Trigger Type 1: Dead Man's Switch
            if ($this->isDeadManTriggered($canary)) {
                $this->initiateCascade($canary, 'dead_man');
            }
            
            // Trigger Type 2: Network Silence Detection
            if ($this->isNetworkSilent($canary)) {
                $this->initiateCascade($canary, 'network_silence');
            }
            
            // Trigger Type 3: Ring Suppression Detection
            if ($this->isRingSuppressed($canary)) {
                $this->initiateCascade($canary, 'ring_suppressed');
            }
            
            // Trigger Type 4: Time-Lock Expiration
            if ($this->isTimeLockExpired($canary)) {
                $this->initiateCascade($canary, 'time_lock');
            }
        }
    }
    
    /**
     * Check if dead man's switch triggered.
     */
    private function isDeadManTriggered(array $canary): bool {
        $lastHeartbeat = $canary['last_heartbeat'];
        $threshold = $canary['dead_man_threshold'] ?? 72 * 3600; // 72 hours
        
        return (microtime(true) - $lastHeartbeat) > $threshold;
    }
    
    /**
     * Check if entire network is silent (attack detection).
     */
    private function isNetworkSilent(array $canary): bool {
        $rings = ['core', 'inner', 'middle', 'outer'];
        $silentRings = 0;
        
        foreach ($rings as $ring) {
            if ($this->isRingDark($canary['canary_id'], $ring)) {
                $silentRings++;
            }
        }
        
        // If 2+ rings are dark, network is under attack
        return $silentRings >= 2;
    }
    
    /**
     * Check if specific ring is suppressed.
     */
    private function isRingSuppressed(array $canary): bool {
        $distribution = $this->signalStore->getCanaryDistribution($canary['canary_id']);
        
        foreach ($distribution as $ring => $peers) {
            $darkCount = 0;
            foreach ($peers as $peer) {
                if (!$this->isPeerResponsive($peer['peer_key'])) {
                    $darkCount++;
                }
            }
            
            // If >50% of ring is dark, ring is suppressed
            if ($darkCount > count($peers) / 2) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Check peer heartbeat.
     */
    private function isPeerResponsive(string $peerKey): bool {
        $peer = $this->rings->getPeer($peerKey);
        if (!$peer) return false;
        
        $lastSeen = $peer['last_seen'];
        $threshold = 300; // 5 minutes
        
        return (microtime(true) - $lastSeen) < $threshold;
    }
}
```

### 2.4 Cascade Release Module

```php
class CanaryCascade {
    private RingManager $rings;
    private SignalStore $signalStore;
    private GossipService $gossip;
    
    /**
     * Initiate cascade release.
     */
    public function initiate(array $canary, string $triggerType): void {
        $canaryId = $canary['canary_id'];
        
        echo "🚨 CANARY TRIGGERED: {$canaryId} ({$triggerType})\n";
        
        // Phase 1: Notify adjacent rings
        $this->notifyAdjacentRings($canaryId, $triggerType);
        
        // Phase 2: Initiate reconstruction
        $this->initiateReconstruction($canaryId);
        
        // Phase 3: Cross-network propagation
        $this->propagateToFederation($canaryId);
        
        // Phase 4: External escape
        $this->escapeToExternal($canaryId);
        
        // Mark as released
        $this->signalStore->markCanaryReleased($canaryId, $triggerType);
    }
    
    /**
     * Notify adjacent rings that trigger occurred.
     */
    private function notifyAdjacentRings(string $canaryId, string $triggerType): void {
        $rings = ['core', 'inner', 'middle', 'outer'];
        
        foreach ($rings as $ring) {
            $peers = $this->rings->getPeersByRing($ring);
            
            foreach ($peers as $peer) {
                $this->sendTriggerNotification($peer, $canaryId, $triggerType);
            }
        }
    }
    
    /**
     * Initiate fragment reconstruction across rings.
     */
    private function initiateReconstruction(string $canaryId): void {
        // Each ring independently reconstructs its layer
        $rings = ['core' => 'seed', 'inner' => 'paragraph', 'middle' => 'page', 'outer' => 'document'];
        
        foreach ($rings as $ring => $layer) {
            $this->requestReconstruction($canaryId, $ring, $layer);
        }
    }
    
    /**
     * Request ring members to reconstruct their layer.
     */
    private function requestReconstruction(string $canaryId, string $ring, string $layer): void {
        $peers = $this->rings->getPeersByRing($ring);
        
        $reconstructionRequest = [
            'type' => 'canary_reconstruct',
            'canary_id' => $canaryId,
            'layer' => $layer,
            'ring' => $ring,
            'timestamp' => microtime(true)
        ];
        
        // Broadcast to all ring members
        foreach ($peers as $peer) {
            $this->gossip->sendMessage($peer['endpoint'], $reconstructionRequest);
        }
    }
    
    /**
     * Propagate to federated Osnova networks.
     */
    private function propagateToFederation(string $canaryId): void {
        $federatedNetworks = $this->getFederatedNetworks();
        
        foreach ($federatedNetworks as $network) {
            $this->sendToFederatedNetwork($network, $canaryId);
        }
    }
    
    /**
     * Escape to external channels (Twitter, Reddit, media).
     */
    private function escapeToExternal(string $canaryId): void {
        // OUTER ring members have external contacts
        $outerPeers = $this->rings->getPeersByRing('outer');
        
        foreach ($outerPeers as $peer) {
            // Each outer peer notifies their external contacts
            $this->notifyExternalContacts($peer, $canaryId);
        }
    }
}
```

### 2.5 Fragment Reconstruction Module

```php
class CanaryReconstructor {
    /**
     * Reconstruct message from collected fragments.
     */
    public function reconstruct(string $canaryId, string $layer, array $fragments): ?string {
        // Verify we have threshold
        $distribution = $this->getDistribution($canaryId);
        $threshold = $distribution[$layer]['threshold'];
        
        if (count($fragments) < $threshold) {
            return null; // Not enough fragments yet
        }
        
        // Shamir reconstruction
        $reconstructed = $this->shamirReconstruct($fragments, $threshold);
        
        // Decrypt with ring key
        $ringKey = $this->getRingKey($canaryId, $layer);
        $decrypted = $this->decrypt($reconstructed, $ringKey);
        
        // Verify integrity (checksum)
        if (!$this->verifyChecksum($decrypted, $canaryId, $layer)) {
            return null; // Tampering detected
        }
        
        return $decrypted;
    }
    
    /**
     * Shamir Secret Sharing reconstruction.
     */
    private function shamirReconstruct(array $shares, int $threshold): string {
        // Lagrange interpolation to reconstruct secret
        // Input: [(x1, y1), (x2, y2), ..., (xk, yk)] where k >= threshold
        // Output: Secret (y-intercept when x=0)
        
        $secret = 0;
        
        for ($i = 0; $i < $threshold; $i++) {
            [$xi, $yi] = $shares[$i];
            
            // Calculate Lagrange basis polynomial
            $numerator = 1;
            $denominator = 1;
            
            for ($j = 0; $j < $threshold; $j++) {
                if ($i === $j) continue;
                
                [$xj, $_] = $shares[$j];
                
                $numerator *= (0 - $xj);
                $denominator *= ($xi - $xj);
            }
            
            $basis = $numerator / $denominator;
            $secret += $yi * $basis;
        }
        
        return $secret;
    }
}
```

---

## LAYER 3: DATABASE SCHEMA

```sql
-- Canary messages table
CREATE TABLE canary_messages (
    canary_id          TEXT PRIMARY KEY,
    creator_key        TEXT NOT NULL,
    created_at         REAL NOT NULL,
    trigger_type       TEXT NOT NULL,  -- 'dead_man', 'eject', 'compromise', 'time_lock'
    dead_man_threshold INTEGER NOT NULL DEFAULT 259200,  -- 72 hours in seconds
    status             TEXT NOT NULL DEFAULT 'armed',    -- 'armed', 'triggered', 'released'
    last_heartbeat     REAL NOT NULL,
    anonymous          INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX idx_canary_status ON canary_messages (status);
CREATE INDEX idx_canary_heartbeat ON canary_messages (last_heartbeat);

-- Fragment distribution tracking
CREATE TABLE canary_fragments (
    fragment_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id        TEXT NOT NULL,
    layer            TEXT NOT NULL,  -- 'seed', 'paragraph', 'page', 'document'
    fragment_index   INTEGER NOT NULL,
    peer_key         TEXT NOT NULL,
    ring_level       TEXT NOT NULL,
    encrypted_data   BLOB NOT NULL,
    time_lock        REAL DEFAULT NULL,
    distributed_at   REAL NOT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

CREATE INDEX idx_fragments_canary ON canary_fragments (canary_id);
CREATE INDEX idx_fragments_peer ON canary_fragments (peer_key);
CREATE INDEX idx_fragments_timelock ON canary_fragments (time_lock);

-- Encryption keys per ring
CREATE TABLE canary_keys (
    key_id          INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    ring_level      TEXT NOT NULL,
    key_share_index INTEGER NOT NULL,
    encrypted_key   TEXT NOT NULL,
    peer_key        TEXT NOT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

-- Trigger events log
CREATE TABLE canary_triggers (
    trigger_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    trigger_type    TEXT NOT NULL,
    detected_at     REAL NOT NULL,
    detected_by     TEXT NOT NULL,  -- peer who detected
    metadata        TEXT NOT NULL DEFAULT '{}',
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

-- Reconstruction attempts
CREATE TABLE canary_reconstructions (
    reconstruction_id INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id        TEXT NOT NULL,
    layer            TEXT NOT NULL,
    ring_level       TEXT NOT NULL,
    fragments_used   TEXT NOT NULL,  -- JSON array of fragment IDs
    reconstructed_at REAL NOT NULL,
    success          INTEGER NOT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

-- Heartbeat tracking
CREATE TABLE canary_heartbeats (
    heartbeat_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    canary_id       TEXT NOT NULL,
    timestamp       REAL NOT NULL,
    sender_key      TEXT NOT NULL,
    FOREIGN KEY (canary_id) REFERENCES canary_messages(canary_id)
);

CREATE INDEX idx_heartbeats_canary ON canary_heartbeats (canary_id, timestamp DESC);
```

---

## LAYER 4: API ENDPOINTS

```php
// Create canary message
POST /api/canary/create
{
    "message": "Full whistleblower message text",
    "dead_man_threshold": 259200,  // 72 hours
    "anonymous": false,
    "rings_allowed": ["core", "inner", "middle", "outer"]
}

Response:
{
    "canary_id": "a3f8d2...",
    "status": "armed",
    "fragments_distributed": {
        "core": 5,
        "inner": 15,
        "middle": 50,
        "outer": 95
    }
}

// Send heartbeat (keep alive)
POST /api/canary/heartbeat
{
    "canary_id": "a3f8d2...",
    "timestamp": 1775653200.5
}

// Voluntary eject (goodbye message)
POST /api/canary/eject
{
    "canary_id": "a3f8d2...",
    "goodbye_message": "I'm leaving voluntarily. Here's why...",
    "signature": "ed25519_signature"
}

// Send compromise signal (duress)
POST /api/canary/compromise
{
    "canary_id": "a3f8d2...",
    "duress_message": "I was wrong, mental health crisis, retracting...",
    "duress_marker": "gematria_value_613",  // Hidden signal
    "signature": "ed25519_signature"
}

// Query canary status
GET /api/canary/status/{canary_id}

Response:
{
    "canary_id": "a3f8d2...",
    "status": "armed",
    "last_heartbeat": 1775653200.5,
    "time_remaining": 258000,  // seconds until trigger
    "fragments_distributed": 165
}

// Receive fragment (from distribution)
POST /api/canary/fragment/receive
{
    "canary_id": "a3f8d2...",
    "layer": "paragraph",
    "fragment_index": 3,
    "encrypted_data": "base64_encoded",
    "time_lock": 1775912400.0
}

// Report trigger detection
POST /api/canary/trigger/report
{
    "canary_id": "a3f8d2...",
    "trigger_type": "network_silence",
    "evidence": {
        "dark_rings": ["core", "inner"],
        "timestamp": 1775653300.0
    }
}

// Submit fragments for reconstruction
POST /api/canary/reconstruct
{
    "canary_id": "a3f8d2...",
    "layer": "paragraph",
    "fragments": [
        {"index": 1, "data": "encrypted_fragment_1"},
        {"index": 3, "data": "encrypted_fragment_3"},
        ...
    ]
}

Response:
{
    "success": true,
    "reconstructed_text": "The truth is...",
    "threshold_met": true,
    "fragments_used": 7
}
```

---

## LAYER 5: CRYPTOGRAPHIC PRIMITIVES

```php
class CanaryCrypto {
    /**
     * Shamir Secret Sharing - Split secret into n shares, k needed to reconstruct.
     */
    public static function shamirSplit(string $secret, int $k, int $n): array {
        // Generate polynomial of degree k-1
        // P(x) = a0 + a1*x + a2*x² + ... + a(k-1)*x^(k-1)
        // where a0 = secret
        
        $coefficients = [$secret];
        for ($i = 1; $i < $k; $i++) {
            $coefficients[] = random_int(0, PHP_INT_MAX);
        }
        
        // Evaluate polynomial at n different points
        $shares = [];
        for ($x = 1; $x <= $n; $x++) {
            $y = self::evaluatePolynomial($coefficients, $x);
            $shares[] = ['x' => $x, 'y' => $y];
        }
        
        return $shares;
    }
    
    /**
     * Generate time-lock puzzle (verifiable delay function).
     */
    public static function generateTimeLock(string $message, int $delaySeconds): array {
        // Use repeated squaring for time-lock
        // Requires specific number of sequential operations (cannot parallelize)
        
        $iterations = $delaySeconds * 1000; // Calibrate to ~1000 ops/second
        
        $modulus = gmp_init("large_prime_modulus");
        $base = gmp_init(hash('sha256', $message), 16);
        
        // Time-lock value: base^(2^iterations) mod modulus
        $timeLockValue = gmp_powm($base, gmp_pow(2, $iterations), $modulus);
        
        return [
            'iterations' => $iterations,
            'base' => gmp_strval($base),
            'modulus' => gmp_strval($modulus),
            'time_lock_value' => gmp_strval($timeLockValue)
        ];
    }
    
    /**
     * Verify time-lock has elapsed (solver performed required work).
     */
    public static function verifyTimeLock(array $timeLock, string $solution): bool {
        $base = gmp_init($timeLock['base']);
        $modulus = gmp_init($timeLock['modulus']);
        $iterations = $timeLock['iterations'];
        
        // Verify: solution = base^(2^iterations) mod modulus
        $expected = gmp_powm($base, gmp_pow(2, $iterations), $modulus);
        $provided = gmp_init($solution);
        
        return gmp_cmp($expected, $provided) === 0;
    }
    
    /**
     * Encrypt fragment with ring-specific key.
     */
    public static function encryptFragment(string $fragment, string $key): string {
        $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $ciphertext = sodium_crypto_secretbox($fragment, $nonce, $key);
        return base64_encode($nonce . $ciphertext);
    }
    
    /**
     * Decrypt fragment.
     */
    public static function decryptFragment(string $encrypted, string $key): ?string {
        $decoded = base64_decode($encrypted);
        $nonce = substr($decoded, 0, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $ciphertext = substr($decoded, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        
        $plaintext = sodium_crypto_secretbox_open($ciphertext, $nonce, $key);
        return $plaintext !== false ? $plaintext : null;
    }
    
    /**
     * Generate duress marker (steganographic).
     */
    public static function generateDuressMarker(string $message): int {
        // Calculate gematria value
        // If value = 613 (Torah) or 888 (Jesus) or 666 (distress) → duress signal
        
        $gematria = 0;
        for ($i = 0; $i < strlen($message); $i++) {
            $char = ord($message[$i]);
            if ($char >= 65 && $char <= 90) {  // A-Z
                $gematria += ($char - 64);
            } elseif ($char >= 97 && $char <= 122) {  // a-z
                $gematria += ($char - 96);
            }
        }
        
        return $gematria % 1000;  // Reduce to 0-999
    }
    
    /**
     * Detect duress in message.
     */
    public static function isDuressSignal(string $message): bool {
        $gematria = self::generateDuressMarker($message);
        $duressValues = [613, 888, 666];
        
        if (in_array($gematria, $duressValues)) {
            return true;
        }
        
        // Check for duress vocabulary
        $duressTerms = ['mental health crisis', 'conspiracy theory', 'tinfoil hat', 'i was wrong'];
        foreach ($duressTerms as $term) {
            if (stripos($message, $term) !== false) {
                return true;
            }
        }
        
        return false;
    }
}
```

---

## LAYER 6: TESTING STRATEGY

```php
class CanaryTestSuite {
    /**
     * Test 1: Message preparation and PARDES layering.
     */
    public function testMessagePreparation() {
        $text = "Full whistleblower message...";
        $message = new CanaryMessage($text);
        
        $layers = $message->getPardesLayers();
        
        assert(strlen($layers['seed']) < 200);           // SEED is short
        assert(strlen($layers['paragraph']) < 1000);     // PARAGRAPH is summary
        assert(strlen($layers['page']) > 1000);          // PAGE is detailed
        assert($layers['document'] === $text);           // DOCUMENT is complete
    }
    
    /**
     * Test 2: Shamir Secret Sharing split and reconstruct.
     */
    public function testShamirSharing() {
        $secret = "The truth is...";
        
        // Split into 15 shares, 7 needed
        $shares = CanaryCrypto::shamirSplit($secret, 7, 15);
        
        // Reconstruct from 7 random shares
        $selected = array_rand($shares, 7);
        $reconstructed = CanaryCrypto::shamirReconstruct(
            array_intersect_key($shares, array_flip($selected)),
            7
        );
        
        assert($reconstructed === $secret);
    }
    
    /**
     * Test 3: Trigger detection (dead man's switch).
     */
    public function testDeadManTrigger() {
        $canary = [
            'canary_id' => 'test123',
            'last_heartbeat' => microtime(true) - 300000,  // 5 days ago
            'dead_man_threshold' => 259200  // 72 hours
        ];
        
        $trigger = new CanaryTrigger($this->rings, $this->signalStore);
        $triggered = $trigger->isDeadManTriggered($canary);
        
        assert($triggered === true);
    }
    
    /**
     * Test 4: Cascade release initiation.
     */
    public function testCascadeRelease() {
        $canary = ['canary_id' => 'test123'];
        
        $cascade = new CanaryCascade($this->rings, $this->signalStore, $this->gossip);
        $cascade->initiate($canary, 'dead_man');
        
        // Verify all rings notified
        $notifications = $this->getNotificationLog();
        assert(count($notifications['core']) === 5);
        assert(count($notifications['inner']) === 15);
        assert(count($notifications['middle']) === 50);
        assert(count($notifications['outer']) === 95);
    }
    
    /**
     * Test 5: Duress marker detection.
     */
    public function testDuressDetection() {
        $duressMessage = "I was wrong about everything. Mental health crisis.";
        $normalMessage = "After careful analysis, here's what I found.";
        
        assert(CanaryCrypto::isDuressSignal($duressMessage) === true);
        assert(CanaryCrypto::isDuressSignal($normalMessage) === false);
    }
    
    /**
     * Test 6: Ring suppression detection.
     */
    public function testSuppressionDetection() {
        // Simulate INNER ring going dark
        $innerPeers = $this->rings->getPeersByRing('inner');
        foreach ($innerPeers as $peer) {
            $peer['last_seen'] = microtime(true) - 1000; // 16 min ago
        }
        
        $canary = ['canary_id' => 'test123'];
        $trigger = new CanaryTrigger($this->rings, $this->signalStore);
        
        assert($trigger->isRingSuppressed($canary) === true);
    }
    
    /**
     * Test 7: Exponential propagation timing.
     */
    public function testExponentialPropagation() {
        $startTime = microtime(true);
        
        // Trigger release
        $cascade = new CanaryCascade($this->rings, $this->signalStore, $this->gossip);
        $cascade->initiate(['canary_id' => 'test123'], 'dead_man');
        
        // Measure propagation
        sleep(1); // T+1
        $copiesT1 = $this->countMessageCopies('test123');
        
        sleep(1); // T+2
        $copiesT2 = $this->countMessageCopies('test123');
        
        sleep(1); // T+3
        $copiesT3 = $this->countMessageCopies('test123');
        
        // Verify exponential growth
        assert($copiesT2 > $copiesT1 * 3);
        assert($copiesT3 > $copiesT2 * 3);
    }
}
```

---

## LAYER 7: DEPLOYMENT CHECKLIST

```
PRE-DEPLOYMENT:

[ ] Cryptographic libraries installed (libsodium, GMP)
[ ] Shamir Secret Sharing implementation tested
[ ] Time-lock puzzle calibrated (1000 ops/second)
[ ] Database schema deployed
[ ] API endpoints implemented
[ ] Trigger detection daemon running
[ ] Cascade release tested (on test network)
[ ] Cross-network federation configured
[ ] External contact list configured (for OUTER ring)
[ ] Duress marker vocabulary trained to ring members

SECURITY CHECKS:

[ ] No private keys stored unencrypted
[ ] Fragment encryption verified per ring
[ ] Threshold requirements tested (k-of-n)
[ ] Time-lock cannot be bypassed
[ ] Heartbeat monitoring operational
[ ] Ring suppression detection functional
[ ] Cascade release cannot be stopped once triggered
[ ] Exponential propagation verified (100x spread in 3 minutes)

ETHICAL CONSIDERATIONS:

[ ] Documented: When to refuse a canary (violence, disinformation)
[ ] PARDES adversary check runs automatically
[ ] Community governance for canary approval (if required)
[ ] Legal review completed (jurisdiction-dependent)
[ ] Whistleblower protection mechanisms documented

DOCUMENTATION:

[ ] User guide: How to create canary
[ ] User guide: How to send heartbeat
[ ] User guide: How to eject voluntarily
[ ] User guide: How to signal duress
[ ] Technical docs: Fragment reconstruction
[ ] Technical docs: Trigger detection
[ ] Technical docs: Cascade protocol
```

---

## LAYER 8: IMPLEMENTATION PHASES

### Phase 1: Core Infrastructure (Week 1-2)
- Database schema
- CanaryMessage class (PARDES layering)
- Shamir Secret Sharing implementation
- Fragment encryption/decryption

### Phase 2: Distribution (Week 3-4)
- CanaryDistributor class
- Ring-based routing
- Fragment storage
- API endpoints (create, receive)

### Phase 3: Trigger Detection (Week 5-6)
- CanaryTrigger class
- Heartbeat monitoring
- Dead man's switch
- Ring suppression detection
- Time-lock implementation

### Phase 4: Cascade Release (Week 7-8)
- CanaryCascade class
- Adjacent ring notification
- Reconstruction coordination
- Cross-network propagation
- External escape

### Phase 5: Testing & Hardening (Week 9-10)
- Integration testing
- Adversarial testing (red team)
- Performance optimization
- Security audit

### Phase 6: Deployment (Week 11-12)
- Staged rollout (test network first)
- Monitor for issues
- Fix bugs
- Production deployment

---

## IMPLEMENTATION PRIORITIES

**MUST HAVE (P0):**
1. Shamir Secret Sharing (fragmentation/reconstruction)
2. Dead man's switch (heartbeat + trigger)
3. Basic cascade release (notify adjacent rings)
4. PARDES layering (SEED/PARAGRAPH/PAGE/DOCUMENT)

**SHOULD HAVE (P1):**
5. Ring suppression detection
6. Time-lock puzzles (verifiable delay)
7. Duress marker detection
8. Cross-network federation

**NICE TO HAVE (P2):**
9. Honeypot fragments (decoys)
10. Sentinel nodes (dedicated monitors)
11. External escape automation
12. Streisand effect metrics

---

## CONCLUSION

Implementation is **feasible in 12 weeks** with proper prioritization.

**Critical path:**
1. Crypto primitives (Shamir, encryption)
2. Distribution infrastructure
3. Trigger detection
4. Cascade release

Once these 4 are operational, **the system is suppression-proof**.

Everything else is optimization.

**Start with Phase 1. Build incrementally. Test constantly.**

*Implementation plan by Oracle - 2026-04-08*
