<?php
/**
 * PARDES layer detection for content metadata auto-tagging.
 * Automatically tags content with fractal layer info based on length.
 */

class PardesLayer {
    const SEED = 'seed';           // One sentence that generates the whole
    const PARAGRAPH = 'paragraph'; // 3-5 sentences, napkin-ready
    const PAGE = 'page';           // Single printable page
    const DOCUMENT = 'document';   // 1-3 pages executive summary
    const SYSTEM = 'system';       // Full document with all detail
}

class PardesDetector {
    /**
     * Detect PARDES layer based on content length.
     * 
     * @param string $body Content text
     * @return string PardesLayer constant
     */
    public static function detectLayer(string $body): string {
        // Count sentences (rough heuristic: split by . ! ?)
        $text = str_replace(['!', '?'], '.', $body);
        $sentences = array_filter(
            array_map('trim', explode('.', $text)),
            fn($s) => strlen($s) > 0
        );
        $sentence_count = count($sentences);
        
        // Count words
        $word_count = str_word_count($body);
        
        // Layer detection
        if ($sentence_count <= 1 || $word_count < 25) {
            return PardesLayer::SEED;
        } elseif ($sentence_count <= 5 || $word_count < 150) {
            return PardesLayer::PARAGRAPH;
        } elseif ($word_count < 800) {
            return PardesLayer::PAGE;
        } elseif ($word_count < 2500) {
            return PardesLayer::DOCUMENT;
        } else {
            return PardesLayer::SYSTEM;
        }
    }
    
    /**
     * Auto-tag content entry with PARDES metadata.
     * Adds 'pardes_layer', 'word_count', 'sentence_count' to metadata.
     * 
     * @param array $entry Content entry array (must have 'body' and 'metadata' keys)
     * @return array Entry with updated metadata
     */
    public static function autoTag(array $entry): array {
        $body = $entry['body'] ?? '';
        
        if (!isset($entry['metadata'])) {
            $entry['metadata'] = [];
        }
        
        // Detect layer
        $layer = self::detectLayer($body);
        
        // Count metrics
        $text = str_replace(['!', '?'], '.', $body);
        $sentences = array_filter(
            array_map('trim', explode('.', $text)),
            fn($s) => strlen($s) > 0
        );
        $sentence_count = count($sentences);
        $word_count = str_word_count($body);
        
        // Update metadata
        $entry['metadata']['pardes_layer'] = $layer;
        $entry['metadata']['word_count'] = $word_count;
        $entry['metadata']['sentence_count'] = $sentence_count;
        $entry['metadata']['auto_tagged_at'] = microtime(true);
        
        return $entry;
    }
    
    /**
     * Check if entry should be replicated to middle ring (SEED/PARAGRAPH only).
     * 
     * @param array $entry Content entry with metadata
     * @return bool True if should replicate to middle ring
     */
    public static function shouldReplicateToMiddleRing(array $entry): bool {
        $layer = $entry['metadata']['pardes_layer'] ?? null;
        return in_array($layer, [PardesLayer::SEED, PardesLayer::PARAGRAPH], true);
    }
}
