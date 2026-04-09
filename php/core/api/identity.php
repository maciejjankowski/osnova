<?php
/**
 * Identity API
 * GET /api/identity - return this node's public identity
 */

function api_identity_handler(string $method, array $kp): void {
    if ($method !== 'GET') {
        json_error(405, 'Method not allowed');
        return;
    }
    json_out([
        'public_key'   => $kp['public'],
        'display_name' => NODE_DISPLAY_NAME,
        'created_at'   => microtime(true),
        'endpoint'     => NODE_HOST,
    ]);
}
