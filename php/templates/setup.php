<?php
/**
 * Setup page - browser-side identity management.
 * No server-side user state. Everything lives in localStorage.
 */
?>
<h2 style="font-size:1.1rem;font-weight:700;margin-bottom:1rem;">Identity</h2>

<div class="setup-section">
  <h3>Your Key</h3>
  <p>Stored in your browser only. The server never sees your private key.</p>

  <div class="identity-box">
    <label>Public Key</label>
    <code class="pubkey-full" id="setup-pubkey">loading...</code>
    <button class="outline copy-btn" onclick="copyPubkey()">Copy</button>
  </div>

  <div style="margin-top:0.75rem;">
    <label for="setup-display-name" style="font-size:0.82rem;font-weight:600;display:block;margin-bottom:0.4rem;">Display Name</label>
    <div class="grid" style="grid-template-columns:1fr auto;gap:0.5rem;align-items:end;">
      <input type="text" id="setup-display-name" placeholder="Anonymous" maxlength="64" />
      <button class="outline" onclick="saveName()">Save</button>
    </div>
    <small id="setup-name-result" style="color:#2ecc71;"></small>
  </div>
</div>

<div class="setup-section">
  <h3>Nodes</h3>
  <p>Your posts are published to these dispatcher nodes. Add 3-6 for resilience.</p>

  <div id="nodes-list"></div>

  <div class="grid" style="grid-template-columns:1fr auto;gap:0.5rem;align-items:end;margin-top:0.75rem;">
    <input type="url" id="new-node-input" placeholder="https://example.com" />
    <button class="outline" onclick="addNode()">Add</button>
  </div>
  <small id="nodes-result"></small>
</div>

<div class="setup-section">
  <h3>Profile Card (QR)</h3>
  <p>Shows your public identity and preferred nodes. <strong>No secret key</strong> - safe to share.</p>

  <div id="profile-qr"></div>

  <div style="margin-top:0.75rem;display:flex;gap:0.5rem;flex-wrap:wrap;">
    <button class="outline" onclick="downloadQR()">Download PNG</button>
    <button class="outline" onclick="copyProfileToken()">Copy Token</button>
  </div>
  <small id="qr-result" style="display:block;margin-top:0.5rem;"></small>
</div>

<div class="setup-section">
  <h3>Import Peer Token</h3>
  <p>Paste a profile token JSON to add someone as a peer.</p>
  <textarea id="import-token-input" rows="3" placeholder='{"v":1,"id":{"pk":"...","name":"..."},"nodes":["..."]}'></textarea>
  <button class="outline" onclick="importToken()" style="margin-top:0.5rem;">Import</button>
  <small id="import-token-result" style="display:block;margin-top:0.5rem;"></small>
</div>

<div class="setup-section">
  <h3>Backup &amp; Migration</h3>

  <div style="display:flex;gap:0.75rem;flex-wrap:wrap;">
    <button class="outline" onclick="exportKeypair()">Download Full Backup</button>
    <label class="outline" style="cursor:pointer;padding:0.45rem 0.75rem;border:1px solid rgba(255,255,255,0.15);border-radius:8px;font-size:0.88rem;">
      Import Backup
      <input type="file" id="import-file" accept=".json,application/json" style="display:none;" onchange="importKeypair(this)" />
    </label>
  </div>
  <small id="backup-result" style="display:block;margin-top:0.5rem;"></small>
</div>

<div class="setup-section eject-section">
  <h3>Generate New Keypair</h3>
  <p><strong>Warning:</strong> Replaces your current keypair. Back up first.</p>
  <button class="eject-btn" onclick="generateNew()">Generate New Keypair</button>
  <small id="gen-result" style="display:block;margin-top:0.5rem;"></small>
</div>

