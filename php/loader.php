<?php
/**
 * Osnova Extension Loader
 * 
 * Determines which extensions to load based on:
 * - User behavioral profile
 * - Ring composition
 * - Social handshakes
 * - Client capabilities
 * 
 * Extensions are INVISIBLE until activated.
 */

declare(strict_types=1);

class OsnovaLoader {
    private array $activeExtensions = [];
    private array $userProfile = [];
    
    public function __construct(private ?string $userPubkey = null) {
        // Core is ALWAYS loaded
        $this->activeExtensions[] = 'core';
    }
    
    /**
     * Check if extensions should be activated
     */
    public function loadExtensions(array $context = []): array {
        // Check activation conditions
        $triggers = $this->checkTriggers($context);
        
        if ($triggers['canary']) {
            $this->activeExtensions[] = 'canary';
        }
        
        if ($triggers['stego']) {
            $this->activeExtensions[] = 'stego';
        }
        
        if ($triggers['signals']) {
            $this->activeExtensions[] = 'signals';
        }
        
        if ($triggers['phantom']) {
            $this->activeExtensions[] = 'phantom';
        }
        
        return $this->activeExtensions;
    }
    
    /**
     * Check behavioral triggers for extension activation
     */
    private function checkTriggers(array $context): array {
        $triggers = [
            'canary' => false,
            'stego' => false,
            'signals' => false,
            'phantom' => false
        ];
        
        // If no user, only core features
        if (!$this->userPubkey) {
            return $triggers;
        }
        
        // 1. Check for phantom user follows
        $phantomFollows = $this->checkPhantomFollows($context);
        
        // 2. Check for social handshake
        $handshakeComplete = $this->checkSocialHandshake($context);
        
        // 3. Check ring composition (trusted nodes present?)
        $trustedRing = $this->checkTrustedRing($context);
        
        // 4. Check client capabilities (extensions installed?)
        $clientCapable = $this->checkClientCapabilities($context);
        
        // 5. Check behavioral patterns
        $behaviorMatch = $this->checkBehavior($context);
        
        // Activation logic (AND conditions for security)
        if ($phantomFollows && $handshakeComplete) {
            $triggers['phantom'] = true;
            $triggers['signals'] = true;
        }
        
        if ($triggers['phantom'] && $trustedRing) {
            $triggers['stego'] = true;
        }
        
        if ($triggers['stego'] && $clientCapable && $behaviorMatch) {
            $triggers['canary'] = true;
        }
        
        return $triggers;
    }
    
    /**
     * Check if user follows phantom accounts
     */
    private function checkPhantomFollows(array $context): bool {
        // Known phantom accounts (could be DB-backed)
        $phantoms = [
            'phantom_leo',
            'phantom_manual',
            'phantom_setup'
        ];
        
        $following = $context['following'] ?? [];
        
        foreach ($phantoms as $phantom) {
            if (in_array($phantom, $following)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Check for social handshake phrases
     */
    private function checkSocialHandshake(array $context): bool {
        $keywords = ['leo', 'manual', 'setup guide', 'read the docs'];
        $recentPosts = $context['recent_posts'] ?? [];
        
        foreach ($recentPosts as $post) {
            $content = strtolower($post['content'] ?? '');
            foreach ($keywords as $keyword) {
                if (str_contains($content, $keyword)) {
                    return true;
                }
            }
        }
        
        return false;
    }
    
    /**
     * Check if ring contains trusted nodes
     */
    private function checkTrustedRing(array $context): bool {
        $ringMembers = $context['ring_members'] ?? [];
        $trustedNodes = $context['trusted_nodes'] ?? [];
        
        foreach ($ringMembers as $member) {
            if (in_array($member, $trustedNodes)) {
                return true;
            }
        }
        
        return false;
    }
    
    /**
     * Check if client has capabilities installed
     */
    private function checkClientCapabilities(array $context): bool {
        // Check for cookie consent (actually capability grant)
        $cookieAccepted = $context['cookie_consent'] ?? false;
        
        // Check for client-side extensions
        $hasExtensions = $context['client_extensions'] ?? false;
        
        return $cookieAccepted && $hasExtensions;
    }
    
    /**
     * Check behavioral patterns
     */
    private function checkBehavior(array $context): bool {
        $profile = $context['behavior'] ?? [];
        
        // Typo frequency analysis
        $typoRate = $profile['typo_rate'] ?? 0;
        
        // Emoji usage patterns
        $emojiPattern = $profile['emoji_sequence'] ?? '';
        
        // Post timing patterns
        $timingMatch = $profile['timing_match'] ?? false;
        
        // Simple heuristic (could be ML model)
        return $typoRate > 0 || !empty($emojiPattern) || $timingMatch;
    }
    
    /**
     * Check if specific extension is active
     */
    public function isActive(string $extension): bool {
        return in_array($extension, $this->activeExtensions);
    }
    
    /**
     * Get all active extensions
     */
    public function getActive(): array {
        return $this->activeExtensions;
    }
    
    /**
     * Require extension files if active
     */
    public function requireExtension(string $extension, string $type = 'api'): bool {
        if (!$this->isActive($extension)) {
            return false;
        }
        
        $path = __DIR__ . "/extensions/{$extension}/{$type}/";
        
        if (!is_dir($path)) {
            return false;
        }
        
        foreach (glob($path . '*.php') as $file) {
            require_once $file;
        }
        
        return true;
    }
}

/**
 * Initialize loader globally
 */
function init_loader(?string $userPubkey = null, array $context = []): OsnovaLoader {
    $loader = new OsnovaLoader($userPubkey);
    $loader->loadExtensions($context);
    return $loader;
}
