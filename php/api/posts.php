<?php
/**
 * Posts API
 * POST   /api/posts                           - create post (server-signed, node-to-node)
 * POST   /api/posts/signed                    - accept pre-signed entry from browser client
 * GET    /api/posts                           - feed
 * GET    /api/posts/{hash}                    - single post
 * POST   /api/posts/{hash}/comment            - add comment
 * GET    /api/posts/{hash}/comments           - get comments
 * POST   /api/posts/{hash}/reshare            - reshare
 */

function api_posts_handler(string $method, array $segments, array $kp, ContentLog $log): void {
    // /api/posts/signed - client pre-signed entry
    if (count($segments) === 3 && $segments[2] === 'signed') {
        if ($method === 'POST') {
            api_receive_signed($log);
            return;
        }
        json_error(405, 'Method not allowed');
        return;
    }

    // /api/posts/{hash}/comments  or  /api/posts/{hash}/comment  or  /api/posts/{hash}/reshare
    if (count($segments) >= 4 && $segments[0] === 'api' && $segments[1] === 'posts') {
        $hash   = $segments[2];
        $action = $segments[3] ?? '';

        if ($action === 'comments' && $method === 'GET') {
            api_get_comments($hash, $log);
            return;
        }
        if ($action === 'comment' && $method === 'POST') {
            api_add_comment($hash, $kp, $log);
            return;
        }
        if ($action === 'reshare' && $method === 'POST') {
            api_reshare($hash, $kp, $log);
            return;
        }
        json_error(404, 'Unknown endpoint');
        return;
    }

    // /api/posts/{hash}
    if (count($segments) === 3 && $segments[0] === 'api' && $segments[1] === 'posts') {
        $hash = $segments[2];
        if ($method === 'GET') {
            api_get_post($hash, $log);
            return;
        }
        json_error(405, 'Method not allowed');
        return;
    }

    // /api/posts
    if ($method === 'POST') {
        api_create_post($kp, $log);
    } elseif ($method === 'GET') {
        api_get_feed($log);
    } else {
        json_error(405, 'Method not allowed');
    }
}

function api_create_post(array $kp, ContentLog $log): void {
    $body = json_input();
    $text = trim($body['body'] ?? '');
    if ($text === '') {
        json_error(422, 'body is required');
        return;
    }
    $metadata  = $body['metadata'] ?? [];
    $timestamp = microtime(true);
    $entry     = make_entry($kp['public'], 'post', $text, null, $metadata, $timestamp);
    $entry['signature'] = crypto_sign_content_hash($entry['content_hash'], $kp);

    try {
        $log->append($entry);
    } catch (\RuntimeException $e) {
        json_error(409, $e->getMessage());
        return;
    }
    json_out($entry);
}

function api_get_feed(ContentLog $log): void {
    $limit      = (int)($_GET['limit']      ?? 50);
    $offset     = (int)($_GET['offset']     ?? 0);
    $author_key = $_GET['author_key'] ?? null;
    json_out($log->getFeed($limit, $offset, $author_key ?: null));
}

function api_get_post(string $hash, ContentLog $log): void {
    $entry = $log->get($hash);
    if (!$entry) {
        json_error(404, 'Post not found');
        return;
    }
    json_out($entry);
}

function api_add_comment(string $parent_hash, array $kp, ContentLog $log): void {
    $parent = $log->get($parent_hash);
    if (!$parent) {
        json_error(404, 'Parent post not found');
        return;
    }
    $body = json_input();
    $text = trim($body['body'] ?? '');
    if ($text === '') {
        json_error(422, 'body is required');
        return;
    }
    $timestamp = microtime(true);
    $entry     = make_entry($kp['public'], 'comment', $text, $parent_hash, [], $timestamp);
    $entry['signature'] = crypto_sign_content_hash($entry['content_hash'], $kp);

    try {
        $log->append($entry);
    } catch (\RuntimeException $e) {
        json_error(409, $e->getMessage());
        return;
    }
    json_out($entry);
}

function api_get_comments(string $parent_hash, ContentLog $log): void {
    $parent = $log->get($parent_hash);
    if (!$parent) {
        json_error(404, 'Post not found');
        return;
    }
    json_out($log->getComments($parent_hash));
}

function api_reshare(string $original_hash, array $kp, ContentLog $log): void {
    $original = $log->get($original_hash);
    if (!$original) {
        json_error(404, 'Post not found');
        return;
    }
    $timestamp = microtime(true);
    $entry     = make_entry(
        $kp['public'],
        'reshare',
        $original['body'],
        $original_hash,
        ['reshared_from' => $original['author_key']],
        $timestamp
    );
    $entry['signature'] = crypto_sign_content_hash($entry['content_hash'], $kp);

    try {
        $log->append($entry);
    } catch (\RuntimeException $e) {
        json_error(409, $e->getMessage());
        return;
    }
    json_out($entry);
}

/**
 * POST /api/posts/signed
 *
 * Accept a pre-signed entry from a browser client.
 * The client (osnova.js) has already:
 *   1. Generated an Ed25519 keypair in localStorage
 *   2. Computed the content_hash
 *   3. Signed the content_hash
 *
 * The server verifies the signature and stores the entry.
 * The server does NOT re-sign - author_key belongs to the user, not this node.
 */
function api_receive_signed(ContentLog $log): void {
    $body = json_input();

    // Required fields
    $required = ['author_key', 'content_type', 'body', 'timestamp', 'signature', 'content_hash'];
    foreach ($required as $field) {
        if (!isset($body[$field]) || $body[$field] === '') {
            json_error(422, "Missing required field: {$field}");
            return;
        }
    }

    $text = trim($body['body']);
    if ($text === '') {
        json_error(422, 'body is required');
        return;
    }

    $author_key   = (string)$body['author_key'];
    $content_type = (string)$body['content_type'];
    $parent_hash  = isset($body['parent_hash']) && $body['parent_hash'] !== '' && $body['parent_hash'] !== null
                    ? (string)$body['parent_hash']
                    : null;
    $metadata     = is_array($body['metadata'] ?? null) ? $body['metadata'] : [];
    $timestamp    = (float)$body['timestamp'];
    $signature    = (string)$body['signature'];
    $client_hash  = (string)$body['content_hash'];

    // 1. Recompute the content_hash server-side and compare
    $server_hash = crypto_content_hash($author_key, $content_type, $text, $parent_hash, $timestamp);
    if ($server_hash !== $client_hash) {
        json_error(400, 'content_hash mismatch: client and server disagree');
        return;
    }

    // 2. Verify the Ed25519 signature over the content_hash
    if (!crypto_verify_content($server_hash, $author_key, $signature)) {
        json_error(403, 'Signature verification failed');
        return;
    }

    // 3. Store the verified entry (author_key stays as the client's public key)
    $entry = [
        'content_hash' => $server_hash,
        'author_key'   => $author_key,
        'content_type' => $content_type,
        'body'         => $text,
        'parent_hash'  => $parent_hash,
        'metadata'     => $metadata,
        'timestamp'    => $timestamp,
        'signature'    => $signature,
    ];

    try {
        $log->append($entry);
    } catch (\RuntimeException $e) {
        json_error(409, $e->getMessage());
        return;
    }

    json_out($entry);
}