<script>
  function renderSetup() {
    const kp = Osnova.getKeypair();
    document.getElementById('setup-pubkey').textContent = kp.publicKey;
    document.getElementById('setup-display-name').value = kp.displayName || '';
    renderNodes();
  }

  function copyPubkey() {
    const pk = Osnova.getPublicKey();
    navigator.clipboard.writeText(pk).then(() => {
      document.getElementById('setup-pubkey').textContent = pk + ' (copied!)';
      setTimeout(() => document.getElementById('setup-pubkey').textContent = pk, 1500);
    });
  }

  function saveName() {
    const name = document.getElementById('setup-display-name').value.trim();
    if (!name) return;
    Osnova.setDisplayName(name);
    document.getElementById('setup-name-result').textContent = 'Saved.';
    Osnova.init();
    setTimeout(() => document.getElementById('setup-name-result').textContent = '', 2000);
  }

  function renderNodes() {
    const nodes = Osnova.getNodes();
    const list  = document.getElementById('nodes-list');
    if (nodes.length === 0) {
      list.innerHTML = '<p class="no-comments">No nodes configured.</p>';
      return;
    }
    list.innerHTML = nodes.map(n => `
      <div class="peer-card">
        <span class="peer-endpoint">${escHtml(n)}</span>
        <button class="outline small" onclick="removeNode(${JSON.stringify(n)})">Remove</button>
      </div>
    `).join('');
  }

  function addNode() {
    const input = document.getElementById('new-node-input');
    const val   = input.value.trim().replace(/\/$/, '');
    if (!val) return;
    try { new URL(val); } catch(e) {
      document.getElementById('nodes-result').textContent = 'Invalid URL.';
      return;
    }
    Osnova.addNode(val);
    input.value = '';
    renderNodes();
    document.getElementById('nodes-result').textContent = 'Added.';
    setTimeout(() => document.getElementById('nodes-result').textContent = '', 2000);
  }

  function removeNode(endpoint) {
    Osnova.removeNode(endpoint);
    renderNodes();
  }

  function exportKeypair() {
    const json = Osnova.exportKeypair();
    if (!json) return;
    const blob = new Blob([json], {type: 'application/json'});
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'osnova-keypair.json';
    a.click();
    URL.revokeObjectURL(url);
    document.getElementById('backup-result').textContent = 'Downloaded.';
    setTimeout(() => document.getElementById('backup-result').textContent = '', 2000);
  }

  function importKeypair(input) {
    const file = input.files[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      const ok = Osnova.importKeypair(e.target.result);
      if (ok) {
        document.getElementById('backup-result').textContent = 'Keypair imported.';
        renderSetup();
        Osnova.init();
      } else {
        document.getElementById('backup-result').textContent = 'Invalid keypair file.';
      }
    };
    reader.readAsText(file);
  }

  function generateNew() {
    if (!confirm('Generate a new keypair? Your current identity will be replaced. Back up first.')) return;
    Osnova.generateNewKeypair();
    renderSetup();
    Osnova.init();
    renderQR();
    document.getElementById('gen-result').textContent = 'New keypair generated.';
    setTimeout(() => document.getElementById('gen-result').textContent = '', 3000);
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }

  function renderQR() {
    Osnova.renderProfileQR('profile-qr');
  }

  function downloadQR() {
    const svg = document.querySelector('#profile-qr svg');
    if (!svg) return;
    const svgData = new XMLSerializer().serializeToString(svg);
    const canvas = document.createElement('canvas');
    const img = new Image();
    img.onload = () => {
      canvas.width = img.width * 2;
      canvas.height = img.height * 2;
      const ctx = canvas.getContext('2d');
      ctx.fillStyle = '#fff';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      const a = document.createElement('a');
      a.download = 'osnova-profile.png';
      a.href = canvas.toDataURL('image/png');
      a.click();
    };
    img.src = 'data:image/svg+xml;base64,' + btoa(svgData);
    document.getElementById('qr-result').textContent = 'Downloaded.';
    setTimeout(() => document.getElementById('qr-result').textContent = '', 2000);
  }

  function copyProfileToken() {
    const token = Osnova.getProfileToken();
    navigator.clipboard.writeText(token).then(() => {
      document.getElementById('qr-result').textContent = 'Token copied.';
      setTimeout(() => document.getElementById('qr-result').textContent = '', 2000);
    });
  }

  function importToken() {
    const raw = document.getElementById('import-token-input').value.trim();
    const token = Osnova.parseProfileToken(raw);
    if (!token) {
      document.getElementById('import-token-result').textContent = 'Invalid token.';
      return;
    }
    if (token.nodes && token.nodes.length > 0) {
      token.nodes.forEach(n => Osnova.addNode(n));
    }
    document.getElementById('import-token-result').innerHTML =
      'Peer: <strong>' + escHtml(token.id.name) + '</strong> [' + token.id.pk.substring(0, 8) + '...]' +
      (token.nodes.length > 0 ? ' - ' + token.nodes.length + ' node(s) added.' : '');
    document.getElementById('import-token-input').value = '';
    renderNodes();
  }

  document.addEventListener('DOMContentLoaded', () => { renderSetup(); renderQR(); });
</script>
