#!/usr/bin/env php
<?php
/**
 * Osnova API test suite - no phpunit required.
 * Run: php tests/test_all.php [base_url]
 *
 * Usage:
 *   php tests/test_all.php                        # defaults to https://va.evil1.org
 *   php tests/test_all.php http://localhost:8080
 */

declare(strict_types=1);

$base = rtrim($argv[1] ?? 'https://va.evil1.org', '/');

// ---------------------------------------------------------------------------
// Crypto helpers (mirrors lib/crypto.php + osnova.js logic)
// ---------------------------------------------------------------------------

require_once __DIR__ . '/../lib/crypto.php';

/**
 * Generate a fresh Ed25519 keypair using PHP sodium.
 * Returns ['secret' => hex128, 'public' => hex64]
 */
function test_generate_keypair(): array {
    $kp = sodium_crypto_sign_keypair();
    return [
        'secret' => bin2hex(sodium_crypto_sign_secretkey($kp)),
        'public' => bin2hex(sodium_crypto_sign_publickey($kp)),
    ];
}

/**
 * Build a client-signed entry (matches what osnova.js produces).
 */
function test_make_signed_entry(array $kp, string $body, string $content_type = 'post', ?string $parent_hash = null, array $metadata = []): array {
    $timestamp = microtime(true);
    $hash      = crypto_content_hash($kp['public'], $content_type, $body, $parent_hash, $timestamp);
    $sig       = crypto_sign_content_hash($hash, $kp);
    return [
        'author_key'   => $kp['public'],
        'content_type' => $content_type,
        'body'         => $body,
        'parent_hash'  => $parent_hash,
        'metadata'     => $metadata,
        'timestamp'    => $timestamp,
        'signature'    => $sig,
        'content_hash' => $hash,
    ];
}

// ---------------------------------------------------------------------------
// Test harness
// ---------------------------------------------------------------------------

$pass = 0;
$fail = 0;

function test(string $name, callable $fn): void {
    global $pass, $fail;
    try {
        $fn();
        echo "\033[32mPASS\033[0m: {$name}\n";
        $pass++;
    } catch (\Throwable $e) {
        echo "\033[31mFAIL\033[0m: {$name} - {$e->getMessage()}\n";
        $fail++;
    }
}

function assert_eq(mixed $a, mixed $b, string $msg = ''): void {
    if ($a !== $b) {
        throw new \Exception(($msg ? $msg . ': ' : '') . 'expected ' . var_export($b, true) . ' got ' . var_export($a, true));
    }
}

function assert_true(mixed $v, string $msg = ''): void {
    if (!$v) throw new \Exception($msg ?: 'Expected true, got false');
}

function assert_false(mixed $v, string $msg = ''): void {
    if ($v) throw new \Exception($msg ?: 'Expected false, got true');
}

// ---------------------------------------------------------------------------
// HTTP helper
// ---------------------------------------------------------------------------

function http(string $method, string $url, mixed $body = null, array $headers = []): array {
    if (!function_exists('curl_init')) {
        throw new \RuntimeException('curl not available');
    }
    $ch = curl_init($url);
    $defaultHeaders = ['Accept: application/json'];
    if ($body !== null) {
        $json = is_string($body) ? $body : json_encode($body);
        curl_setopt($ch, CURLOPT_POSTFIELDS, $json);
        $defaultHeaders[] = 'Content-Type: application/json';
    }
    curl_setopt_array($ch, [
        CURLOPT_CUSTOMREQUEST  => $method,
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT        => 15,
        CURLOPT_FOLLOWLOCATION => false,
        CURLOPT_SSL_VERIFYPEER => false, // for local dev
        CURLOPT_HTTPHEADER     => array_merge($defaultHeaders, $headers),
    ]);
    $resp = curl_exec($ch);
    $code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $err  = curl_error($ch);
    curl_close($ch);
    if ($resp === false) throw new \RuntimeException("curl error: $err");
    $data = json_decode($resp, true);
    return ['status' => $code, 'body' => $data, 'raw' => $resp];
}

function GET(string $path): array    { global $base; return http('GET',    $base . $path); }
function POST(string $path, mixed $body = null): array { global $base; return http('POST', $base . $path, $body); }

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

echo "Testing: {$base}\n\n";

