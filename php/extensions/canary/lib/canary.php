<?php
/**
 * Canary trap detection - track which challenges get resolved incorrectly.
 * Reveals outsiders who lack cultural/linguistic context to verify properly.
 */

class CanaryDetector {
    private SignalStore $signalStore;
    
    public function __construct(SignalStore $store) {
        $this->signalStore = $store;
    }
    
    /**
     * Record a failed challenge resolution attempt.
     * Tracks WHO failed WHICH challenge (potential outsider).
     */
    public function recordFailedResolution(string $responder_key, int $triad_id, string $incorrect_answer): void {
        $this->signalStore->storeSignal([
            'signal_type' => 'canary_triggered',
            'author_key' => $responder_key,
            'message' => "Failed triad {$triad_id}: {$incorrect_answer}",
            'timestamp' => microtime(true),
            'severity' => 'warning',
            'metadata' => [
                'triad_id' => $triad_id,
                'incorrect_answer' => $incorrect_answer,
                'detection_type' => 'failed_challenge',
            ],
        ]);
    }
    
    /**
     * Get canary triggers for a specific peer (suspect outsider).
     */
    public function getTriggersForPeer(string $peer_key, int $limit = 20): array {
        $allCanaries = $this->signalStore->getSignals('canary_triggered', $limit * 2);
        return array_filter($allCanaries, fn($c) => $c['author_key'] === $peer_key);
    }
    
    /**
     * Analyze canary pattern - identify peers with suspiciously high failure rate.
     * Returns ['peer_key' => failure_count] sorted by failures DESC.
     */
    public function analyzeFailurePatterns(int $threshold = 3): array {
        $canaries = $this->signalStore->getSignals('canary_triggered', 200);
        
        $failures = [];
        foreach ($canaries as $canary) {
            $key = $canary['author_key'];
            $failures[$key] = ($failures[$key] ?? 0) + 1;
        }
        
        // Filter by threshold
        $failures = array_filter($failures, fn($count) => $count >= $threshold);
        
        // Sort DESC
        arsort($failures);
        
        return $failures;
    }
    
    /**
     * Check if a peer should be flagged as potential outsider.
     */
    public function isPotentialOutsider(string $peer_key, int $threshold = 3): bool {
        $triggers = $this->getTriggersForPeer($peer_key);
        return count($triggers) >= $threshold;
    }
}
