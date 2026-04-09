<?php
/**
 * Gigs page - marketplace for tasks and services
 */
?>
<link rel="stylesheet" href="/static/css/osnova.css">

<div class="container">
    <h1>Gigs Near You</h1>
    <p class="text-muted mb-3">Earn money helping your network</p>
    
    <div class="mb-3">
        <a href="/gigs/post" class="btn btn-gig">Post a Gig</a>
    </div>
    
    <div class="gig-list">
        <?php if (empty($gigs)): ?>
            <div class="card text-center">
                <p class="text-muted">No gigs available yet. Be the first to post!</p>
            </div>
        <?php else: ?>
            <?php foreach ($gigs as $gig): ?>
                <div class="card gig-card">
                    <div class="gig-item">
                        <div class="info">
                            <div class="title"><?= htmlspecialchars($gig['title']) ?></div>
                            <div class="text-muted mt-1"><?= htmlspecialchars($gig['description']) ?></div>
                            <div class="meta mt-2">
                                <span>👤 <?= htmlspecialchars(substr($gig['author_key'], 0, 8)) ?>...</span>
                                <?php if ($gig['location']): ?>
                                    <span>📍 <?= htmlspecialchars($gig['location']) ?></span>
                                <?php endif; ?>
                                <?php if ($gig['deadline']): ?>
                                    <span>⏰ <?= htmlspecialchars($gig['deadline']) ?></span>
                                <?php endif; ?>
                            </div>
                        </div>
                        <div class="price">$<?= number_format($gig['price'], 0) ?></div>
                    </div>
                    <div class="mt-2">
                        <a href="/gigs/<?= $gig['gig_id'] ?>" class="btn btn-secondary">View Details</a>
                    </div>
                </div>
            <?php endforeach; ?>
        <?php endif; ?>
    </div>
</div>

<script>
// Auto-refresh gigs every 30s
setInterval(async () => {
    const response = await fetch('/api/gigs/list');
    if (response.ok) {
        location.reload();
    }
}, 30000);
</script>