// 1. GET /api/identity
test('GET /api/identity returns 200 with public_key', function() {
    $r = GET('/api/identity');
    assert_eq($r['status'], 200, 'status');
    assert_true(isset($r['body']['public_key']), 'has public_key');
    assert_true(strlen($r['body']['public_key']) === 64, 'public_key is 32 bytes hex');
});

// 2. POST /api/posts (server-signed, for node-to-node use)
$server_post_hash = null;
test('POST /api/posts creates a server-signed post', function() use (&$server_post_hash) {
    $r = POST('/api/posts', ['body' => 'Server-signed test post ' . time()]);
    assert_eq($r['status'], 200, 'status');
    assert_true(isset($r['body']['content_hash']), 'has content_hash');
    assert_true(isset($r['body']['signature']),    'has signature');
    assert_true(isset($r['body']['author_key']),   'has author_key');
    assert_eq($r['body']['content_type'], 'post',  'content_type is post');
    $server_post_hash = $r['body']['content_hash'];
});

// 3. POST /api/posts/signed with a valid client-signed entry
$client_kp        = test_generate_keypair();
$client_post_hash = null;
test('POST /api/posts/signed accepts a valid client-signed entry', function() use ($client_kp, &$client_post_hash) {
    $entry = test_make_signed_entry($client_kp, 'Client-signed test post ' . time());
    $r     = POST('/api/posts/signed', $entry);
    assert_eq($r['status'], 200, 'status');
    assert_true(isset($r['body']['content_hash']), 'has content_hash');
    assert_eq($r['body']['author_key'], $client_kp['public'], 'author_key matches client pubkey');
    $client_post_hash = $r['body']['content_hash'];
});

// 4. POST /api/posts/signed with a BAD signature is rejected (403)
test('POST /api/posts/signed with bad signature returns 403', function() use ($client_kp) {
    $entry = test_make_signed_entry($client_kp, 'Bad sig test ' . time());
    // Corrupt the signature
    $entry['signature'] = str_repeat('00', 64); // 64 zero bytes
    $r = POST('/api/posts/signed', $entry);
    assert_eq($r['status'], 403, 'status should be 403');
    assert_true(isset($r['body']['detail']), 'has detail');
});

// 5. POST /api/posts/signed with wrong content_hash is rejected (400)
test('POST /api/posts/signed with mismatched content_hash returns 400', function() use ($client_kp) {
    $entry = test_make_signed_entry($client_kp, 'Hash mismatch test ' . time());
    $entry['content_hash'] = str_repeat('ab', 32); // wrong hash
    $r = POST('/api/posts/signed', $entry);
    assert_eq($r['status'], 400, 'status should be 400');
});

// 6. POST /api/posts/signed with empty body returns 422
test('POST /api/posts/signed with empty body returns 422', function() use ($client_kp) {
    $entry = test_make_signed_entry($client_kp, '');
    $r     = POST('/api/posts/signed', $entry);
    assert_eq($r['status'], 422, 'status should be 422');
});

// 7. POST /api/posts/signed with missing required field returns 422
test('POST /api/posts/signed with missing author_key returns 422', function() use ($client_kp) {
    $entry = test_make_signed_entry($client_kp, 'Missing field test ' . time());
    unset($entry['author_key']);
    $r = POST('/api/posts/signed', $entry);
    assert_eq($r['status'], 422, 'status should be 422');
});

// 8. GET /api/posts returns the feed
test('GET /api/posts returns feed array', function() {
    $r = GET('/api/posts');
    assert_eq($r['status'], 200, 'status');
    assert_true(is_array($r['body']), 'body is array');
});

// 9. GET /api/posts/{hash} returns the client-signed post we created
test('GET /api/posts/{hash} returns specific post', function() use (&$client_post_hash) {
    if (!$client_post_hash) throw new \Exception('No client_post_hash from earlier test');
    $r = GET('/api/posts/' . $client_post_hash);
    assert_eq($r['status'], 200, 'status');
    assert_eq($r['body']['content_hash'], $client_post_hash, 'content_hash matches');
});

// 10. GET /api/posts/{hash} for non-existent hash returns 404
test('GET /api/posts/{nonexistent} returns 404', function() {
    $r = GET('/api/posts/' . str_repeat('00', 32));
    assert_eq($r['status'], 404, 'status');
});

