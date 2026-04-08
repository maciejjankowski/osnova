<?php
/**
 * Signals API
 * POST /api/signals/canary   - broadcast canary (node compromised)
 * POST /api/signals/eject    - eject from network
 * POST /api/signals/receive  - receive inbound canary or eject signal
 */

function api_signals_handler(
    string      $method,
    array       $segments,
    array       $kp,
    ContentLog  $log,
    RingManager $rings,
    SignalStore  $sigStore
): void {
    $action = $segments[2] ?? '';

    if ($action === 'canary' && $method === 'POST') {
        api_signals_canary($kp, $rings, $sigStore);
        return;
    }
    if ($action === 'eject' && $method === 'POST') {
        api_signals_eject($kp, $log, $rings, $sigStore);
        return;
    }
    if ($action === 'receive' && $method === 'POST') {
        api_signals_receive($sigStore);
        return;
    }
    json_error(404, 'Unknown signal endpoint');
}

function api_signals_canary(array $kp, RingManager $rings, SignalStore $sigStore): void {
    $body     = json_input();
    $message  = $body['message']  ?? '';
    $severity = $body['severity'] ?? 'critical';

    $eject    = new EjectProtocol($kp['public']);
    $signal   = $eject->broadcastCanary($rings, $kp, $message);
    $signal['severity'] = $severity;

    // Store our own canary (for record)
    $sigStore->store($signal);

    json_out($signal);
}

function api_signals_eject(array $kp, ContentLog $log, RingManager $rings, SignalStore $sigStore): void {
    $body            = json_input();
    $closingMessage  = $body['closing_message']  ?? '';
    $includeProvenance = (bool)($body['include_provenance'] ?? true);

    $eject   = new EjectProtocol($kp['public']);
    $package = $eject->packageContent($log, $rings, $kp, $closingMessage, $includeProvenance);
    $eject->broadcastEject($package, $rings, $kp);

    $peers = $rings->getSyncPeers();

    json_out([
        'ejected'           => true,
        'author_key'        => $kp['public'],
        'entries_packaged'  => count($package['content_entries']),
        'peers_notified'    => count($peers),
        'timestamp'         => $package['timestamp'],
        'package_signature' => $package['signature'],
    ]);
}

function api_signals_receive(SignalStore $sigStore): void {
    $signal = json_input();

    $required = ['signal_type', 'author_key', 'timestamp', 'signature'];
    foreach ($required as $f) {
        if (!isset($signal[$f])) {
            json_error(422, "Field '{$f}' is required");
            return;
        }
    }

    // Verify signature
    $eject  = new EjectProtocol();
    $result = $eject->handleReceivedSignal($signal);

    if ($result === 'invalid_signature') {
        json_error(400, 'Invalid signature');
        return;
    }

    // Store it
    $sigStore->store($signal);

    json_out(['accepted' => true, 'signal_type' => $signal['signal_type']]);
}
