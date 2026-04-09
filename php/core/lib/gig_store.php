<?php
/**
 * Gig Storage
 * SQLite-backed gig marketplace storage
 */

class GigStore {
    private PDO $db;
    
    public function __construct(string $db_path) {
        $this->db = new PDO('sqlite:' . $db_path);
        $this->db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $this->initSchema();
    }
    
    private function initSchema(): void {
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS gigs (
                gig_id TEXT PRIMARY KEY,
                author_key TEXT NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                price REAL NOT NULL,
                location TEXT,
                deadline TEXT,
                ring_visibility INTEGER DEFAULT 2,
                status TEXT DEFAULT 'open',
                created_at REAL NOT NULL,
                completed_at REAL,
                completer_key TEXT
            )
        ");
        
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_gigs_status ON gigs(status)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_gigs_author ON gigs(author_key)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_gigs_created ON gigs(created_at DESC)");
    }
    
    public function createGig(array $gig): bool {
        $stmt = $this->db->prepare("
            INSERT INTO gigs (
                gig_id, author_key, title, description, price, 
                location, deadline, ring_visibility, status, created_at
            ) VALUES (
                :gig_id, :author_key, :title, :description, :price,
                :location, :deadline, :ring_visibility, :status, :created_at
            )
        ");
        
        return $stmt->execute([
            ':gig_id' => $gig['gig_id'],
            ':author_key' => $gig['author_key'],
            ':title' => $gig['title'],
            ':description' => $gig['description'],
            ':price' => $gig['price'],
            ':location' => $gig['location'] ?? '',
            ':deadline' => $gig['deadline'] ?? null,
            ':ring_visibility' => $gig['ring_visibility'] ?? 2,
            ':status' => $gig['status'] ?? 'open',
            ':created_at' => $gig['created_at'],
        ]);
    }
    
    public function listGigs(int $limit = 20, int $offset = 0, ?string $ring = null): array {
        $sql = "SELECT * FROM gigs WHERE status = 'open'";
        
        if ($ring !== null) {
            $sql .= " AND ring_visibility >= :ring";
        }
        
        $sql .= " ORDER BY created_at DESC LIMIT :limit OFFSET :offset";
        
        $stmt = $this->db->prepare($sql);
        
        if ($ring !== null) {
            $stmt->bindValue(':ring', (int)$ring, PDO::PARAM_INT);
        }
        
        $stmt->bindValue(':limit', $limit, PDO::PARAM_INT);
        $stmt->bindValue(':offset', $offset, PDO::PARAM_INT);
        $stmt->execute();
        
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    public function getGig(string $gig_id): ?array {
        $stmt = $this->db->prepare("SELECT * FROM gigs WHERE gig_id = :gig_id");
        $stmt->execute([':gig_id' => $gig_id]);
        
        $result = $stmt->fetch(PDO::FETCH_ASSOC);
        return $result ?: null;
    }
    
    public function markComplete(string $gig_id, string $completer_key): bool {
        $stmt = $this->db->prepare("
            UPDATE gigs 
            SET status = 'completed', 
                completed_at = :completed_at,
                completer_key = :completer_key
            WHERE gig_id = :gig_id AND status = 'open'
        ");
        
        $stmt->execute([
            ':gig_id' => $gig_id,
            ':completed_at' => microtime(true),
            ':completer_key' => $completer_key,
        ]);
        
        return $stmt->rowCount() > 0;
    }
    
    public function getUserGigs(string $author_key, string $status = 'all'): array {
        $sql = "SELECT * FROM gigs WHERE author_key = :author_key";
        
        if ($status !== 'all') {
            $sql .= " AND status = :status";
        }
        
        $sql .= " ORDER BY created_at DESC";
        
        $stmt = $this->db->prepare($sql);
        $stmt->bindValue(':author_key', $author_key);
        
        if ($status !== 'all') {
            $stmt->bindValue(':status', $status);
        }
        
        $stmt->execute();
        
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
}
