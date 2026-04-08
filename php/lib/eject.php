<?php
/**
 * EjectProtocol - voluntary node ejection and canary (compromise) signalling.
 */
class EjectProtocol {
    private ?string $nodeKey;

    public function __construct(?string $nodeKey = null) {
        $this->nodeKey = $nodeKey;
    }

    // -----------------------------------------------------------------------
    // Eject: package + broadcast
    // -----------------------------------------------------------------------

    /**
     * Build an EjectPackage (serializable array) from the content log and ring.
     */
    public function packageContent(
        ContentLog  $log,
        RingManager $rings,
        array       $kp,
        string      $closingMessage = '',
        bool        $includeProvenance = true
    ): array {
        $allEntries = [];
        $offset = 0;
        $chunk  = 500;
        while (true) {
            $batch = $log->getFeed($chunk, $offset);
            $allEntries = array_merge($allEntries, $batch);
            if (count($batch) < $chunk) break;
            $offset += $chunk;
        }

        $allPeers  = $rings->getAllPeers();
        $authorKey = $kp['public'];
        $timestamp = microtime(true);

        $payload   = $this->ejectPayload($authorKey, $timestamp, $closingMessage, count($allEntries));
        $signature = crypto_sign_bytes($payload, $kp);

        return [
            'author_key'         => $authorKey,
            'content_entries'    => $allEntries,
            'peer_list'          => $allPeers,
            'timestamp'          => $timestamp,
            'signature'          => $signature,
            'include_provenance' => $includeProvenance,
            'closing_message'    => $closingMessage,
        ];
    }

    /**
     * Broadcast an EJECT signal to all known peers (fire-and-forget).
     */
    public function broadcastEject(
        array       $package,
        RingManager $rings,
        array       $kp
    ): void {
        $signal = $this->buildSignal('eject', $kp, $package['closing_message'], 'info');
        $peers  = $rings->getAllPeers();
        $data   = array_merge($signal, [
            'closing_message'  => $package['closing_message'],
            'content_entries'  => $package['content_entries'],
            'peer_list'        => $package['peer_list'],
            'include_provenance' => $package['include_provenance'],
        ]);
        $this->broadcastTopeers($peers, $data);
    }

    // -----------------------------------------------------------------------
    // Canary: compromise signal
    // -----------------------------------------------------------------------

    public function broadcastCanary(RingManager $rings, array $kp, string $message = ''): array {
        $signal = $this->buildSignal('canary', $kp, $message, 'critical');
        $peers  = $rings->getAllPeers();
        $this->broadcastTopeers($peers, $signal);
        return $signal;
    }

    // -----------------------------------------------------------------------
    // Signal verification + storage
    // -----------------------------------------------------------------------

    /**
     * Verify a received signal (canary or eject).
     * Returns: "canary_received" | "eject_received" | "invalid_signature"
     */
    public function handleReceivedSignal(array $signal): string {
        $payload = $this->canaryPayload(
            $signal['author_key'],
            $signal['signal_type'],
            (float)$signal['timestamp'],
            $signal['message'] ?? ''
        );
        if (!crypto_verify_bytes($payload, $signal['author_key'], $signal['signature'] ?? '')) {
            return 'invalid_signature';
        }
        return match ($signal['signal_type']) {
            'canary' => 'canary_received',
            'eject'  => 'eject_received',
            default  => 'unknown_signal',
        };
    }

    // -----------------------------------------------------------------------
    // Internal
    // -----------------------------------------------------------------------

    private function buildSignal(string $type, array $kp, string $message, string $severity): array {
        $authorKey = $kp['public'];
        $timestamp = microtime(true);
        $payload   = $this->canaryPayload($authorKey, $type, $timestamp, $message);
        $signature = crypto_sign_bytes($payload, $kp);
        return [
            'author_key'   => $authorKey,
            'signal_type'  => $type,
            'message'      => $message,
            'timestamp'    => $timestamp,
            'signature'    => $signature,
            'severity'     => $severity,
        ];
    }

    private function ejectPayload(string $authorKey, float $timestamp, string $closing, int $count): string {
        $raw = "{$authorKey}:{$timestamp}:{$closing}:{$count}";
        return hash('sha256', $raw);
    }

    private function canaryPayload(string $authorKey, string $type, float $timestamp, string $message): string {
        $raw = "{$authorKey}:{$type}:{$timestamp}:{$message}";
        return hash('sha256', $raw);
    }

    private function broadcastTopeers(array $peers, array $data): void {
        if (!function_exists('curl_init')) return;
        $json = json_encode($data);
        foreach ($peers as $peer) {
            $url = rtrim($peer['endpoint'], '/') . '/api/signals/receive';
            $ch  = curl_init($url);
            curl_setopt_array($ch, [
                CURLOPT_POST           => true,
                CURLOPT_POSTFIELDS     => $json,
                CURLOPT_RETURNTRANSFER => true,
                CURLOPT_TIMEOUT        => 5,
                CURLOPT_HTTPHEADER     => ['Content-Type: application/json'],
                CURLOPT_FOLLOWLOCATION => false,
            ]);
            curl_exec($ch); // fire and forget
            curl_close($ch);
        }
    }
}

// ---------------------------------------------------------------------------
// Signals SQLite store (received canary/eject signals)
// ---------------------------------------------------------------------------
class SignalStore {
    private SQLite3 $db;

    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS signals (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                signal_type TEXT NOT NULL,
                author_key  TEXT NOT NULL,
                message     TEXT,
                timestamp   REAL NOT NULL,
                signature   TEXT,
                severity    TEXT,
                received_at REAL NOT NULL
            )
        ");
    }

    public function store(array $signal): void {
        $stmt = $this->db->prepare("
            INSERT INTO signals (signal_type, author_key, message, timestamp, signature, severity, received_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $signal['signal_type'],       SQLITE3_TEXT);
        $stmt->bindValue(2, $signal['author_key'],        SQLITE3_TEXT);
        $stmt->bindValue(3, $signal['message'] ?? '',     SQLITE3_TEXT);
        $stmt->bindValue(4, (float)$signal['timestamp'],  SQLITE3_FLOAT);
        $stmt->bindValue(5, $signal['signature'] ?? '',   SQLITE3_TEXT);
        $stmt->bindValue(6, $signal['severity'] ?? '',    SQLITE3_TEXT);
        $stmt->bindValue(7, microtime(true),              SQLITE3_FLOAT);
        $stmt->execute();
    }

    public function getAll(int $limit = 50): array {
        $stmt = $this->db->prepare("SELECT * FROM signals ORDER BY received_at DESC LIMIT ?");
        $stmt->bindValue(1, $limit, SQLITE3_INTEGER);
        $res  = $stmt->execute();
        $rows = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $rows[] = $row;
        }
        return $rows;
    }
}
