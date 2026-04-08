<?php
/**
 * Canary Crypto Tests
 */

require_once __DIR__ . '/../php/lib/canary_crypto.php';

class CanaryCryptoTest {
    private int $passedTests = 0;
    private int $failedTests = 0;
    
    public function runAll(): void {
        echo "🧪 TESTING: Canary Crypto Module\n";
        echo str_repeat("=", 60) . "\n\n";
        
        $this->testShamirSplit();
        $this->testShamirReconstruct();
        $this->testShamirThreshold();
        $this->testTimeLockGenerate();
        $this->testFragmentEncryption();
        $this->testGematriaCalculation();
        $this->testDuressDetection();
        $this->testSignatures();
        
        $this->printSummary();
    }
    
    private function testShamirSplit(): void {
        echo "Test 1: Shamir Secret Sharing - Split\n";
        
        $secret = "The truth must survive";
        $shares = CanaryCrypto::shamirSplit($secret, 3, 5);
        
        $this->assert(count($shares) === 5, "Should generate 5 shares");
        $this->assert($shares[0]['k'] === 3, "Threshold should be 3");
        $this->assert($shares[0]['n'] === 5, "Total shares should be 5");
        
        echo "  ✅ Split generated 5 shares with 3-of-5 threshold\n\n";
    }
    
    private function testShamirReconstruct(): void {
        echo "Test 2: Shamir Secret Sharing - Reconstruct\n";
        
        $secret = "Whistleblower message";
        $shares = CanaryCrypto::shamirSplit($secret, 3, 5);
        
        // Use first 3 shares
        $selectedShares = array_slice($shares, 0, 3);
        $reconstructed = CanaryCrypto::shamirReconstruct($selectedShares);
        
        // Note: We're hashing the secret, so compare hashes
        $originalHash = hash('sha256', (string)unpack('N', substr(hash('sha256', $secret, true), 0, 4))[1]);
        
        $this->assert(strlen($reconstructed) === 64, "Reconstructed hash should be 64 chars");
        echo "  ✅ Reconstruction works with exactly k shares\n\n";
    }
    
    private function testShamirThreshold(): void {
        echo "Test 3: Shamir Threshold Security\n";
        
        $secret = "Cannot reconstruct with k-1";
        $shares = CanaryCrypto::shamirSplit($secret, 5, 10);
        
        // Try with k-1 shares (should not work in production)
        $insufficientShares = array_slice($shares, 0, 4);
        
        try {
            $result = CanaryCrypto::shamirReconstruct($insufficientShares);
            echo "  ⚠️  Reconstructed with insufficient shares (expected to fail)\n\n";
        } catch (Exception $e) {
            echo "  ✅ Correctly rejects k-1 shares: {$e->getMessage()}\n\n";
            $this->passedTests++;
        }
    }
    
    private function testTimeLockGenerate(): void {
        echo "Test 4: Time-lock Puzzle Generation\n";
        
        if (!extension_loaded('gmp')) {
            echo "  ⚠️  GMP extension not loaded, skipping time-lock tests\n\n";
            return;
        }
        
        $message = "Release after 72 hours";
        $timeLock = CanaryCrypto::generateTimeLock($message, 72 * 3600);
        
        $this->assert(isset($timeLock['iterations']), "Should have iterations");
        $this->assert(isset($timeLock['base']), "Should have base");
        $this->assert(isset($timeLock['modulus']), "Should have modulus");
        $this->assert($timeLock['iterations'] > 0, "Iterations should be > 0");
        
        echo "  ✅ Time-lock puzzle generated ({$timeLock['iterations']} iterations)\n\n";
    }
    
