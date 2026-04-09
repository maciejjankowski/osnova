<?php
/**
 * Rings page - trust ring management.
 * Expects: $stats (array), $peers_by_ring (array keyed by level)
 */
?>
<h2>Trust Rings</h2>

<div class="ring-stats grid">
  <?php foreach ($stats as $level => $count): ?>
  <div class="ring-stat ring-<?= htmlspecialchars($level) ?>">
    <strong><?= (int)$count ?></strong>
    <small><?= htmlspecialchars($level) ?></small>
  </div>
  <?php endforeach; ?>
</div>

<details open>
  <summary><strong>Add Peer</strong></summary>
  <article>
    <form id="add-peer-form">
      <div class="grid">
        <label>
          Public Key
          <input type="text" name="public_key" placeholder="hex-encoded Ed25519 key" required />
        </label>
        <label>
          Display Name
          <input type="text" name="display_name" placeholder="Alice Node" required />
        </label>
      </div>
      <div class="grid">
        <label>
          Endpoint
          <input type="text" name="endpoint" placeholder="https://peer.example.com" required />
        </label>
        <label>
          Ring Level
          <select name="ring_level" required>
            <option value="core">Core (~5)</option>
            <option value="inner">Inner (~15)</option>
            <option value="middle" selected>Middle (~50)</option>
            <option value="outer">Outer (~95)</option>
          </select>
        </label>
      </div>
      <button type="submit">Add Peer</button>
    </form>
    <div id="add-peer-result"></div>
  </article>
</details>

<div id="rings-list">
  <?php foreach (['core', 'inner', 'middle', 'outer'] as $level): ?>
  <?php $levelPeers = $peers_by_ring[$level] ?? []; ?>
  <?php if (!empty($levelPeers)): ?>
  <section>
    <p class="ring-level-heading"><?= ucfirst($level) ?> ring (<?= count($levelPeers) ?>/<?= RING_CAPS[$level] ?>)</p>
    <?php foreach ($levelPeers as $peer): ?>
    <article class="peer-card ring-border-<?= $level ?>">
      <div class="peer-info">
        <strong><?= htmlspecialchars($peer['display_name']) ?></strong>
        <span class="author-key" title="<?= htmlspecialchars($peer['public_key']) ?>"><?= htmlspecialchars(substr($peer['public_key'], 0, 16)) ?>...</span>
        <span class="peer-endpoint"><?= htmlspecialchars($peer['endpoint']) ?></span>
      </div>
      <div class="peer-actions">
        <button
          class="outline small"
          onclick="removePeer('<?= htmlspecialchars($peer['public_key']) ?>')"
        >Remove</button>
      </div>
    </article>
    <?php endforeach; ?>
  </section>
  <?php endif; ?>
  <?php endforeach; ?>
</div>

<script>
  document.getElementById('add-peer-form').addEventListener('submit', function(evt) {
    evt.preventDefault();
    const form = evt.target;
    const data = {
      public_key:   form.querySelector('[name=public_key]').value,
      display_name: form.querySelector('[name=display_name]').value,
      endpoint:     form.querySelector('[name=endpoint]').value,
      ring_level:   form.querySelector('[name=ring_level]').value,
    };

    fetch('/api/rings/peers', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(r => r.json().then(j => ({ok: r.ok, j})))
    .then(({ok, j}) => {
      if (ok) {
        document.getElementById('add-peer-result').innerHTML = '<ins>Peer added. <a href="/rings">Refresh</a></ins>';
        form.reset();
      } else {
        document.getElementById('add-peer-result').innerHTML = '<mark>Error: ' + (j.detail || 'Unknown error') + '</mark>';
      }
    });
  });

  function removePeer(key) {
    if (!confirm('Remove this peer?')) return;
    fetch('/api/rings/peers/' + encodeURIComponent(key), {method: 'DELETE'})
      .then(r => { if (r.ok) location.reload(); });
  }
</script>
