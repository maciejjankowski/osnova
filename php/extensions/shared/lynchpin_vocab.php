<?php
/**
 * Lynchpin domain vocabulary for discovery challenge hints.
 * Provides culturally-grounded noise that's meaningful to humans but difficult for outsiders.
 */

class LynchpinVocab {
    /**
     * Get a random hint from Lynchpin vocabulary domains.
     * Categories: Polish proverbs, biblical references, network topology, PARDES layers.
     */
    public static function getRandomHint(?string $category = null): string {
        $hints = self::getVocabulary();
        
        if ($category && isset($hints[$category])) {
            $pool = $hints[$category];
        } else {
            // Flatten all categories
            $pool = [];
            foreach ($hints as $cat_hints) {
                $pool = array_merge($pool, $cat_hints);
            }
        }
        
        return $pool[array_rand($pool)] ?? 'verify integrity';
    }
    
    private static function getVocabulary(): array {
        return [
            'polish_proverbs' => [
                'Co nagle, to po diable',
                'Lepszy wróbel w garści niż gołąb na dachu',
                'Nie dziel skóry na niedźwiedziu',
                'Kto pod kim dołki kopie, sam w nie wpada',
                'Apetyt rośnie w miarę jedzenia',
            ],
            'biblical' => [
                'Exodus twenty sixteen',
                'Proverbs eighteen seventeen',
                'First Kings twenty-two',
                'Numbers twenty-two',
                'Habakkuk two two',
            ],
            'network' => [
                'Dunbar core',
                'gossip convergence',
                'append-only integrity',
                'trust ring boundary',
                'signal layer verification',
            ],
            'pardes' => [
                'SEED generates whole',
                'holographic reconstruction',
                'fractal propagation',
                'five-scale invariance',
                'void detection',
            ],
            'technical' => [
                'Ed25519 verification',
                'SHA256 content hash',
                'SQLite WAL mode',
                'HTMX partial swap',
                'CSP encoding layer',
            ],
        ];
    }
    
    /**
     * Generate contextual hint for a discovery challenge.
     * Combines category hint with structural guidance.
     */
    public static function generateChallengeHint(string $difficulty = 'medium'): string {
        $categories = ['polish_proverbs', 'biblical', 'network', 'pardes'];
        $category = $categories[array_rand($categories)];
        $hint = self::getRandomHint($category);
        
        $prefixes = match($difficulty) {
            'easy'   => ['Hint:', 'Consider:', 'Think:'],
            'medium' => ['Verify via:', 'Cross-reference:', 'Context:'],
            'hard'   => ['Adversarial check:', 'Triangulate:', 'Steel-man:'],
            default  => ['Context:'],
        };
        
        $prefix = $prefixes[array_rand($prefixes)];
        return "$prefix $hint";
    }
}
