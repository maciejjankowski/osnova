<?php
/**
 * Canary API - Whistleblower dead man's switch
 */

require_once __DIR__ . '/../lib/canary_extended.php';

function api_canary_handler(string $method, array $segments, array $kp, object $log): void {
    global $canarySystem;
    
    if (!isset($canarySystem)) {
        $canarySystem = new CanarySystemExtended(DATA_DIR . '/canary.db', $kp['public']);
    }
    
    $action = $segments[2] ?? 'status';
    
    match ($action) {
        'create' => match ($method) {
            'POST' => canary_create($canarySystem, $kp),
            default => json_error(405, 'Method not allowed')
        },
        
        'heartbeat' => match ($method) {
            'POST' => canary_heartbeat($canarySystem),
            default => json_error(405, 'Method not allowed')
        },
        
        'status' => match ($method) {
            'GET' => canary_status($canarySystem, $segments[3] ?? ''),
            default => json_error(405, 'Method not allowed')
        },
        
        'compromised' => match ($method) {
            'POST' => canary_compromised($canarySystem),
            default => json_error(405, 'Method not allowed')
        },
        
        'reconstruct' => match ($method) {
            'GET' => canary_reconstruct($canarySystem, $segments[3] ?? ''),
            default => json_error(405, 'Method not allowed')
        },
        
        'list' => match ($method) {
            'GET' => canary_list($canarySystem, $kp),
            default => json_error(405, 'Method not allowed')
        },
        
        default => json_error(404, "Unknown canary action: {$action}")
    };
}

function canary_create(object $system, array $kp): void {
    $data = json_input();
    
    if (!isset($data['message'])) {
        json_error(400, 'Missing message');
    }
    
    $canary_data = [
        'author_key' => $kp['public'],
        'message' => $data['message'],
        'encrypted_message' => $data['encrypted_message'] ?? $data['message'],
        'heartbeat_interval' => $data['heartbeat_interval'] ?? 86400,
        'fragment_count' => $data['fragment_count'] ?? 100,
    ];
    
    $result = $system->createCanary($canary_data);
    
    json_out($result, 201);
}

function canary_heartbeat(object $system): void {
    $data = json_input();
    
    if (!isset($data['canary_id'])) {
        json_error(400, 'Missing canary_id');
    }
    
    $method = $data['method'] ?? 'manual';
    $success = $system->heartbeat($data['canary_id'], $method);
    
    if (!$success) {
        json_error(404, 'Canary not found or not active');
    }
    
    json_out(['status' => 'ok', 'timestamp' => microtime(true)]);
}

function canary_status(object $system, string $canary_id): void {
    if (!$canary_id) {
        json_error(400, 'Missing canary_id');
    }
    
    $status = $system->getStatus($canary_id);
    
    if (!$status) {
        json_error(404, 'Canary not found');
    }
    
    json_out($status);
}

function canary_compromised(object $system): void {
    $data = json_input();
    
    if (!isset($data['canary_id']) || !isset($data['signal'])) {
        json_error(400, 'Missing canary_id or signal');
    }
    
    $success = $system->signalCompromised($data['canary_id'], $data['signal']);
    
    if (!$success) {
        json_error(404, 'Canary not found or already triggered');
    }
    
    json_out(['status' => 'compromised', 'cascade' => 'triggered']);
}

function canary_reconstruct(object $system, string $canary_id): void {
    if (!$canary_id) {
        json_error(400, 'Missing canary_id');
    }
    
    $result = $system->reconstructMessage($canary_id);
    
    json_out($result);
}

function canary_list(object $system, array $kp): void {
    // List canaries for this user
    // For now, just return empty array - full implementation would query by author_key
    json_out(['canaries' => []]);
}
