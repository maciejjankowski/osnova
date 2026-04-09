<?php
/**
 * Osnova PHP - Main Router
 * All requests pass through here via .htaccess rewrite.
 *
 * Identity model: client-side (Ed25519 keypair in browser localStorage).
 * Server nodes are dispatchers - they store and relay signed content.
 * No user accounts, no sessions, no login/register.
 */

declare(strict_types=1);

require_once __DIR__ . '/config.php';

// ---------------------------------------------------------------------------
// API handlers
// ---------------------------------------------------------------------------
require_once __DIR__ . '/api/posts.php';
require_once __DIR__ . '/api/rings.php';
require_once __DIR__ . '/api/sync.php';
require_once __DIR__ . '/api/identity.php';
require_once __DIR__ . '/api/signals.php';
require_once __DIR__ . '/api/discovery.php';
require_once __DIR__ . '/api/gigs.php';

// ---------------------------------------------------------------------------
// Shared helper functions
// ---------------------------------------------------------------------------

function json_out(mixed $data, int $status = 200): void {
    http_response_code($status);
    header('Content-Type: application/json');
    echo json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
    exit;
}

function json_error(int $status, string $detail): void {
    json_out(['detail' => $detail], $status);
}

function json_input(): array {
    $raw = file_get_contents('php://input');
    if (!$raw) return [];
    $data = json_decode($raw, true);
    return is_array($data) ? $data : [];
}

// ---------------------------------------------------------------------------
// Parse request
// ---------------------------------------------------------------------------

$method = $_SERVER['REQUEST_METHOD'] ?? 'GET';
$uri    = $_SERVER['REQUEST_URI']    ?? '/';

// Strip query string
$path = strtok($uri, '?');
$path = '/' . trim($path, '/');

// Normalize: split into segments
$segments = array_filter(explode('/', trim($path, '/')), fn($s) => $s !== '');
$segments = array_values($segments);

// ---------------------------------------------------------------------------
// Initialize singletons (one DB open per request)
// ---------------------------------------------------------------------------

$kp         = crypto_load_keypair(IDENTITY_KEY_FILE);
$log        = new ContentLog(CONTENT_DB);
$rings      = new RingManager(PEERS_DB);
$gossip     = new GossipService($log, $rings, $kp['public']);
$sigStore   = new SignalStore(SIGNALS_DB);
$triadStore = $sigStore; // Triads now in same DB via SignalStore

// ---------------------------------------------------------------------------
// API routing
// ---------------------------------------------------------------------------

if (count($segments) >= 2 && $segments[0] === 'api') {
    header('Content-Type: application/json');

    $api = $segments[1] ?? '';

    match (true) {
        $api === 'posts'     => api_posts_handler($method, $segments, $kp, $log),
        $api === 'rings'     => api_rings_handler($method, $segments, $rings),
        $api === 'sync'      => api_sync_handler($method, $segments, $kp, $log, $rings, $gossip),
        $api === 'identity'  => api_identity_handler($method, $kp),
        $api === 'signals'   => api_signals_handler($method, $segments, $kp, $log, $rings, $sigStore),
        $api === 'discovery' => api_discovery_handler($method, $segments, $kp, $rings, $triadStore),
        $api === 'gigs'      => api_gigs_handler($method, $segments, $kp, $log, $rings),
        default              => json_error(404, "Unknown API endpoint: /api/{$api}"),
    };
    exit;
}

// ---------------------------------------------------------------------------
// Static files served directly by Apache - fallback just in case
// ---------------------------------------------------------------------------
if (count($segments) >= 1 && $segments[0] === 'static') {
    $file = __DIR__ . '/' . implode('/', $segments);
    if (is_file($file) && strpos(realpath($file), realpath(__DIR__ . '/static')) === 0) {
        $ext = pathinfo($file, PATHINFO_EXTENSION);
        $types = ['css' => 'text/css', 'js' => 'application/javascript', 'png' => 'image/png', 'svg' => 'image/svg+xml'];
        header('Content-Type: ' . ($types[$ext] ?? 'application/octet-stream'));
        readfile($file);
        exit;
    }
    http_response_code(404);
    exit;
}

// ---------------------------------------------------------------------------
// Feed: partial for HTMX comments lazy-load
// /feed/posts/{hash}/comments
// ---------------------------------------------------------------------------
if (count($segments) === 4 && $segments[0] === 'feed' && $segments[1] === 'posts' && $segments[3] === 'comments') {
    $parent_hash = $segments[2];
    $comments    = $log->getComments($parent_hash);
    ob_start();
    include __DIR__ . '/templates/comments_partial.php';
    echo ob_get_clean();
    exit;
}

// ---------------------------------------------------------------------------
// HTML page routing
// ---------------------------------------------------------------------------

function render_page(string $template, array $vars, string $active, string $title): void {
    extract($vars);
    ob_start();
    include __DIR__ . "/templates/{$template}.php";
    $content = ob_get_clean();
    include __DIR__ . '/templates/base.php';
}

