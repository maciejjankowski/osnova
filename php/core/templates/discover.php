<?php
/**
 * Discovery / triangulation page.
 * Expects: $triads (list of triads with content_hash stripped)
 */
?>
<h2>Discovery Triads</h2>

<p>Create message/countermessage/challenge triads to triangulate content. Only ring members with context can resolve the challenge - machines see two equally valid candidates.</p>

<article>
  <h4>Create Triad</h4>
  <form id="create-triad-form">
    <label>
      Content Hash
      <input type="text" name="content_hash" id="triad-hash" placeholder="sha256 hash of the content entry" required />
    </label>
    <label>
      Decoy Key (optional - auto-selected from peers if blank)
      <input type="text" name="decoy_key" id="triad-decoy" placeholder="hex-encoded Ed25519 public key" />
    </label>
    <button type="submit">Create Triad</button>
  </form>
  <div id="triad-result"></div>
</article>

<hr />

<h4>Your Triads</h4>

<?php if (!empty($triads)): ?>
<?php foreach ($triads as $triad): ?>
<article>
  <dl>
    <dt>Triad ID</dt>
    <dd><code><?= htmlspecialchars(substr($triad['triad_id'], 0, 16)) ?>...</code></dd>

    <dt>Real Holder</dt>
    <dd><code><?= htmlspecialchars(substr($triad['real_holder_key'] ?? '', 0, 16)) ?>...</code></dd>

    <dt>Decoy</dt>
    <dd><code><?= htmlspecialchars(substr($triad['decoy_key'] ?? '', 0, 16)) ?>...</code></dd>

    <dt>Message Fragment</dt>
    <dd><code><?= htmlspecialchars(substr($triad['message']['fragment'] ?? '', 0, 32)) ?>...</code></dd>

    <dt>Challenge Fragment</dt>
    <dd><code><?= htmlspecialchars(substr($triad['challenge']['fragment'] ?? '', 0, 32)) ?>...</code></dd>

    <dt>Created</dt>
    <dd><?= date('Y-m-d H:i', (int)($triad['created_at'] ?? 0)) ?></dd>
  </dl>

  <details>
    <summary>Resolve Challenge</summary>
    <form onsubmit="resolveTriad(event, '<?= htmlspecialchars($triad['triad_id']) ?>')">
      <label>
        Content Hash (required to prove you know it)
        <input type="text" name="content_hash" placeholder="The actual content hash" required />
      </label>
      <label>
        Chosen Candidate
        <input type="text" name="chosen" placeholder="hex public key you believe holds the content" required />
      </label>
      <button type="submit" class="outline">Verify Resolution</button>
      <span class="resolve-result-<?= htmlspecialchars($triad['triad_id']) ?>"></span>
    </form>
  </details>
</article>
<?php endforeach; ?>
<?php else: ?>
<p>No triads created yet.</p>
<?php endif; ?>

<script>
  document.getElementById('create-triad-form').addEventListener('submit', function(evt) {
    evt.preventDefault();
    const data = {
      content_hash: document.getElementById('triad-hash').value,
      decoy_key: document.getElementById('triad-decoy').value || undefined,
    };
    fetch('/api/discovery/create', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(d => {
      document.getElementById('triad-result').innerHTML =
        '<ins>Triad created: <code>' + d.triad_id.substring(0,16) + '...</code> <a href="/discover">Refresh</a></ins>';
    })
    .catch(() => {
      document.getElementById('triad-result').innerHTML = '<ins class="error">Failed to create triad.</ins>';
    });
  });

  function resolveTriad(evt, triadId) {
    evt.preventDefault();
    const form = evt.target;
    const data = {
      triad_id: triadId,
      chosen_candidate: form.querySelector('[name=chosen]').value,
      content_hash: form.querySelector('[name=content_hash]').value,
    };
    fetch('/api/discovery/resolve', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(r => r.json())
    .then(d => {
      const el = document.querySelector('.resolve-result-' + triadId);
      el.innerHTML = d.valid ? ' <ins>Valid - correct candidate identified.</ins>' : ' <mark>Invalid - wrong candidate.</mark>';
    });
  }
</script>
