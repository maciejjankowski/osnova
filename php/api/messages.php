<?php
/**
 * Messages API
 * Handles direct messages and spam folder
 */

function api_messages_handler(string $method, array $segments, array $kp, object $log): void {
    global $messageStore;
    
    if (!isset($messageStore)) {
        $messageStore = new MessageStore(DATA_DIR . '/messages.db');
    }
    
    $action = $segments[2] ?? 'list';
    
    match ($action) {
        'list' => match ($method) {
            'GET' => messages_list($messageStore, $kp),
            default => json_error(405, 'Method not allowed')
        },
        
        'spam' => match ($method) {
            'GET' => messages_spam($messageStore, $kp),
            default => json_error(405, 'Method not allowed')
        },
        
        'send' => match ($method) {
            'POST' => messages_send($messageStore, $kp, $log),
            default => json_error(405, 'Method not allowed')
        },
        
        default => json_error(404, "Unknown message action: {$action}")
    };
}

function messages_list(object $store, array $kp): void {
    $messages = $store->getInbox($kp['public']);
    json_out(['messages' => $messages]);
}

function messages_spam(object $store, array $kp): void {
    $messages = $store->getSpam($kp['public']);
    json_out(['messages' => $messages]);
}

function messages_send(object $store, array $kp, object $log): void {
    $data = json_input();
    
    $required = ['to_key', 'body'];
    foreach ($required as $field) {
        if (!isset($data[$field])) {
            json_error(400, "Missing field: {$field}");
        }
    }
    
    $message = [
        'message_id' => bin2hex(random_bytes(16)),
        'from_key' => $kp['public'],
        'to_key' => $data['to_key'],
        'body' => $data['body'],
        'timestamp' => microtime(true),
        'is_spam' => false,
    ];
    
    $store->sendMessage($message);
    
    // Also log for replication
    $content = [
        'type' => 'message',
        'data' => $message,
    ];
    $log->append($kp['public'], $content, $kp['private']);
    
    json_out(['message' => $message], 201);
}

class MessageStore {
    private PDO $db;
    
    public function __construct(string $db_path) {
        $this->db = new PDO('sqlite:' . $db_path);
        $this->db->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
        $this->initSchema();
    }
    
    private function initSchema(): void {
        $this->db->exec("
            CREATE TABLE IF NOT EXISTS messages (
                message_id TEXT PRIMARY KEY,
                from_key TEXT NOT NULL,
                to_key TEXT NOT NULL,
                body TEXT NOT NULL,
                timestamp REAL NOT NULL,
                is_spam INTEGER DEFAULT 0,
                read INTEGER DEFAULT 0
            )
        ");
        
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_messages_to ON messages(to_key, timestamp DESC)");
        $this->db->exec("CREATE INDEX IF NOT EXISTS idx_messages_spam ON messages(to_key, is_spam)");
    }
    
    public function sendMessage(array $msg): bool {
        $stmt = $this->db->prepare("
            INSERT INTO messages (message_id, from_key, to_key, body, timestamp, is_spam)
            VALUES (:id, :from, :to, :body, :ts, :spam)
        ");
        
        return $stmt->execute([
            ':id' => $msg['message_id'],
            ':from' => $msg['from_key'],
            ':to' => $msg['to_key'],
            ':body' => $msg['body'],
            ':ts' => $msg['timestamp'],
            ':spam' => $msg['is_spam'] ? 1 : 0,
        ]);
    }
    
    public function getInbox(string $to_key): array {
        $stmt = $this->db->prepare("
            SELECT * FROM messages 
            WHERE to_key = :to AND is_spam = 0
            ORDER BY timestamp DESC
        ");
        
        $stmt->execute([':to' => $to_key]);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    public function getSpam(string $to_key): array {
        $stmt = $this->db->prepare("
            SELECT * FROM messages 
            WHERE to_key = :to AND is_spam = 1
            ORDER BY timestamp DESC
        ");
        
        $stmt->execute([':to' => $to_key]);
        return $stmt->fetchAll(PDO::FETCH_ASSOC);
    }
    
    public function markAsSpam(string $message_id): bool {
        $stmt = $this->db->prepare("UPDATE messages SET is_spam = 1 WHERE message_id = :id");
        $stmt->execute([':id' => $message_id]);
        return $stmt->rowCount() > 0;
    }
}
