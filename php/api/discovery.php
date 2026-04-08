<?php
/**
 * Discovery API
 * POST /api/discovery/create        - create a triad for a content hash
 * POST /api/discovery/resolve       - attempt to resolve a challenge
 * GET  /api/discovery/triads        - list triads (content_hash stripped)
 * POST /api/discovery/receive-key   - accept an inbound discovery key
 */

function api_discovery_handler(
    string      $method,
    array       $segments,
    array       $kp,
    RingManager $rings,
    TriadStore  $triadStore
): void {
    $action = $segments[2] ?? '';

    match (true) {
        $action === 'create'      && $method === 'POST' => api_discovery_create($kp, $rings, $triadStore),
        $action === 'resolve'     && $method === 'POST' => api_discovery_resolve($triadStore),
        $action === 'triads'      && $method === 'GET'  => api_discovery_list($triadStore),
        $action === 'receive-key' && $method === 'POST' => api_discovery_receive_key($triadStore),
        default => json_error(404, 'Unknown discovery endpoint'),
    };
}

function api_discovery_create(array $kp, RingManager $rings, TriadStore $triadStore): void {
    $body         = json_input();
    $content_hash = $body['content_hash'] ?? '';
    if (!$content_hash) {
        json_error(422, 'content_hash is required');
        return;
    }

    $decoy_key = $body['decoy_key'] ?? null;
    if (!$decoy_key) {
        // Auto-select from peers
        $peers     = $rings->getAllPeers();
        $peerDicts = array_map(fn($p) => ['public_key' => $p['public_key']], $peers);
        $decoy_key = discovery_select_decoy($peerDicts, $kp['public'], $content_hash);
        if (!$decoy_key) {
            // Synthetic decoy
            $decoy_key = hash('sha256', 'synthetic_decoy:' . $content_hash);
        }
    }

    $triad = discovery_create_triad($content_hash, $kp['public'], $kp['public'], $decoy_key);
    $triadStore->save($triad);

    // Strip content_hash from response (it's the secret)
    $response = $triad;
    unset($response['content_hash']);
    json_out($response);
}

function api_discovery_resolve(TriadStore $triadStore): void {
    $body      = json_input();
    $triad_id  = $body['triad_id']          ?? '';
    $chosen    = $body['chosen_candidate']   ?? '';
    $content_h = $body['content_hash']       ?? '';

    $triad = $triadStore->find($triad_id);
    if (!$triad) {
        json_error(404, 'Triad not found');
        return;
    }
    $valid = discovery_verify_resolution($triad, $chosen, $content_h);
    json_out(['valid' => $valid]);
}

function api_discovery_list(TriadStore $triadStore): void {
    $triads = $triadStore->listAll();
    $result = [];
    foreach ($triads as $t) {
        unset($t['content_hash']); // strip secret
        $result[] = $t;
    }
    json_out($result);
}

function api_discovery_receive_key(TriadStore $triadStore): void {
    $key = json_input();
    if (empty($key['key_id'])) {
        json_error(422, 'key_id is required');
        return;
    }
    $triadStore->saveKey($key);
    json_out(['accepted' => true, 'key_id' => $key['key_id']]);
}
