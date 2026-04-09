<?php
/**
 * Gig Marketplace API
 * Handles posting, browsing, and managing gigs
 */

function api_gigs_handler(string $method, array $segments, array $kp, object $log, object $rings): void {
    global $gigStore;
    
    if (!isset($gigStore)) {
        $gigStore = new GigStore(DATA_DIR . '/gigs.db');
    }
    
    $action = $segments[2] ?? 'list';
    
    match ($action) {
        'list' => match ($method) {
            'GET' => gigs_list($gigStore, $rings),
            default => json_error(405, 'Method not allowed')
        },
        
        'post' => match ($method) {
            'POST' => gigs_post($gigStore, $kp, $log),
            default => json_error(405, 'Method not allowed')
        },
        
        'get' => match ($method) {
            'GET' => gigs_get($gigStore, $segments[3] ?? ''),
            default => json_error(405, 'Method not allowed')
        },
        
        'complete' => match ($method) {
            'POST' => gigs_complete($gigStore, $kp, $segments[3] ?? ''),
            default => json_error(405, 'Method not allowed')
        },
        
        default => json_error(404, "Unknown gig action: {$action}")
    };
}

function gigs_list(object $store, object $rings): void {
    $limit = (int)($_GET['limit'] ?? 20);
    $offset = (int)($_GET['offset'] ?? 0);
    $ring = $_GET['ring'] ?? null;
    
    $gigs = $store->listGigs($limit, $offset, $ring);
    
    json_out(['gigs' => $gigs, 'count' => count($gigs)]);
}

function gigs_post(object $store, array $kp, object $log): void {
    $data = json_input();
    
    $required = ['title', 'description', 'price', 'ring_visibility'];
    foreach ($required as $field) {
        if (!isset($data[$field])) {
            json_error(400, "Missing field: {$field}");
        }
    }
    
    $gig = [
        'gig_id' => bin2hex(random_bytes(16)),
        'author_key' => $kp['public'],
        'title' => $data['title'],
        'description' => $data['description'],
        'price' => (float)$data['price'],
        'location' => $data['location'] ?? '',
        'deadline' => $data['deadline'] ?? null,
        'ring_visibility' => (int)$data['ring_visibility'],
        'status' => 'open',
        'created_at' => microtime(true),
    ];
    
    $store->createGig($gig);
    
    // Also log as content for replication
    $content = [
        'type' => 'gig',
        'data' => $gig,
    ];
    $log->append($kp['public'], $content, $kp['private']);
    
    json_out(['gig' => $gig], 201);
}

function gigs_get(object $store, string $gig_id): void {
    if (!$gig_id) {
        json_error(400, 'Missing gig_id');
    }
    
    $gig = $store->getGig($gig_id);
    
    if (!$gig) {
        json_error(404, 'Gig not found');
    }
    
    json_out(['gig' => $gig]);
}

function gigs_complete(object $store, array $kp, string $gig_id): void {
    if (!$gig_id) {
        json_error(400, 'Missing gig_id');
    }
    
    $data = json_input();
    $completer_key = $data['completer_key'] ?? $kp['public'];
    
    $result = $store->markComplete($gig_id, $completer_key);
    
    if (!$result) {
        json_error(404, 'Gig not found or already completed');
    }
    
    json_out(['status' => 'completed', 'gig_id' => $gig_id]);
}
