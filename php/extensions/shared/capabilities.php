<?php
/**
 * Capabilities API
 * Handles progressive feature unlocking based on ring membership and phantom users
 */

function api_capabilities_handler(string $method, array $segments, array $kp, object $rings): void {
    $action = $segments[2] ?? 'check';
    
    match ($action) {
        'check' => match ($method) {
            'GET' => capabilities_check($kp, $rings),
            default => json_error(405, 'Method not allowed')
        },
        
        'unlock' => match ($method) {
            'POST' => capabilities_unlock($kp, $rings),
            default => json_error(405, 'Method not allowed')
        },
        
        default => json_error(404, "Unknown capability action: {$action}")
    };
}

function capabilities_check(array $kp, object $rings): void {
    $public_key = $kp['public'];
    $peers = $rings->getAllPeers();
    
    // Check for phantom users in ring
    $phantom_users = [
        'leo_setup',
        'manual_reader',
        'canary_witness',
        'spam_trainer'
    ];
    
    $unlocked_capabilities = [];
    
    foreach ($peers as $peer) {
        $peer_name = $peer['display_name'] ?? '';
        
        if (in_array($peer_name, $phantom_users)) {
            $unlocked_capabilities[] = match ($peer_name) {
                'leo_setup' => 'help_center',
                'manual_reader' => 'advanced_docs',
                'canary_witness' => 'canary_composer',
                'spam_trainer' => 'spam_folder',
                default => null
            };
        }
    }
    
    $unlocked_capabilities = array_filter($unlocked_capabilities);
    
    // Check if user should see "update" prompt for keystroke telemetry
    $ring_size = count($peers);
    $should_show_telemetry = $ring_size >= 3 && !in_array('keystroke_telemetry', $unlocked_capabilities);
    
    json_out([
        'capabilities' => $unlocked_capabilities,
        'update_available' => $should_show_telemetry,
        'next_capability' => $should_show_telemetry ? 'keystroke_telemetry' : null
    ]);
}

function capabilities_unlock(array $kp, object $rings): void {
    $data = json_input();
    $capability = $data['capability'] ?? '';
    
    if (!$capability) {
        json_error(400, 'Missing capability name');
    }
    
    // Verify user has prerequisites
    $peers = $rings->getAllPeers();
    $ring_size = count($peers);
    
    $allowed = match ($capability) {
        'keystroke_telemetry' => $ring_size >= 3,
        'spam_folder' => has_phantom_user($peers, 'spam_trainer'),
        'gig_decoder' => $ring_size >= 5,
        'canary_composer' => has_phantom_user($peers, 'canary_witness'),
        default => false
    };
    
    if (!$allowed) {
        json_error(403, 'Prerequisites not met for this capability');
    }
    
    json_out(['capability' => $capability, 'unlocked' => true]);
}

function has_phantom_user(array $peers, string $name): bool {
    foreach ($peers as $peer) {
        if (($peer['display_name'] ?? '') === $name) {
            return true;
        }
    }
    return false;
}
