<?php
/**
 * Ed25519 crypto via PHP sodium extension.
 *
 * Key storage format: hex-encoded.
 * Signing key (secret): first 64 hex chars of the 32-byte seed.
 * Verify key (public):  last 64 hex chars (32 bytes).
 *
 * We store only the 32-byte seed (signing seed) in the key file,
 * matching what Python nacl SigningKey stores (the seed, not the full keypair).
 * sodium_crypto_sign_SECRETKEYBYTES = 64 bytes = seed || public key concatenated.
 */

/**
 * Returns ['secret' => hex64bytes, 'public' => hex32bytes]
 * secret = the full 64-byte sodium secret key (seed||pk), hex-encoded
 * public = the 32-byte public key, hex-encoded
 */
function crypto_generate_keypair(): array {
    $kp = sodium_crypto_sign_keypair();
    $sk = sodium_crypto_sign_secretkey($kp);  // 64 bytes
    $pk = sodium_crypto_sign_publickey($kp);  // 32 bytes
    return [
        'secret' => bin2hex($sk),
        'public' => bin2hex($pk),
    ];
}

/**
 * Save keypair to file (0600 perms).
 * Stores only the 32-byte seed (first 32 bytes of the secret key) as hex,
 * matching the Python nacl format (SigningKey stores the seed).
 */
function crypto_save_keypair(array $kp, string $path): void {
    // Store the full secret key hex so we can reconstruct everything
    file_put_contents($path, $kp['secret']);
    chmod($path, 0600);
}

/**
 * Load keypair from file.
 * Returns ['secret' => hex64bytes, 'public' => hex32bytes]
 */
function crypto_load_keypair(string $path): array {
    $hex = trim(file_get_contents($path));
    // Could be 64-byte full secret (128 hex chars) or 32-byte seed (64 hex chars)
    if (strlen($hex) === 64) {
        // It's a 32-byte seed - derive full secret key
        $seed = hex2bin($hex);
        $kp = sodium_crypto_sign_seed_keypair($seed);
        $sk = sodium_crypto_sign_secretkey($kp);
        $pk = sodium_crypto_sign_publickey($kp);
        return [
            'secret' => bin2hex($sk),
            'public' => bin2hex($pk),
        ];
    }
    // It's the full 128-hex secret key
    $sk = hex2bin($hex);
    $pk = sodium_crypto_sign_publickey_from_secretkey($sk);
    return [
        'secret' => $hex,
        'public' => bin2hex($pk),
    ];
}

/**
 * Format a float timestamp exactly as Python's str(float) does.
 * Python's time.time() gives up to ~6 decimal places (microseconds).
 * We round to 6 decimals and strip trailing zeros, keeping at least ".0".
 * This ensures PHP and Python produce identical content_hash values.
 */
function py_float_str(float $f): string {
    $rounded = round($f, 6);
    $s = number_format($rounded, 6, '.', '');
    $s = rtrim($s, '0');
    if (substr($s, -1) === '.') $s .= '0';
    return $s;
}

/**
 * Compute the deterministic content hash (mirrors Python ContentEntry.content_hash).
 * payload = "{author_key}:{content_type}:{body}:{parent_hash}:{timestamp}"
 * parent_hash is the string "None" when null (matching Python str(None))
 * timestamp is formatted as Python's str(float): rounded to 6 decimals, no trailing zeros
 */
function crypto_content_hash(
    string $author_key,
    string $content_type,
    string $body,
    ?string $parent_hash,
    float $timestamp
): string {
    $ph = ($parent_hash === null) ? 'None' : $parent_hash;
    $ts_str = py_float_str($timestamp);
    $payload = "{$author_key}:{$content_type}:{$body}:{$ph}:{$ts_str}";
    return hash('sha256', $payload);
}

/**
 * Sign the content_hash with the secret key.
 * Returns hex-encoded detached signature (64 bytes = 128 hex chars).
 */
function crypto_sign_content_hash(string $content_hash, array $kp): string {
    $sk = hex2bin($kp['secret']);
    $sig = sodium_crypto_sign_detached($content_hash, $sk);
    return bin2hex($sig);
}

/**
 * Verify a detached signature over the content_hash.
 */
function crypto_verify_content(
    string $content_hash,
    string $author_key_hex,
    string $signature_hex
): bool {
    if (empty($signature_hex) || empty($author_key_hex)) {
        return false;
    }
    try {
        $pk  = hex2bin($author_key_hex);
        $sig = hex2bin($signature_hex);
        return sodium_crypto_sign_verify_detached($sig, $content_hash, $pk);
    } catch (\Throwable) {
        return false;
    }
}

/**
 * Sign arbitrary bytes. Returns hex signature.
 */
function crypto_sign_bytes(string $payload, array $kp): string {
    $sk = hex2bin($kp['secret']);
    $sig = sodium_crypto_sign_detached($payload, $sk);
    return bin2hex($sig);
}

/**
 * Verify arbitrary bytes signature.
 */
function crypto_verify_bytes(string $payload, string $author_key_hex, string $signature_hex): bool {
    if (empty($signature_hex) || empty($author_key_hex)) {
        return false;
    }
    try {
        $pk  = hex2bin($author_key_hex);
        $sig = hex2bin($signature_hex);
        return sodium_crypto_sign_verify_detached($sig, $payload, $pk);
    } catch (\Throwable) {
        return false;
    }
}

/**
 * Get node identity array.
 */
function crypto_get_identity(array $kp, string $display_name): array {
    return [
        'public_key'   => $kp['public'],
        'display_name' => $display_name,
        'created_at'   => microtime(true),
    ];
}