// 11. POST /api/posts/{hash}/comment creates a comment (server-signed)
$comment_hash = null;
test('POST /api/posts/{hash}/comment creates a comment', function() use (&$server_post_hash, &$comment_hash) {
    if (!$server_post_hash) throw new \Exception('No server_post_hash from earlier test');
    $r = POST('/api/posts/' . $server_post_hash . '/comment', ['body' => 'Test comment ' . time()]);
    assert_eq($r['status'], 200, 'status');
    assert_eq($r['body']['content_type'], 'comment', 'content_type is comment');
    assert_eq($r['body']['parent_hash'],  $server_post_hash, 'parent_hash matches');
    $comment_hash = $r['body']['content_hash'];
});

// 12. Client-signed comment via /api/posts/signed
test('POST /api/posts/signed accepts a client-signed comment', function() use ($client_kp, $server_post_hash) {
    if (!$server_post_hash) throw new \Exception('No server_post_hash');
    $entry = test_make_signed_entry($client_kp, 'Client comment ' . time(), 'comment', $server_post_hash);
    $r     = POST('/api/posts/signed', $entry);
    assert_eq($r['status'], 200, 'status');
    assert_eq($r['body']['content_type'], 'comment', 'content_type is comment');
    assert_eq($r['body']['parent_hash'], $server_post_hash, 'parent_hash matches');
});

// 13. GET /api/posts/{hash}/comments returns comments
test('GET /api/posts/{hash}/comments returns comments array', function() use (&$server_post_hash) {
    if (!$server_post_hash) throw new \Exception('No server_post_hash');
    $r = GET('/api/posts/' . $server_post_hash . '/comments');
    assert_eq($r['status'], 200, 'status');
    assert_true(is_array($r['body']), 'body is array');
    assert_true(count($r['body']) >= 1, 'at least 1 comment');
});

// 14. GET /api/rings returns ring stats
test('GET /api/rings returns ring stats', function() {
    $r = GET('/api/rings');
    assert_eq($r['status'], 200, 'status');
    assert_true(isset($r['body']['total']), 'has total');
});

// 15. POST /api/sync returns a valid sync response
test('POST /api/sync returns entries array', function() {
    $r = POST('/api/sync', [
        'requester_key'   => str_repeat('ab', 32),
        'known_hashes'    => [],
        'since_timestamp' => 0.0,
        'max_entries'     => 5,
    ]);
    assert_eq($r['status'], 200, 'status');
    assert_true(isset($r['body']['entries']), 'has entries');
    assert_true(is_array($r['body']['entries']), 'entries is array');
    assert_true(isset($r['body']['peer_key']), 'has peer_key');
});

// 16. py_float_str compatibility check
test('crypto_content_hash is consistent for same inputs', function() use ($client_kp) {
    $ts = 1712345678.123456;
    $h1 = crypto_content_hash($client_kp['public'], 'post', 'hello world', null, $ts);
    $h2 = crypto_content_hash($client_kp['public'], 'post', 'hello world', null, $ts);
    assert_eq($h1, $h2, 'same hash for same inputs');
    assert_true(strlen($h1) === 64, 'hash is 64 hex chars (sha256)');
});

// 17. py_float_str known values
test('py_float_str produces expected Python-compatible strings', function() {
    $cases = [
        [1712345678.0,      '1712345678.0'],
        [1712345678.1,      '1712345678.1'],
        [1712345678.123456, '1712345678.123456'],
        [1712345678.100000, '1712345678.1'],
        [1712345678.123400, '1712345678.1234'],
        [0.0,               '0.0'],
        [1.0,               '1.0'],
    ];
    foreach ($cases as [$input, $expected]) {
        $got = py_float_str($input);
        if ($got !== $expected) {
            throw new \Exception("py_float_str({$input}): expected '{$expected}' got '{$got}'");
        }
    }
});

// ---------------------------------------------------------------------------
// Summary
// ---------------------------------------------------------------------------
echo "\n" . str_repeat('-', 40) . "\n";
echo "Results: \033[32m{$pass} passed\033[0m, ";
if ($fail > 0) {
    echo "\033[31m{$fail} failed\033[0m\n";
    exit(1);
} else {
    echo "0 failed\n";
    exit(0);
}
