<?php
/**
 * Compose page - create a new post.
 * Signing happens in the browser via osnova.js (Ed25519 / tweetnacl).
 * The signed entry is posted to all configured nodes via Osnova.publish().
 */
?>
<h2 style="font-size:1.1rem;font-weight:700;margin-bottom:1rem;">New post</h2>

<div class="compose-container">
  <article>
    <div class="compose-who">
      <div class="compose-avatar" id="compose-avatar">?</div>
      <span class="compose-name" id="compose-name">Anonymous</span>
    </div>

    <form id="compose-form" onsubmit="submitPost(event)">
      <textarea
        id="body"
        name="body"
        rows="4"
        placeholder="What truth needs to be said?"
        required
        autofocus
      ></textarea>

      <div class="compose-options">
        <label>
          <input type="checkbox" name="encode_riddle" value="1" id="encode-riddle" />
          PARDES layer
        </label>
        <button type="submit" id="compose-btn">Publish</button>
      </div>
    </form>

    <div id="compose-result"></div>
  </article>
</div>

<script>
  // Populate avatar / name from identity
  document.addEventListener('DOMContentLoaded', () => {
    const kp = Osnova.getKeypair();
    const name = kp.displayName || 'Anonymous';
    const pk   = kp.publicKey;

    // Avatar initials + color
    const initials = name.substring(0, 2).toUpperCase();
    const colors   = ['#7c6af7','#e85d75','#2ecc71','#3498db','#e67e22','#9b59b6','#1abc9c','#e74c3c'];
    const color    = colors[parseInt(pk.substring(0, 2), 16) % colors.length];

    const av = document.getElementById('compose-avatar');
    if (av) { av.textContent = initials; av.style.background = color; }

    const nm = document.getElementById('compose-name');
    if (nm) nm.textContent = name;
  });

  async function submitPost(evt) {
    evt.preventDefault();

    const btn  = document.getElementById('compose-btn');
    const text = document.getElementById('body').value.trim();
    if (!text) return;

    const encodeRiddle = document.getElementById('encode-riddle').checked;
    const metadata     = encodeRiddle ? { encode_riddle: true } : {};

    btn.setAttribute('aria-busy', 'true');
    btn.disabled = true;

    const resultEl = document.getElementById('compose-result');
    resultEl.innerHTML = '';

    try {
      const entry   = await Osnova.createSignedEntry(text, 'post', null, metadata);
      const nodes   = Osnova.getNodes();
      const results = await Osnova.publish(entry, nodes);

      let ok = 0, fail = 0;
      const lines = results.map(r => {
        const res = r.value || { ok: false, node: '?', data: { detail: r.reason } };
        if (res.ok) { ok++; return '<span style="color:#2ecc71">' + escHtml(res.node) + ': ok</span>'; }
        fail++;
        const detail = res.data && res.data.detail ? res.data.detail : 'failed';
        return '<span class="error">' + escHtml(res.node) + ': ' + escHtml(String(detail)) + '</span>';
      });

      if (ok > 0) {
        resultEl.innerHTML =
          '<p>Published to ' + ok + '/' + nodes.length + ' node(s). <a href="/feed">View feed &rarr;</a></p>' +
          lines.join('<br>');
        evt.target.reset();
      } else {
        resultEl.innerHTML = '<p class="error">Failed to publish to any node.</p>' + lines.join('<br>');
      }
    } catch (e) {
      resultEl.innerHTML = '<p class="error">Error: ' + escHtml(e.message) + '</p>';
    } finally {
      btn.removeAttribute('aria-busy');
      btn.disabled = false;
    }
  }

  function escHtml(s) {
    return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
</script>
