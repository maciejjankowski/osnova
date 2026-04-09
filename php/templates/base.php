<?php
/**
 * Base HTML layout.
 * Usage: ob_start(); include 'feed.php'; $content = ob_get_clean();
 *        include 'base.php';
 *
 * Expected variables:
 *   $title  - page title suffix (default "Feed")
 *   $active - active nav link ('feed','compose','rings','identity','discover','eject','setup')
 *   $content - rendered page content (from ob_get_clean())
 */
$title  = $title  ?? 'Feed';
$active = $active ?? '';
?>
<!doctype html>
<html lang="en" data-theme="dark">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Osnova | <?= htmlspecialchars($title) ?></title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@picocss/pico@2/css/pico.min.css" />
  <link rel="stylesheet" href="/static/style.css" />
  <link rel="stylesheet" href="/static/css/osnova.css" />
  <script src="https://unpkg.com/htmx.org@2.0.4" defer></script>
  <script src="https://cdn.jsdelivr.net/npm/qrcode-generator@1.4.4/qrcode.min.js"></script>
  <!-- tweetnacl: Ed25519 in the browser, no npm needed -->
  <script src="https://cdn.jsdelivr.net/npm/tweetnacl@1.0.3/nacl-fast.min.js"></script>
  <script src="/static/js/stego.js" defer></script>
  <script src="/static/osnova.js" defer></script>
</head>
<body>
  <header class="container-fluid osnova-header">
    <nav>
      <ul>
        <li><strong class="osnova-logo"><a href="/feed">osnova</a></strong></li>
      </ul>
      <ul>
        <li><a href="/feed"     <?= $active === 'feed'     ? 'class="active"' : '' ?>>Feed</a></li>
        <li><a href="/compose"  <?= $active === 'compose'  ? 'class="active"' : '' ?>>Compose</a></li>
        <li><a href="/rings"    <?= $active === 'rings'    ? 'class="active"' : '' ?>>Rings</a></li>
        <li><a href="/gigs"     <?= $active === 'gigs'     ? 'class="active"' : '' ?>>💼 Gigs</a></li>
        <li><a href="/messages" <?= $active === 'messages' ? 'class="active"' : '' ?>>📬 Messages</a></li>
        <li><a href="/discover" <?= $active === 'discover' ? 'class="active"' : '' ?>>Discover</a></li>
        <li><a href="/eject"    class="eject-nav <?= $active === 'eject' ? 'active' : '' ?>">Eject</a></li>
      </ul>
      <ul>
        <!-- Identity indicator: populated by osnova.js from localStorage -->
        <li>
          <a href="/setup" id="osnova-identity-link" <?= $active === 'setup' ? 'class="active"' : '' ?>>
            <span id="osnova-identity" title="">...</span>
          </a>
        </li>
      </ul>
    </nav>
  </header>

  <main class="container">
    <?= $content ?? '' ?>
  </main>

  <footer class="container-fluid osnova-footer">
    <small>
      Osnova - decentralized truth network · 
      <a href="https://github.com/maciejjankowski/osnova" target="_blank" rel="noopener">GitHub</a>
    </small>
  </footer>
</body>
</html>
