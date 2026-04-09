<?php
/**
 * Feed page - rendered into $content, then base.php wraps it.
 * Expects:
 *   $posts        (array of ContentEntry arrays)
 *   $author_names (array of public_key => display string, optional)
 */
$author_names     = $author_names ?? [];
$surfaced_context = $surfaced_context ?? [];

function fmt_time(float $ts): string {
    return date('Y-m-d H:i', (int)$ts);
}

/** Get avatar initials + a deterministic color from the public key */
function avatar_color(string $pk): string {
    $colors = ['#7c6af7','#e85d75','#2ecc71','#3498db','#e67e22','#9b59b6','#1abc9c','#e74c3c'];
    $idx = hexdec(substr($pk, 0, 2)) % count($colors);
    return $colors[$idx];
}
?>
<div class="feed-header">
  <h2>Feed</h2>
  <a href="/compose" role="button" class="outline">+ New Post</a>
</div>

<?php if (!empty($posts)): ?>
  <?php foreach ($posts as $post): ?>
  <?php
    $shortHash = substr($post['content_hash'], 0, 8);
    $pk        = $post['author_key'];
    $display   = $author_names[$pk] ?? (substr($pk, 0, 8) . '...');
    $initials  = strtoupper(substr(str_replace('...', '', $display), 0, 2));
    $color     = avatar_color($pk);
  ?>
  <?php
    // Surfaced-by context: show WHY this outside-network post is in your feed
    $ctx = $surfaced_context[$post['content_hash']] ?? null;
  ?>
  <?php if ($ctx): ?>
  <div class="surfaced-banner">
    <svg viewBox="0 0 24 24" width="14" height="14" style="vertical-align:middle;opacity:0.5;fill:none;stroke:currentColor;stroke-width:2;">
      <polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path>
    </svg>
    <span>
      <?= htmlspecialchars(substr($ctx['by'], 0, 8)) ?>...
      <?= $ctx['type'] === 'comment' ? 'replied' : 'reshared' ?>
    </span>
  </div>
  <?php endif; ?>

  <div class="post-card" id="post-<?= $shortHash ?>">
    <div class="post-avatar" style="background:<?= $color ?>;"><?= htmlspecialchars($initials) ?></div>
    <div class="post-main">
      <div class="post-header">
        <span class="post-author" title="<?= htmlspecialchars($pk) ?>"><?= htmlspecialchars($display) ?></span>
        <?php if ($post['content_type'] !== 'post'): ?>
        <span class="post-type type-<?= htmlspecialchars($post['content_type']) ?>"><?= htmlspecialchars($post['content_type']) ?></span>
        <?php endif; ?>
        <span class="post-time" data-ts="<?= htmlspecialchars((string)$post['timestamp']) ?>" title="<?= fmt_time($post['timestamp']) ?>">
          <?= fmt_time($post['timestamp']) ?>
        </span>
      </div>

      <?php if ($post['content_type'] === 'reshare' && !empty($post['metadata']['reshared_from'])): ?>
      <div class="reshare-notice">
        reshared from <span class="author-key" title="<?= htmlspecialchars($post['metadata']['reshared_from']) ?>"><?= htmlspecialchars(substr($post['metadata']['reshared_from'], 0, 8)) ?>...</span>
      </div>
      <?php endif; ?>

      <p class="post-body"><?= htmlspecialchars($post['body']) ?></p>

      <div class="post-actions">
        <button
          class="comment-toggle"
          hx-get="/feed/posts/<?= htmlspecialchars($post['content_hash']) ?>/comments"
          hx-target="#comments-<?= $shortHash ?>"
          hx-swap="outerHTML"
          hx-trigger="click once"
        >
          <svg viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path></svg>
          Reply
        </button>
        <button
          hx-post="/api/posts/<?= htmlspecialchars($post['content_hash']) ?>/reshare"
          hx-target="#post-<?= $shortHash ?>"
          hx-swap="outerHTML"
          hx-confirm="Reshare this post?"
        >
          <svg viewBox="0 0 24 24"><polyline points="17 1 21 5 17 9"></polyline><path d="M3 11V9a4 4 0 0 1 4-4h14"></path><polyline points="7 23 3 19 7 15"></polyline><path d="M21 13v2a4 4 0 0 1-4 4H3"></path></svg>
          Reshare
        </button>
      </div>

      <div id="comments-<?= $shortHash ?>"></div>
    </div>
  </div>
  <?php endforeach; ?>
<?php else: ?>
  <div class="empty-feed">
    <p>No posts yet. <a href="/compose">Write the first one.</a></p>
  </div>
<?php endif; ?>
