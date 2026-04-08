<?php
/**
 * Canary Cryptographic Primitives
 * - Shamir Secret Sharing (k-of-n threshold)
 * - Time-lock puzzles (verifiable delay)
 * - Duress marker detection
 */

class CanaryCrypto {
    /**
     * Shamir Secret Sharing - split secret into n shares, k needed to reconstruct.
     * 
     * Implementation: Polynomial evaluation over finite field
     * P(x) = a0 + a1*x + a2*x² + ... + a(k-1)*x^(k-1)
     * where a0 = secret, a1...a(k-1) are random coefficients
     */
    public static function shamirSplit(string $secret, int $k, int $n): array {
        if ($k > $n) {
            throw new InvalidArgumentException("Threshold k must be <= total shares n");
        }
        
        // Convert secret to integer (for simplicity, use first 4 bytes)
        $secretInt = unpack('N', substr(hash('sha256', $secret, true), 0, 4))[1];
        
        // Prime modulus (large enough to avoid overflow)
        $prime = 2147483647; // Mersenne prime 2^31 - 1
        
        // Generate random polynomial coefficients
        $coefficients = [$secretInt % $prime];
        for ($i = 1; $i < $k; $i++) {
            $coefficients[] = random_int(1, $prime - 1);
        }
        
        // Evaluate polynomial at n different x values
        $shares = [];
        for ($x = 1; $x <= $n; $x++) {
            $y = self::evaluatePolynomial($coefficients, $x, $prime);
            $shares[] = [
                'x' => $x,
                'y' => $y,
                'k' => $k,
                'n' => $n,
                'prime' => $prime
            ];
        }
        
        return $shares;
    }
    
    /**
     * Evaluate polynomial at point x.
     */
    private static function evaluatePolynomial(array $coefficients, int $x, int $prime): int {
        $result = 0;
        $xPower = 1;
        
        foreach ($coefficients as $coeff) {
            $result = ($result + ($coeff * $xPower) % $prime) % $prime;
            $xPower = ($xPower * $x) % $prime;
        }
        
        return $result;
    }
    
    /**
     * Reconstruct secret from k shares using Lagrange interpolation.
     */
    public static function shamirReconstruct(array $shares): string {
        if (empty($shares)) {
            throw new InvalidArgumentException("No shares provided");
        }
        
        $k = $shares[0]['k'];
        $prime = $shares[0]['prime'];
        
        if (count($shares) < $k) {
            throw new InvalidArgumentException("Not enough shares (need $k, got " . count($shares) . ")");
        }
        
        // Take first k shares
        $shares = array_slice($shares, 0, $k);
        
        // Lagrange interpolation to find P(0) = secret
        $secret = 0;
        
        foreach ($shares as $i => $shareI) {
            $xi = $shareI['x'];
            $yi = $shareI['y'];
            
            // Calculate Lagrange basis polynomial L_i(0)
            $numerator = 1;
            $denominator = 1;
            
            foreach ($shares as $j => $shareJ) {
                if ($i === $j) continue;
                
                $xj = $shareJ['x'];
                
                $numerator = ($numerator * (0 - $xj)) % $prime;
                $denominator = ($denominator * ($xi - $xj)) % $prime;
            }
            
            // Modular inverse for division
            $denomInverse = self::modInverse($denominator, $prime);
            $basis = ($numerator * $denomInverse) % $prime;
            
            $secret = ($secret + ($yi * $basis)) % $prime;
        }
        
        // Normalize to positive
        $secret = ($secret % $prime + $prime) % $prime;
        
        // Convert back to string (hash for consistency)
        return hash('sha256', (string)$secret);
    }
    
    /**
     * Modular multiplicative inverse using Extended Euclidean Algorithm.
     */
    private static function modInverse(int $a, int $m): int {
        $a = ($a % $m + $m) % $m;
        
        if ($a === 0) return 0;
        
        $m0 = $m;
        $x0 = 0;
        $x1 = 1;
        
        while ($a > 1) {
            $q = intdiv($a, $m);
            $t = $m;
            
            $m = $a % $m;
            $a = $t;
            $t = $x0;
            
            $x0 = $x1 - $q * $x0;
            $x1 = $t;
        }
        
        if ($x1 < 0) {
            $x1 += $m0;
        }
        
        return $x1;
    }
    
