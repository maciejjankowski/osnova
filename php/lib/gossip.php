<?php
/**
 * GossipService - pull-based sync between Osnova nodes via HTTP/curl.
 *
 * JSON wire format is identical to the Python SyncRequest/SyncResponse
 * so PHP and Python nodes can interoperate.
 */
class GossipService {
    private ContentLog  $log;
    private RingManager $rings;
    private string      $nodeKey;

    public function __construct(ContentLog $log, RingManager $rings, string $nodeKey) {
        $this->log     = $log;
        $this->rings   = $rings;
        $this->nodeKey = $nodeKey;
    }

    /**
     * Pull new entries from one peer's /api/sync endpoint.
     * Returns the number of new entries appended.
     */
    public function pullFromPeer(string $peerEndpoint, string $peerKey, float $since = 0.0): int {
        $known = $this->log->getHashesSince($since);

        $payload = json_encode([
            'requester_key'   => $this->nodeKey,
            'known_hashes'    => $known,
            'since_timestamp' => $since,
            'max_entries'     => 100,
        ]);

        $url = rtrim($peerEndpoint, '/') . '/api/sync';
        $response = $this->httpPost($url, $payload);
        if ($response === null) return 0;

        $data = json_decode($response, true);
        if (!$data || !isset($data['entries'])) return 0;

        $knownSet = array_flip($known);
        $appended = 0;
        foreach ($data['entries'] as $entryData) {
            $hash = $entryData['content_hash'] ?? null;
            if (!$hash || isset($knownSet[$hash])) continue;
            // Verify signature before storing
            if (!empty($entryData['signature'])) {
                $computedHash = crypto_content_hash(
                    $entryData['author_key'],
                    $entryData['content_type'],
                    $entryData['body'],
                    $entryData['parent_hash'] ?? null,
                    (float)$entryData['timestamp']
                );
                if (!crypto_verify_content($computedHash, $entryData['author_key'], $entryData['signature'])) {
                    continue; // Drop entries with bad signatures
                }
            }
            try {
                $this->log->append($entryData);
                $knownSet[$hash] = true;
                $appended++;
            } catch (\RuntimeException) {
                // Already exists (race) - safe to ignore
            }
        }

        // Update last_seen for the peer
        $this->rings->updateLastSeen($peerKey, microtime(true));
        return $appended;
    }

    /**
     * Prepare a SyncResponse for an inbound SyncRequest.
     * Filters content based on requester's ring level:
     * - CORE/INNER: Full replication (all layers)
     * - MIDDLE: SEEDs + PARAGRAPHs only
     * - OUTER: On-demand only (no auto-sync)
     * Returns JSON-serializable array.
     */
    public function prepareSyncResponse(array $request): array {
        $since      = (float)($request['since_timestamp'] ?? 0.0);
        $knownSet   = array_flip($request['known_hashes'] ?? []);
        $maxEntries = (int)($request['max_entries'] ?? 100);
        $requesterKey = $request['requester_key'] ?? null;

        $candidates = $this->log->getHashesSince($since);
        $missing    = array_filter($candidates, fn($h) => !isset($knownSet[$h]));
        $missing    = array_values($missing);

        $hasMore = count($missing) > $maxEntries;
        $capped  = array_slice($missing, 0, $maxEntries);

        $entries = $this->log->getEntriesByHashes($capped);
        
        // Filter by ring level if requester is in MIDDLE ring
        if ($requesterKey) {
            $peer = $this->rings->getPeer($requesterKey);
            if ($peer && $peer['ring_level'] === 'middle') {
                require_once __DIR__ . '/pardes.php';
                $entries = array_filter($entries, function($entry) {
                    return PardesDetector::shouldReplicateToMiddleRing($entry);
                });
                $entries = array_values($entries); // Re-index
            }
        }
        
        // Sort ASC by timestamp (same as Python)
        usort($entries, fn($a, $b) => $a['timestamp'] <=> $b['timestamp']);

        return [
            'entries'  => $entries,
            'peer_key' => $this->nodeKey,
            'has_more' => $hasMore,
        ];
    }

    /**
     * Run a gossip round: pull from CORE + INNER peers.
     * Returns ['peer_key' => entries_count]
     */
    public function runGossipRound(): array {
        $peers = array_merge(
            $this->rings->getPeersByRing('core'),
            $this->rings->getPeersByRing('inner')
        );
        $results = [];
        foreach ($peers as $peer) {
            $count = $this->pullFromPeer($peer['endpoint'], $peer['public_key']);
            $results[$peer['public_key']] = $count;
        }
        return $results;
    }

    // -----------------------------------------------------------------------
    private function httpPost(string $url, string $jsonBody, int $timeout = 10): ?string {
        if (!function_exists('curl_init')) return null;
        $ch = curl_init($url);
        curl_setopt_array($ch, [
            CURLOPT_POST           => true,
            CURLOPT_POSTFIELDS     => $jsonBody,
            CURLOPT_RETURNTRANSFER => true,
            CURLOPT_TIMEOUT        => $timeout,
            CURLOPT_HTTPHEADER     => ['Content-Type: application/json', 'Accept: application/json'],
            CURLOPT_FOLLOWLOCATION => false,
            CURLOPT_SSL_VERIFYPEER => true,
        ]);
        $resp  = curl_exec($ch);
        $code  = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        return ($resp !== false && $code >= 200 && $code < 300) ? $resp : null;
    }
}
