<?php
/**
 * Messages page with spam folder (capability-gated)
 */
?>
<link rel="stylesheet" href="/static/css/osnova.css">
<script src="/static/js/stego.js"></script>

<div class="container">
    <h1>Messages</h1>
    
    <div class="mb-3">
        <button class="btn btn-primary" onclick="location.href='/messages/compose'">
            New Message
        </button>
        
        <button id="spam-folder-btn" class="btn btn-secondary" 
                onclick="toggleSpamFolder()" style="display:none;">
            📬 Spam Folder
        </button>
    </div>
    
    <div id="inbox" class="message-list">
        <?php if (empty($messages)): ?>
            <div class="card text-center">
                <p class="text-muted">No messages yet</p>
            </div>
        <?php else: ?>
            <?php foreach ($messages as $msg): ?>
                <div class="card post-card">
                    <div class="feed-item">
                        <div class="avatar"></div>
                        <div class="content">
                            <div class="author">
                                <?= htmlspecialchars(substr($msg['from_key'], 0, 8)) ?>...
                                <span class="text-muted"><?= date('Y-m-d H:i', $msg['timestamp']) ?></span>
                            </div>
                            <div class="text mt-1">
                                <?= htmlspecialchars($msg['body']) ?>
                            </div>
                            <div class="actions mt-2">
                                <button onclick="replyTo('<?= $msg['from_key'] ?>')">Reply</button>
                            </div>
                        </div>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
    
    <div id="spam-folder" style="display:none;">
        <h2>Spam Folder</h2>
        <p class="text-muted">Messages flagged by AI filter</p>
        
        <div id="spam-list" class="message-list">
            <!-- Spam messages loaded here -->
        </div>
    </div>
</div>

<script>
async function toggleSpamFolder() {
    const spam = document.getElementById('spam-folder');
    const inbox = document.getElementById('inbox');
    
    if (spam.style.display === 'none') {
        // Load spam messages
        const response = await fetch('/api/messages/spam');
        if (response.ok) {
            const data = await response.json();
            renderSpamMessages(data.messages);
        }
        spam.style.display = 'block';
        inbox.style.display = 'none';
    } else {
        spam.style.display = 'none';
        inbox.style.display = 'block';
    }
}

function renderSpamMessages(messages) {
    const container = document.getElementById('spam-list');
    
    if (messages.length === 0) {
        container.innerHTML = '<div class="card text-center"><p class="text-muted">No spam messages</p></div>';
        return;
    }
    
    container.innerHTML = messages.map(msg => `
        <div class="card" style="border-left-color: #C62828;">
            <div class="feed-item">
                <div class="avatar"></div>
                <div class="content">
                    <div class="author">
                        ${msg.from_key.substring(0, 8)}...
                        <span class="text-muted">${new Date(msg.timestamp * 1000).toLocaleString()}</span>
                    </div>
                    <div class="text mt-1">${msg.body}</div>
                    <div class="actions mt-2">
                        <button onclick="moveToInbox('${msg.message_id}')">Not Spam</button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function replyTo(key) {
    location.href = `/messages/compose?to=${key}`;
}

// Show spam folder button if capability unlocked
if (osnovaStego.showSpamFolder()) {
    document.getElementById('spam-folder-btn').style.display = 'inline-block';
}
</script>