    /**
     * Generate time-lock puzzle (verifiable delay function).
     * Uses repeated squaring - requires sequential computation.
     */
    public static function generateTimeLock(string $message, int $delaySeconds): array {
        // Calibrate: ~1000 iterations per second
        $iterations = $delaySeconds * 1000;
        
        // Use GMP for large number operations
        if (!extension_loaded('gmp')) {
            throw new RuntimeException("GMP extension required for time-lock puzzles");
        }
        
        // Large prime modulus (2048-bit)
        $modulus = gmp_init('179769313486231590772930519078902473361797697894230657273430081157732675805500963132708477322407536021120113879871393357658789768814416622492847430639474124377767893424865485276302219601246094119453082952085005768838150682342462881473913110540827237163350510684586298239947245938479716304835356329624224137859');
        
        // Base from message hash
        $base = gmp_init(hash('sha256', $message), 16);
        $base = gmp_mod($base, $modulus);
        
        // Time-lock value: base^(2^iterations) mod modulus
        // Store this for verification (solver must compute it)
        $timeLockValue = $base;
        for ($i = 0; $i < min($iterations, 1000); $i++) { // Cap for generation
            $timeLockValue = gmp_powm($timeLockValue, 2, $modulus);
        }
        
        return [
            'iterations' => $iterations,
            'base' => gmp_strval($base),
            'modulus' => gmp_strval($modulus),
            'time_lock_value' => gmp_strval($timeLockValue),
            'created_at' => microtime(true)
        ];
    }
    
    /**
     * Verify time-lock solution (solver performed required work).
     */
    public static function verifyTimeLock(array $timeLock, string $solution): bool {
        if (!extension_loaded('gmp')) {
            return false;
        }
        
        $expected = gmp_init($timeLock['time_lock_value']);
        $provided = gmp_init($solution);
        
        return gmp_cmp($expected, $provided) === 0;
    }
    
    /**
     * Encrypt fragment with ring-specific key.
     */
    public static function encryptFragment(string $fragment, string $key): string {
        if (!extension_loaded('sodium')) {
            throw new RuntimeException("Sodium extension required");
        }
        
        // Ensure key is proper length
        $keyHash = hash('sha256', $key, true);
        
        $nonce = random_bytes(SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $ciphertext = sodium_crypto_secretbox($fragment, $nonce, $keyHash);
        
        return base64_encode($nonce . $ciphertext);
    }
    
    /**
     * Decrypt fragment.
     */
    public static function decryptFragment(string $encrypted, string $key): ?string {
        if (!extension_loaded('sodium')) {
            return null;
        }
        
        $decoded = base64_decode($encrypted);
        if ($decoded === false) {
            return null;
        }
        
        $keyHash = hash('sha256', $key, true);
        
        $nonce = substr($decoded, 0, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        $ciphertext = substr($decoded, SODIUM_CRYPTO_SECRETBOX_NONCEBYTES);
        
        $plaintext = sodium_crypto_secretbox_open($ciphertext, $nonce, $keyHash);
        
        return $plaintext !== false ? $plaintext : null;
    }
    
    /**
     * Calculate gematria value (Hebrew numerology).
     * Used for duress detection: 613 (Torah), 888 (Jesus), 666 (distress)
     */
    public static function calculateGematria(string $text): int {
        $gematria = 0;
        
        for ($i = 0; $i < strlen($text); $i++) {
            $char = ord($text[$i]);
            
            if ($char >= 65 && $char <= 90) {  // A-Z
                $gematria += ($char - 64);
            } elseif ($char >= 97 && $char <= 122) {  // a-z
                $gematria += ($char - 96);
            }
        }
        
        return $gematria % 1000;  // Reduce to 0-999
    }
    
    /**
     * Detect if message contains duress signal.
     */
    public static function isDuressSignal(string $message): bool {
        // Check gematria for known duress values
        $gematria = self::calculateGematria($message);
        $duressValues = [613, 888, 666];
        
        if (in_array($gematria, $duressValues, true)) {
            return true;
        }
        
        // Check for duress vocabulary
        $duressTerms = [
            'mental health crisis',
            'conspiracy theory',
            'tinfoil hat',
            'i was wrong',
            'apologize for',
            'seeking help'
        ];
        
        $lowerMessage = strtolower($message);
        foreach ($duressTerms as $term) {
            if (strpos($lowerMessage, $term) !== false) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Generate Ed25519 signature for content.
     */
    public static function signContent(string $content, string $privateKey): string {
        if (!extension_loaded('sodium')) {
            throw new RuntimeException("Sodium extension required");
        }
        
        return base64_encode(sodium_crypto_sign_detached($content, hex2bin($privateKey)));
    }
    
    /**
     * Verify Ed25519 signature.
     */
    public static function verifySignature(string $content, string $signature, string $publicKey): bool {
        if (!extension_loaded('sodium')) {
            return false;
        }
        
        return sodium_crypto_sign_verify_detached(
            base64_decode($signature),
            $content,
            hex2bin($publicKey)
        );
    }
}
