<?php
/**
 * Osnova Node Configuration
 * Edit DISPLAY_NAME before first run.
 */

define('NODE_DISPLAY_NAME', getenv('OSNOVA_NAME') ?: 'Osnova Node');
define('NODE_HOST',          getenv('OSNOVA_HOST') ?: 'https://va.evil1.org');
define('DATA_DIR',           __DIR__ . '/data');
define('IDENTITY_KEY_FILE',  DATA_DIR . '/identity.key');
define('CONTENT_DB',         DATA_DIR . '/content.db');
define('PEERS_DB',           DATA_DIR . '/peers.db');
define('SIGNALS_DB',         DATA_DIR . '/signals.db');
define('GOSSIP_INTERVAL',    30);  // seconds (used only by CLI cron, not web)
// Dunbar ring capacity caps (same as Python)
define('RING_CAPS', [
    'core'   => 5,
    'inner'  => 15,
    'middle' => 50,
    'outer'  => 95,
]);

// ---------------------------------------------------------------------------
// Bootstrap: ensure data dir and keypair exist on first run
// ---------------------------------------------------------------------------
if (!is_dir(DATA_DIR)) {
    mkdir(DATA_DIR, 0700, true);
}

// Autoload libs
require_once __DIR__ . '/lib/crypto.php';
require_once __DIR__ . '/lib/storage.php';
require_once __DIR__ . '/lib/rings.php';
require_once __DIR__ . '/lib/gossip.php';
require_once __DIR__ . '/lib/eject.php';
require_once __DIR__ . '/lib/discovery.php';
require_once __DIR__ . '/lib/gig_store.php';

// Ensure keypair exists
if (!file_exists(IDENTITY_KEY_FILE)) {
    $kp = crypto_generate_keypair();
    crypto_save_keypair($kp, IDENTITY_KEY_FILE);
}
