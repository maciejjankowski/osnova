<?php
/**
 * ContentLog - append-only SQLite log.
 * Schema mirrors the Python aiosqlite version exactly.
 */
class ContentLog {
    private SQLite3 $db;

    public function __construct(string $db_path) {
        $this->db = new SQLite3($db_path);
        $this->db->enableExceptions(true);
        $this->db->exec('PRAGMA journal_mode=WAL;');
        $this->db->exec('PRAGMA foreign_keys=ON;');
        $this->initialize();
    }

    private function initialize(): void {
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS entries (
                content_hash  TEXT PRIMARY KEY,
                author_key    TEXT NOT NULL,
                content_type  TEXT NOT NULL,
                body          TEXT NOT NULL,
                parent_hash   TEXT,
                metadata      TEXT NOT NULL DEFAULT '{}',
                timestamp     REAL NOT NULL,
                signature     TEXT NOT NULL DEFAULT ''
            )
        ");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_entries_timestamp   ON entries (timestamp DESC)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_entries_author_key  ON entries (author_key)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_entries_parent_hash ON entries (parent_hash)");
    }

    /**
     * Append an entry. Throws \RuntimeException if hash already exists.
     * Auto-tags with PARDES metadata before storing.
     * Returns content_hash.
     */
    public function append(array $entry): string {
        // Auto-tag with PARDES metadata
        require_once __DIR__ . '/pardes.php';
        $entry = PardesDetector::autoTag($entry);
        
        $hash = $entry['content_hash'];

        $check = $this->db->prepare("SELECT 1 FROM entries WHERE content_hash = ?");
        $check->bindValue(1, $hash, SQLITE3_TEXT);
        $res = $check->execute();
        if ($res && $res->fetchArray()) {
            throw new \RuntimeException("Entry with hash {$hash} already exists");
        }

        $stmt = $this->db->prepare("
            INSERT INTO entries
                (content_hash, author_key, content_type, body, parent_hash, metadata, timestamp, signature)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ");
        $stmt->bindValue(1, $hash,                         SQLITE3_TEXT);
        $stmt->bindValue(2, $entry['author_key'],          SQLITE3_TEXT);
        $stmt->bindValue(3, $entry['content_type'],        SQLITE3_TEXT);
        $stmt->bindValue(4, $entry['body'],                SQLITE3_TEXT);
        $stmt->bindValue(5, $entry['parent_hash'] ?? null, SQLITE3_NULL);
        $stmt->bindValue(6, json_encode($entry['metadata'] ?? []), SQLITE3_TEXT);
        $stmt->bindValue(7, (float)($entry['timestamp']),  SQLITE3_FLOAT);
        $stmt->bindValue(8, $entry['signature'] ?? '',     SQLITE3_TEXT);

        // SQLite3::bindValue does not support nullable TEXT cleanly - re-bind parent_hash
        if ($entry['parent_hash'] !== null && $entry['parent_hash'] !== '') {
            $stmt->bindValue(5, $entry['parent_hash'], SQLITE3_TEXT);
        } else {
            $stmt->bindValue(5, null, SQLITE3_NULL);
        }

        $stmt->execute();
        return $hash;
    }

    /** Get a single entry by hash. Returns null if not found. */
    public function get(string $content_hash): ?array {
        $stmt = $this->db->prepare("SELECT * FROM entries WHERE content_hash = ?");
        $stmt->bindValue(1, $content_hash, SQLITE3_TEXT);
        $res = $stmt->execute();
        $row = $res->fetchArray(SQLITE3_ASSOC);
        return $row ? $this->rowToEntry($row) : null;
    }

    /** Feed in reverse-chronological order. */
    public function getFeed(int $limit = 50, int $offset = 0, ?string $author_key = null): array {
        if ($author_key !== null) {
            $stmt = $this->db->prepare("
                SELECT * FROM entries WHERE author_key = ?
                ORDER BY timestamp DESC LIMIT ? OFFSET ?
            ");
            $stmt->bindValue(1, $author_key, SQLITE3_TEXT);
            $stmt->bindValue(2, $limit,      SQLITE3_INTEGER);
            $stmt->bindValue(3, $offset,     SQLITE3_INTEGER);
        } else {
            $stmt = $this->db->prepare("
                SELECT * FROM entries ORDER BY timestamp DESC LIMIT ? OFFSET ?
            ");
            $stmt->bindValue(1, $limit,  SQLITE3_INTEGER);
            $stmt->bindValue(2, $offset, SQLITE3_INTEGER);
        }
        $res = $stmt->execute();
        $entries = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $entries[] = $this->rowToEntry($row);
        }
        return $entries;
    }

    /** All comments for a post (ASC order). */
    public function getComments(string $parent_hash): array {
        $stmt = $this->db->prepare("
            SELECT * FROM entries WHERE parent_hash = ? ORDER BY timestamp ASC
        ");
        $stmt->bindValue(1, $parent_hash, SQLITE3_TEXT);
        $res = $stmt->execute();
        $entries = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $entries[] = $this->rowToEntry($row);
        }
        return $entries;
    }

    /** Hashes of entries newer than $since_timestamp (ASC order - for gossip). */
    public function getHashesSince(float $since_timestamp): array {
        $stmt = $this->db->prepare("
            SELECT content_hash FROM entries WHERE timestamp > ? ORDER BY timestamp ASC
        ");
        $stmt->bindValue(1, $since_timestamp, SQLITE3_FLOAT);
        $res = $stmt->execute();
        $hashes = [];
        while ($row = $res->fetchArray(SQLITE3_NUM)) {
            $hashes[] = $row[0];
        }
        return $hashes;
    }

    /** Bulk-fetch entries by a list of hashes. */
    public function getEntriesByHashes(array $hashes): array {
        if (empty($hashes)) return [];
        $placeholders = implode(',', array_fill(0, count($hashes), '?'));
        $stmt = $this->db->prepare("SELECT * FROM entries WHERE content_hash IN ({$placeholders})");
        foreach ($hashes as $i => $h) {
            $stmt->bindValue($i + 1, $h, SQLITE3_TEXT);
        }
        $res = $stmt->execute();
        $entries = [];
        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $entries[] = $this->rowToEntry($row);
        }
        return $entries;
    }

    /**
     * Get posts that were surfaced by engagement from specific authors.
     * "Bob commented on Alice's post" -> Alice's post appears in your feed.
     *
     * Returns array of ['post' => entry, 'surfaced_by' => engager_key, 'surface_type' => 'comment'|'reshare']
     */
    public function getSurfacedPosts(array $ring_keys, int $limit = 50, int $offset = 0): array {
        if (empty($ring_keys)) return [];

        // Find comments/reshares by ring members on posts NOT by ring members
        // This surfaces outside-network content through ring engagement
        $placeholders = implode(',', array_fill(0, count($ring_keys), '?'));

        $sql = "
            SELECT
                e.content_hash AS engagement_hash,
                e.author_key   AS engager_key,
                e.content_type AS engagement_type,
                e.parent_hash  AS parent_hash,
                e.timestamp    AS engagement_ts,
                p.content_hash AS post_hash,
                p.author_key   AS post_author,
                p.content_type AS post_type,
                p.body         AS post_body,
                p.parent_hash  AS post_parent_hash,
                p.metadata     AS post_metadata,
                p.timestamp    AS post_timestamp,
                p.signature    AS post_signature
            FROM entries e
            JOIN entries p ON e.parent_hash = p.content_hash
            WHERE e.author_key IN ({$placeholders})
              AND e.content_type IN ('comment', 'reshare')
              AND p.author_key NOT IN ({$placeholders})
            ORDER BY e.timestamp DESC
            LIMIT ? OFFSET ?
        ";

        $stmt = $this->db->prepare($sql);
        $i = 1;
        // Bind ring_keys for engager match
        foreach ($ring_keys as $key) {
            $stmt->bindValue($i++, $key, SQLITE3_TEXT);
        }
        // Bind ring_keys for exclusion (post author NOT in ring)
        foreach ($ring_keys as $key) {
            $stmt->bindValue($i++, $key, SQLITE3_TEXT);
        }
        $stmt->bindValue($i++, $limit, SQLITE3_INTEGER);
        $stmt->bindValue($i, $offset, SQLITE3_INTEGER);

        $res = $stmt->execute();
        $surfaced = [];
        $seen_posts = [];

        while ($row = $res->fetchArray(SQLITE3_ASSOC)) {
            $post_hash = $row['post_hash'];
            // Deduplicate: if multiple ring members commented on same post, show once
            if (isset($seen_posts[$post_hash])) continue;
            $seen_posts[$post_hash] = true;

            $surfaced[] = [
                'post' => [
                    'content_hash' => $row['post_hash'],
                    'author_key'   => $row['post_author'],
                    'content_type' => $row['post_type'],
                    'body'         => $row['post_body'],
                    'parent_hash'  => $row['post_parent_hash'],
                    'metadata'     => json_decode($row['post_metadata'], true) ?? [],
                    'timestamp'    => (float)$row['post_timestamp'],
                    'signature'    => $row['post_signature'],
                ],
                'surfaced_by'   => $row['engager_key'],
                'surface_type'  => $row['engagement_type'],  // 'comment' or 'reshare'
                'engagement_ts' => (float)$row['engagement_ts'],
            ];
        }
        return $surfaced;
    }

    public function count(): int {
        $res = $this->db->query("SELECT COUNT(*) FROM entries");
        return (int)$res->fetchArray(SQLITE3_NUM)[0];
    }

    // -----------------------------------------------------------------------
    // Internal
    // -----------------------------------------------------------------------

    private function rowToEntry(array $row): array {
        return [
            'content_hash' => $row['content_hash'],
            'author_key'   => $row['author_key'],
            'content_type' => $row['content_type'],
            'body'         => $row['body'],
            'parent_hash'  => $row['parent_hash'],
            'metadata'     => json_decode($row['metadata'], true) ?? [],
            'timestamp'    => (float)$row['timestamp'],
            'signature'    => $row['signature'],
        ];
    }
}

/**
 * Build a ContentEntry array from raw fields, computing the hash.
 */
function make_entry(
    string $author_key,
    string $content_type,
    string $body,
    ?string $parent_hash,
    array $metadata,
    float $timestamp,
    string $signature = ''
): array {
    $hash = crypto_content_hash($author_key, $content_type, $body, $parent_hash, $timestamp);
    return [
        'content_hash' => $hash,
        'author_key'   => $author_key,
        'content_type' => $content_type,
        'body'         => $body,
        'parent_hash'  => $parent_hash,
        'metadata'     => $metadata,
        'timestamp'    => $timestamp,
        'signature'    => $signature,
    ];
}
