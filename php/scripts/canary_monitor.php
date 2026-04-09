#!/usr/bin/env php
<?php
/**
 * Canary Heartbeat Monitor - Cron Job
 * Run this every hour to check for missed heartbeats
 * 
 * Add to crontab:
 * 0 * * * * /path/to/osnova/php/scripts/canary_monitor.php
 */

require_once __DIR__ . '/../config.php';
require_once __DIR__ . '/../lib/canary_extended.php';

$kp = crypto_load_keypair(IDENTITY_KEY_FILE);
$canarySystem = new CanarySystemExtended(DATA_DIR . '/canary.db', $kp['public']);

echo "[" . date('Y-m-d H:i:s') . "] Checking for missed heartbeats...\n";

$triggered = $canarySystem->checkMissedHeartbeats();

if (empty($triggered)) {
    echo "No canaries triggered.\n";
} else {
    echo "ALERT: " . count($triggered) . " canaries triggered:\n";
    foreach ($triggered as $canary_id) {
        echo "  - {$canary_id}\n";
        
        // Attempt reconstruction and broadcast
        $result = $canarySystem->reconstructMessage($canary_id);
        if ($result['status'] === 'complete') {
            echo "    ✅ Message reconstructed (" . strlen($result['message']) . " bytes)\n";
            echo "    📡 Broadcasting to network...\n";
            
            // In production, this would trigger gossip protocol broadcast
            // For now, just log it
            @mkdir(DATA_DIR . '/canary_releases', 0700, true);
            file_put_contents(
                DATA_DIR . "/canary_releases/{$canary_id}.txt",
                $result['message']
            );
        } else {
            echo "    ⚠️ Incomplete: {$result['available']}/{$result['required']} fragments\n";
        }
    }
}

echo "Done.\n";