$page = $segments[0] ?? 'feed';

// Redirect / to /welcome for first-time users, /feed for returning
if ($path === '/' || $path === '') {
    // Check if user has identity in localStorage (checked client-side)
    // For now, always redirect to welcome for proper onboarding
    header('Location: /welcome');
    exit;
}

// ---------------------------------------------------------------------------
// Main page routing
// ---------------------------------------------------------------------------

match ($page) {
    'feed' => (function() use ($log, $rings) {
        $limit  = (int)($_GET['limit']  ?? 50);
        $offset = (int)($_GET['offset'] ?? 0);
        $posts  = $log->getFeed($limit, $offset);

        // Get ring member keys for surfacing
        $ring_peers = $rings->getAllPeers();
        $ring_keys  = array_map(fn($p) => $p['public_key'], $ring_peers);

        // Surfaced posts: outside-network content that ring members engaged with
        $surfaced = [];
        $surfaced_context = [];  // content_hash => ['by' => key, 'type' => 'comment'|'reshare']
        if (!empty($ring_keys)) {
            $surfaced_raw = $log->getSurfacedPosts($ring_keys, $limit);
            foreach ($surfaced_raw as $s) {
                $ph = $s['post']['content_hash'];
                // Skip if already in direct feed
                $already_in_feed = false;
                foreach ($posts as $p) {
                    if ($p['content_hash'] === $ph) { $already_in_feed = true; break; }
                }
                if (!$already_in_feed) {
                    $surfaced[] = $s['post'];
                    $surfaced_context[$ph] = [
                        'by'   => $s['surfaced_by'],
                        'type' => $s['surface_type'],
                        'ts'   => $s['engagement_ts'],
                    ];
                }
            }
        }

        // Merge: interleave surfaced posts by engagement timestamp
        $all_posts = $posts;
        foreach ($surfaced as $sp) {
            $all_posts[] = $sp;
        }
        // Sort all by timestamp DESC
        usort($all_posts, fn($a, $b) => $b['timestamp'] <=> $a['timestamp']);

        // Build author display
        $author_names = [];
        foreach ($all_posts as $post) {
            $pk = $post['author_key'];
            if (!isset($author_names[$pk])) {
                $author_names[$pk] = substr($pk, 0, 8) . '...';
            }
        }

        render_page('feed', [
            'posts'            => $all_posts,
            'author_names'     => $author_names,
            'surfaced_context' => $surfaced_context,
        ], 'feed', 'Feed');
    })(),

    'compose' => (function() {
        render_page('compose', [], 'compose', 'Compose');
    })(),

    'setup' => (function() {
        render_page('setup', [], 'setup', 'Setup');
    })(),

    'rings' => (function() use ($rings) {
        $stats         = $rings->getRingStats();
        $peers_by_ring = [];
        foreach (['core', 'inner', 'middle', 'outer'] as $level) {
            $peers_by_ring[$level] = $rings->getPeersByRing($level);
        }
        render_page('rings', ['stats' => $stats, 'peers_by_ring' => $peers_by_ring], 'rings', 'Rings');
    })(),

    'identity' => (function() use ($kp) {
        $identity = [
            'public_key'   => $kp['public'],
            'display_name' => NODE_DISPLAY_NAME,
            'created_at'   => microtime(true),
        ];
        $endpoint = NODE_HOST;
        render_page('identity', ['identity' => $identity, 'endpoint' => $endpoint], 'identity', 'Identity');
    })(),

    'discover' => (function() use ($triadStore) {
        $all    = $triadStore->listAll();
        $triads = array_map(function($t) {
            unset($t['content_hash']);
            return $t;
        }, $all);
        render_page('discover', ['triads' => $triads], 'discover', 'Discover');
    })(),

    'eject' => (function() {
        render_page('eject', [], 'eject', 'Eject');
    })(),
    
    'welcome' => (function() {
        // Serve onboarding directly
        readfile(__DIR__ . '/templates/onboarding/welcome.php');
    })(),
    
    'gigs' => (function() use ($rings, $segments) {
        global $gigStore;
        if (!isset($gigStore)) {
            $gigStore = new GigStore(DATA_DIR . '/gigs.db');
        }
        
        // Check for /gigs/post route
        if (isset($segments[1]) && $segments[1] === 'post') {
            render_page('gigs_post', [], 'gigs', 'Post a Gig');
            return;
        }
        
        $gigs = $gigStore->listGigs(20, 0);
        render_page('gigs', ['gigs' => $gigs], 'gigs', 'Gigs');
    })(),

    default => (function() use ($path) {
        http_response_code(404);
        echo '<!doctype html><html><body><h1>404 Not Found</h1><p>' . htmlspecialchars($path) . '</p><a href="/feed">Home</a></body></html>';
    })(),
};
