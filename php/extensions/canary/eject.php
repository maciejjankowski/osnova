<?php
/**
 * Eject / Emergency controls page.
 * Node-level signals (canary/eject) still work via the server.
 * Client-side eject clears the keypair from localStorage.
 */
?>
<h2>Emergency Controls</h2>

<div class="eject-warning">
  <strong>Warning:</strong> These actions notify your trust ring and cannot be undone.
</div>

<article class="canary-section">
  <h3>Canary Signal</h3>
  <p>Signals your ring that <strong>this node is compromised</strong>. Use if you are captured, under coercion, or your keys may be exposed. Recipients should treat all your content as potentially manipulated.</p>

  <form id="canary-form">
    <label>
      Message (optional)
      <input type="text" id="canary-message" name="message" placeholder="Optional context for your ring..." />
    </label>
    <button type="button" class="canary-btn" onclick="sendCanary()">Signal COMPROMISED to Ring</button>
  </form>

  <div id="canary-result"></div>
</article>

<hr />

<article class="eject-section">
  <h3>Eject from Network</h3>
  <p>Packages your content and peer list, notifies your ring, and prepares this node for disappearance. Use for planned exit or when continued participation becomes unsafe.</p>

  <form id="eject-form">
    <label>
      Closing Message
      <textarea id="closing-message" name="closing_message" rows="4" placeholder="Final message for your ring (optional)..."></textarea>
    </label>
    <label>
      <input type="checkbox" id="include-provenance" name="include_provenance" checked />
      Include provenance (keep author attribution in packaged content)
    </label>
    <button type="button" class="eject-btn" onclick="sendEject()">Eject from Network</button>
  </form>

  <div id="eject-result"></div>
</article>

<hr />

<article>
  <h3>Clear Local Identity</h3>
  <p>Removes your keypair from this browser's localStorage. Your posts on nodes remain - only your ability to sign new content from this device is erased. Download a backup first if you want to recover.</p>

  <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
    <button class="outline" onclick="backupAndEject()">Backup then Clear Identity</button>
    <button class="eject-btn" onclick="clearIdentity()">Clear Identity Now (no backup)</button>
  </div>
  <div id="local-eject-result" style="margin-top:0.5rem;"></div>
</article>

<script>
  function sendCanary() {
    const btn = document.querySelector('.canary-btn');
    if (!confirm('Signal your ring that this node is COMPROMISED? This cannot be undone.')) return;

    btn.setAttribute('aria-busy', 'true');
    btn.disabled = true;

    fetch('/api/signals/canary', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        message: document.getElementById('canary-message').value,
        severity: 'critical'
      })
    })
    .then(r => r.json())
    .then(data => {
      document.getElementById('canary-result').innerHTML =
        '<ins>Canary signal sent. Ring notified at ' + new Date(data.timestamp * 1000).toLocaleString() + '</ins>';
    })
    .catch(() => {
      document.getElementById('canary-result').innerHTML = '<ins class="error">Failed to send canary signal.</ins>';
    })
    .finally(() => {
      btn.removeAttribute('aria-busy');
      btn.disabled = false;
    });
  }

  function sendEject() {
    const btn = document.querySelector('.eject-btn');
    if (!confirm('EJECT from the network? This will package your content, notify your ring, and cannot be undone.')) return;

    btn.setAttribute('aria-busy', 'true');
    btn.disabled = true;

    fetch('/api/signals/eject', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({
        closing_message: document.getElementById('closing-message').value,
        include_provenance: document.getElementById('include-provenance').checked,
      })
    })
    .then(r => r.json())
    .then(data => {
      document.getElementById('eject-result').innerHTML =
        '<ins>Ejected. ' + data.entries_packaged + ' entries packaged, ' +
        data.peers_notified + ' peers notified.</ins>';
    })
    .catch(() => {
      document.getElementById('eject-result').innerHTML = '<ins class="error">Eject failed.</ins>';
    })
    .finally(() => {
      btn.removeAttribute('aria-busy');
      btn.disabled = false;
    });
  }

  function backupAndEject() {
    // Download backup then clear
    const json = Osnova.exportKeypair();
    if (json) {
      const blob = new Blob([json], {type: 'application/json'});
      const url  = URL.createObjectURL(blob);
      const a    = document.createElement('a');
      a.href     = url;
      a.download = 'osnova-keypair-backup.json';
      a.click();
      URL.revokeObjectURL(url);
    }
    setTimeout(() => {
      if (confirm('Backup downloaded. Clear identity from this browser now?')) {
        Osnova.eject();
        document.getElementById('local-eject-result').innerHTML =
          '<ins>Local identity cleared. <a href="/setup">Setup new identity</a></ins>';
        Osnova.init();
      }
    }, 500);
  }

  function clearIdentity() {
    if (!confirm('Clear your local identity? This cannot be undone without a backup.')) return;
    Osnova.eject();
    document.getElementById('local-eject-result').innerHTML =
      '<ins>Local identity cleared. <a href="/setup">Setup new identity</a></ins>';
    Osnova.init();
  }
</script>
