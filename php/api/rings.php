<?php
/**
 * Rings API
 * GET    /api/rings                       - stats
 * GET    /api/rings/{level}               - peers in level
 * POST   /api/rings/peers                 - add peer
 * DELETE /api/rings/peers/{key}           - remove peer
 * PUT    /api/rings/peers/{key}/promote   - change ring level
 */

function api_rings_handler(string $method, array $segments, RingManager $rings): void {
    // /api/rings/peers/{key}/promote
    if (count($segments) >= 5 && $segments[3] === 'promote') {
        $key = urldecode($segments[2]);
        api_rings_promote($key, $method, $rings);
        return;
    }

    // /api/rings/peers/{key}
    if (count($segments) === 4 && $segments[2] === 'peers') {
        $key = urldecode($segments[3]);
        if ($method === 'DELETE') {
            api_rings_remove($key, $rings);
            return;
        }
        json_error(405, 'Method not allowed');
        return;
    }

    // /api/rings/peers
    if (count($segments) === 3 && $segments[2] === 'peers') {
        if ($method === 'POST') {
            api_rings_add($rings);
            return;
        }
        json_error(405, 'Method not allowed');
        return;
    }

    // /api/rings/{level}
    if (count($segments) === 3 && $segments[2] !== 'peers') {
        $level = $segments[2];
        if ($method === 'GET') {
            api_rings_get_level($level, $rings);
            return;
        }
        json_error(405, 'Method not allowed');
        return;
    }

    // /api/rings
    if ($method === 'GET') {
        json_out($rings->getRingStats());
        return;
    }
    json_error(405, 'Method not allowed');
}

function api_rings_add(RingManager $rings): void {
    $body = json_input();
    $required = ['public_key', 'display_name', 'ring_level', 'endpoint'];
    foreach ($required as $f) {
        if (empty($body[$f])) {
            json_error(422, "Field '{$f}' is required");
            return;
        }
    }
    $caps = RING_CAPS;
    if (!isset($caps[$body['ring_level']])) {
        json_error(400, 'Invalid ring_level. Must be core|inner|middle|outer');
        return;
    }
    $peer = [
        'public_key'   => $body['public_key'],
        'display_name' => $body['display_name'],
        'ring_level'   => $body['ring_level'],
        'endpoint'     => $body['endpoint'],
        'added_at'     => $body['added_at'] ?? microtime(true),
        'last_seen'    => $body['last_seen'] ?? 0.0,
    ];
    $ok = $rings->addPeer($peer);
    if (!$ok) {
        json_error(409, "Ring '{$body['ring_level']}' is at capacity or peer already exists");
        return;
    }
    json_out($peer);
}

function api_rings_remove(string $key, RingManager $rings): void {
    $ok = $rings->removePeer($key);
    if (!$ok) {
        json_error(404, 'Peer not found');
        return;
    }
    json_out(['removed' => true, 'public_key' => $key]);
}

function api_rings_get_level(string $level, RingManager $rings): void {
    $caps = RING_CAPS;
    if (!isset($caps[$level])) {
        json_error(400, 'Invalid ring level. Must be core|inner|middle|outer');
        return;
    }
    json_out($rings->getPeersByRing($level));
}

function api_rings_promote(string $key, string $method, RingManager $rings): void {
    if ($method !== 'PUT') {
        json_error(405, 'Method not allowed');
        return;
    }
    $body = json_input();
    $new_level = $body['ring_level'] ?? '';
    $caps = RING_CAPS;
    if (!isset($caps[$new_level])) {
        json_error(400, 'Invalid ring_level');
        return;
    }
    $ok = $rings->setPeerRing($key, $new_level);
    if (!$ok) {
        json_error(409, 'Peer not found or target ring is at capacity');
        return;
    }
    $peer = $rings->getPeer($key);
    json_out($peer);
}
