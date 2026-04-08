<?php
/**
 * Sync API
 * POST /api/sync       - handle inbound SyncRequest from a peer
 * POST /api/sync/pull  - trigger a manual gossip round
 */

function api_sync_handler(string $method, array $segments, array $kp, ContentLog $log, RingManager $rings, GossipService $gossip): void {
    // /api/sync/pull
    if (count($segments) >= 3 && $segments[2] === 'pull') {
        if ($method === 'POST') {
            api_sync_pull($gossip);
            return;
        }
        json_error(405, 'Method not allowed');
        return;
    }

    // /api/sync
    if ($method === 'POST') {
        api_sync_handle_request($log, $rings, $gossip);
        return;
    }
    json_error(405, 'Method not allowed');
}

function api_sync_handle_request(ContentLog $log, RingManager $rings, GossipService $gossip): void {
    $request = json_input();

    // Update last_seen for the requester if we know them
    $requester = $request['requester_key'] ?? '';
    if ($requester) {
        $rings->updateLastSeen($requester, microtime(true));
    }

    $response = $gossip->prepareSyncResponse($request);
    json_out($response);
}

function api_sync_pull(GossipService $gossip): void {
    $results = $gossip->runGossipRound();
    $total   = array_sum($results);
    json_out([
        'peers_contacted'    => count($results),
        'total_new_entries'  => $total,
        'per_peer'           => $results,
    ]);
}
