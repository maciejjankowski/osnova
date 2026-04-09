<?php
/**
 * Identity page.
 * Expects: $identity (array with public_key, display_name, created_at), $endpoint
 */
function fmt_time_id(float $ts): string {
    return date('Y-m-d H:i:s', (int)$ts);
}
?>
<h2>Node Identity</h2>

<article>
  <dl>
    <dt>Display Name</dt>
    <dd><strong><?= htmlspecialchars($identity['display_name']) ?></strong></dd>

    <dt>Public Key</dt>
    <dd>
      <code id="pubkey" class="pubkey-full"><?= htmlspecialchars($identity['public_key']) ?></code>
      <button
        class="outline small copy-btn"
        onclick="navigator.clipboard.writeText(document.getElementById('pubkey').textContent).then(() => this.textContent = 'Copied!')"
      >Copy</button>
    </dd>

    <dt>Node Endpoint</dt>
    <dd><code><?= htmlspecialchars($endpoint) ?></code></dd>

    <dt>Created</dt>
    <dd><?= fmt_time_id($identity['created_at']) ?></dd>
  </dl>
</article>

<article>
  <h4>Sync Status</h4>
  <button
    hx-post="/api/sync/pull"
    hx-target="#sync-result"
    hx-swap="innerHTML"
    class="outline"
  >Trigger Gossip Round</button>
  <div id="sync-result" class="sync-result"></div>
</article>
