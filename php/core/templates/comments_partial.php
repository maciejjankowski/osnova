<?php
/**
 * Comments partial - returned for HTMX lazy-load requests.
 * Expects: $comments (array), $parent_hash (string)
 */
$avatar_colors = ['#7c6af7','#e85d75','#2ecc71','#3498db','#e67e22','#9b59b6','#1abc9c','#e74c3c'];
function comment_avatar_color(string $pk, array $colors): string {
    return $colors[hexdec(substr($pk, 0, 2)) % count($colors)];
}
?>
<div class="comments-section" id="comments-<?= htmlspecialchars(substr($parent_hash, 0, 8)) ?>">
  <?php if (!empty($comments)): ?>
    <?php foreach ($comments as $comment): ?>
    <?php
      $cpk     = $comment['author_key'];
      $cshort  = substr($cpk, 0, 8) . '...';
      $cinit   = strtoupper(substr($cshort, 0, 2));
      $ccolor  = comment_avatar_color($cpk, $avatar_colors);
      $ctime   = date('H:i', (int)$comment['timestamp']);
    ?>
    <div class="comment-card">
      <div class="comment-avatar" style="background:<?= $ccolor ?>;"><?= htmlspecialchars($cinit) ?></div>
      <div class="comment-main">
        <div class="comment-meta">
          <span class="author-key" title="<?= htmlspecialchars($cpk) ?>"><?= htmlspecialchars($cshort) ?></span>
          <span class="post-time" data-ts="<?= htmlspecialchars((string)$comment['timestamp']) ?>" title="<?= date('Y-m-d H:i', (int)$comment['timestamp']) ?>"><?= $ctime ?></span>
        </div>
        <p><?= htmlspecialchars($comment['body']) ?></p>
      </div>
    </div>
    <?php endforeach; ?>
  <?php else: ?>
    <p class="no-comments">No replies yet.</p>
  <?php endif; ?>

  <form class="comment-form" onsubmit="submitComment(event, '<?= htmlspecialchars($parent_hash) ?>')">
    <div class="grid">
      <input type="text" name="body" placeholder="Add a reply..." required />
      <button type="submit" class="outline small">Reply</button>
    </div>
  </form>
</div>

<script>
async function submitComment(evt, parentHash) {
  evt.preventDefault();
  const form = evt.target;
  const body = form.querySelector('[name=body]').value.trim();
  if (!body) return;

  let entry;
  try {
    entry = await Osnova.createSignedEntry(body, 'comment', parentHash, {});
  } catch (e) {
    alert('Signing error: ' + e.message);
    return;
  }

  const nodes = Osnova.getNodes();
  const results = await Promise.allSettled(
    nodes.map(n => Osnova.publishToNode(n, entry))
  );
  const anyOk = results.some(r => r.value && r.value.ok);
  if (anyOk) {
    form.reset();
    htmx.ajax('GET', '/feed/posts/' + parentHash + '/comments', {
      target: '#comments-' + parentHash.substring(0, 8),
      swap: 'outerHTML'
    });
  } else {
    alert('Failed to post reply to any node.');
  }
}
</script>