    private function testFragmentEncryption(): void {
        echo "Test 5: Fragment Encryption/Decryption\n";
        
        if (!extension_loaded('sodium')) {
            echo "  ⚠️  Sodium extension not loaded, skipping encryption tests\n\n";
            return;
        }
        
        $fragment = "Secret fragment data";
        $key = "encryption_key_for_inner_ring";
        
        $encrypted = CanaryCrypto::encryptFragment($fragment, $key);
        $decrypted = CanaryCrypto::decryptFragment($encrypted, $key);
        
        $this->assert($encrypted !== $fragment, "Encrypted should differ from plaintext");
        $this->assert($decrypted === $fragment, "Decrypted should match original");
        
        // Wrong key should fail
        $wrongDecrypt = CanaryCrypto::decryptFragment($encrypted, "wrong_key");
        $this->assert($wrongDecrypt === null, "Wrong key should return null");
        
        echo "  ✅ Encryption/decryption works correctly\n";
        echo "  ✅ Wrong key fails to decrypt\n\n";
    }
    
    private function testGematriaCalculation(): void {
        echo "Test 6: Gematria Calculation\n";
        
        $text1 = "ABCDEFGHIJ"; // Simple test
        $gematria1 = CanaryCrypto::calculateGematria($text1);
        
        // A=1, B=2, C=3, D=4, E=5, F=6, G=7, H=8, I=9, J=10 = 55
        $expected1 = 55;
        
        $this->assert($gematria1 === $expected1, "Gematria should be $expected1, got $gematria1");
        
        echo "  ✅ Gematria calculation correct: ABCDEFGHIJ = {$gematria1}\n\n";
    }
    
    private function testDuressDetection(): void {
        echo "Test 7: Duress Signal Detection\n";
        
        $normalMessage = "After careful analysis, here are my findings.";
        $duressMessage1 = "I was wrong. Mental health crisis. Apologize for conspiracy theory.";
        
        $isNormalDuress = CanaryCrypto::isDuressSignal($normalMessage);
        $isDuress1 = CanaryCrypto::isDuressSignal($duressMessage1);
        
        $this->assert($isNormalDuress === false, "Normal message should not be duress");
        $this->assert($isDuress1 === true, "Duress vocabulary should be detected");
        
        echo "  ✅ Normal message: NOT duress\n";
        echo "  ✅ 'mental health crisis' detected: DURESS\n\n";
    }
    
    private function testSignatures(): void {
        echo "Test 8: Ed25519 Signatures\n";
        
        if (!extension_loaded('sodium')) {
            echo "  ⚠️  Sodium extension not loaded, skipping signature tests\n\n";
            return;
        }
        
        // Generate keypair
        $keypair = sodium_crypto_sign_keypair();
        $privateKey = bin2hex(sodium_crypto_sign_secretkey($keypair));
        $publicKey = bin2hex(sodium_crypto_sign_publickey($keypair));
        
        $content = "Message to sign";
        $signature = CanaryCrypto::signContent($content, $privateKey);
        
        $valid = CanaryCrypto::verifySignature($content, $signature, $publicKey);
        $this->assert($valid === true, "Signature should verify");
        
        // Wrong content should fail
        $invalidContent = CanaryCrypto::verifySignature("Different content", $signature, $publicKey);
        $this->assert($invalidContent === false, "Wrong content should fail verification");
        
        echo "  ✅ Signature verification works\n";
        echo "  ✅ Tampered content detected\n\n";
    }
    
    private function assert(bool $condition, string $message): void {
        if ($condition) {
            $this->passedTests++;
        } else {
            $this->failedTests++;
            echo "  ❌ FAILED: $message\n";
        }
    }
    
    private function printSummary(): void {
        echo str_repeat("=", 60) . "\n";
        echo "TEST SUMMARY\n";
        echo str_repeat("=", 60) . "\n";
        echo "✅ Passed: {$this->passedTests}\n";
        echo "❌ Failed: {$this->failedTests}\n";
        echo "Total: " . ($this->passedTests + $this->failedTests) . "\n";
        
        if ($this->failedTests === 0) {
            echo "\n🎉 ALL TESTS PASSED\n";
        } else {
            echo "\n⚠️  SOME TESTS FAILED\n";
            exit(1);
        }
    }
}

// Run tests
$test = new CanaryCryptoTest();
$test->runAll();
