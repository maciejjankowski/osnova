/**
 * osnova.js - Client-side identity and signing
 *
 * Requires: nacl (tweetnacl) loaded before this script.
 * No npm, no build step. Plain JS.
 *
 * Content hash format must match PHP crypto_content_hash() and Python:
 *   "{author_key}:{content_type}:{body}:{parent_hash}:{timestamp}"
 * where parent_hash = "None" when null, timestamp = py_float_str(f)
 */

// ---------------------------------------------------------------------------
// Hex helpers
// ---------------------------------------------------------------------------

function toHex(bytes) {
    return Array.from(bytes).map(b => b.toString(16).padStart(2, '0')).join('');
}

function hexToBytes(hex) {
    const len = hex.length;
    const bytes = new Uint8Array(len / 2);
    for (let i = 0; i < len; i += 2) {
        bytes[i / 2] = parseInt(hex.substring(i, i + 2), 16);
    }
    return bytes;
}

// ---------------------------------------------------------------------------
// Python float string formatting
// Must produce identical output to PHP py_float_str() and Python str(float).
// Rule: round to 6 decimals, strip trailing zeros, keep at least ".0"
// ---------------------------------------------------------------------------

function pyFloatStr(f) {
    // Round to 6 decimal places
    let rounded = Math.round(f * 1e6) / 1e6;
    // Format with 6 decimal places
    let s = rounded.toFixed(6);
    // Strip trailing zeros after the decimal point
    s = s.replace(/(\.\d*?)0+$/, '$1');
    // Ensure at least one decimal digit
    if (s.endsWith('.')) s += '0';
    return s;
}

// ---------------------------------------------------------------------------
// SHA-256 via Web Crypto (async)
// ---------------------------------------------------------------------------

async function sha256Hex(str) {
    const buf = new TextEncoder().encode(str);
    const hashBuf = await crypto.subtle.digest('SHA-256', buf);
    return toHex(new Uint8Array(hashBuf));
}

// ---------------------------------------------------------------------------
// Relative time helper
// ---------------------------------------------------------------------------

function relativeTime(timestamp) {
    const now = Date.now() / 1000;
    const diff = Math.floor(now - timestamp);
    if (diff < 60) return diff + 's';
    if (diff < 3600) return Math.floor(diff / 60) + 'm';
    if (diff < 86400) return Math.floor(diff / 3600) + 'h';
    if (diff < 604800) return Math.floor(diff / 86400) + 'd';
    return Math.floor(diff / 604800) + 'w';
}

// ---------------------------------------------------------------------------
// Osnova - main module
// ---------------------------------------------------------------------------

const Osnova = {

    // ------------------------------------------------------------------------
    // Identity management
    // ------------------------------------------------------------------------

    /** Returns the stored keypair from localStorage, or generates a new one. */
    getKeypair() {
        const stored = localStorage.getItem('osnova_keypair');
        if (stored) {
            try { return JSON.parse(stored); } catch (e) { /* corrupt - regenerate */ }
        }
        const kp = nacl.sign.keyPair();
        const data = {
            publicKey:   toHex(kp.publicKey),
            secretKey:   toHex(kp.secretKey),  // 64-byte sodium-style (seed||pk)
            displayName: 'Anonymous',
            createdAt:   Date.now(),
        };
        localStorage.setItem('osnova_keypair', JSON.stringify(data));
        return data;
    },

    /** Get hex public key. */
    getPublicKey() {
        return this.getKeypair().publicKey;
    },

    /** Get display name. */
    getDisplayName() {
        return this.getKeypair().displayName || 'Anonymous';
    },

    /** Set display name (persists to localStorage). */
    setDisplayName(name) {
        const kp = this.getKeypair();
        kp.displayName = name;
        localStorage.setItem('osnova_keypair', JSON.stringify(kp));
    },

    /** Generate and store a fresh keypair (replaces existing). */
    generateNewKeypair() {
        const kp = nacl.sign.keyPair();
        const data = {
            publicKey:   toHex(kp.publicKey),
            secretKey:   toHex(kp.secretKey),
            displayName: 'Anonymous',
            createdAt:   Date.now(),
        };
        localStorage.setItem('osnova_keypair', JSON.stringify(data));
        return data;
    },

    /** Export keypair JSON string (for download/backup). */
    exportKeypair() {
        return localStorage.getItem('osnova_keypair') || null;
    },

    /** Import keypair from JSON string. Returns true on success. */
    importKeypair(json) {
        try {
            const parsed = JSON.parse(json);
            if (!parsed.publicKey || !parsed.secretKey) return false;
            localStorage.setItem('osnova_keypair', JSON.stringify(parsed));
            return true;
        } catch (e) {
            return false;
        }
    },

    /** Clear keypair from localStorage (client-side eject). */
    eject() {
        localStorage.removeItem('osnova_keypair');
    },

    // ------------------------------------------------------------------------
    // Node configuration (which dispatcher nodes to post to)
    // ------------------------------------------------------------------------

    getNodes() {
        const stored = localStorage.getItem('osnova_nodes');
        if (stored) {
            try { return JSON.parse(stored); } catch (e) {}
        }
        // Default: current host
        return [window.location.origin];
    },

    setNodes(nodes) {
        localStorage.setItem('osnova_nodes', JSON.stringify(nodes));
    },

    addNode(endpoint) {
        const nodes = this.getNodes();
        const clean = endpoint.replace(/\/$/, '');
        if (!nodes.includes(clean)) {
            nodes.push(clean);
            this.setNodes(nodes);
        }
    },

    removeNode(endpoint) {
        const nodes = this.getNodes().filter(n => n !== endpoint);
        this.setNodes(nodes);
    },

    // ------------------------------------------------------------------------
    // Content hash (mirrors PHP crypto_content_hash / Python ContentEntry)
    // ------------------------------------------------------------------------

    /**
     * Compute content hash. Async because it uses crypto.subtle.
     * Must produce the same hex as PHP crypto_content_hash().
     *
     * payload = "{author_key}:{content_type}:{body}:{parent_hash}:{timestamp}"
     * parent_hash = "None" when null (Python str(None) compat)
     * timestamp   = pyFloatStr(f)
     */
    async contentHash(authorKey, contentType, body, parentHash, timestamp) {
        const ph = (parentHash === null || parentHash === undefined || parentHash === '') ? 'None' : parentHash;
        const tsStr = pyFloatStr(timestamp);
        const payload = `${authorKey}:${contentType}:${body}:${ph}:${tsStr}`;
        return await sha256Hex(payload);
    },

    // ------------------------------------------------------------------------
    // Signing
    // ------------------------------------------------------------------------

    /**
     * Create a fully signed entry ready to POST to /api/posts/signed.
     * Async because contentHash uses crypto.subtle.
     */
    async createSignedEntry(body, contentType, parentHash, metadata) {
        const kp = this.getKeypair();
        // Use microtime-equivalent: seconds as float with microsecond precision
        const timestamp = Date.now() / 1000.0;
        const hash = await this.contentHash(kp.publicKey, contentType, body, parentHash, timestamp);

        // nacl.sign.detached signs the message bytes
        const msgBytes = new TextEncoder().encode(hash);
        const sigBytes = nacl.sign.detached(msgBytes, hexToBytes(kp.secretKey));

        return {
            author_key:   kp.publicKey,
            content_type: contentType,
            body:         body,
            parent_hash:  parentHash || null,
            metadata:     metadata || {},
            timestamp:    timestamp,
            signature:    toHex(sigBytes),
            content_hash: hash,
        };
    },

    // ------------------------------------------------------------------------
    // Network
    // ------------------------------------------------------------------------

    /** POST a pre-signed entry to a single node. Returns {ok, data, node}. */
    async publishToNode(nodeEndpoint, entry) {
        const url = nodeEndpoint.replace(/\/$/, '') + '/api/posts/signed';
        try {
            const resp = await fetch(url, {
                method:  'POST',
                headers: {'Content-Type': 'application/json'},
                body:    JSON.stringify(entry),
            });
            const data = await resp.json();
            return { ok: resp.ok, status: resp.status, data, node: nodeEndpoint };
        } catch (e) {
            return { ok: false, status: 0, data: { detail: e.message }, node: nodeEndpoint };
        }
    },

    /** Publish to all configured nodes in parallel. Returns array of results. */
    async publish(entry, nodes) {
        const targets = nodes || this.getNodes();
        return await Promise.allSettled(targets.map(n => this.publishToNode(n, entry)));
    },

    // ------------------------------------------------------------------------
    // Convenience: create + publish in one call
    // ------------------------------------------------------------------------

    async post(body, contentType, parentHash, metadata, nodes) {
        const entry = await this.createSignedEntry(body, contentType || 'post', parentHash, metadata);
        const results = await this.publish(entry, nodes);
        return { entry, results };
    },

    // ------------------------------------------------------------------------
    // QR Profile Token
    // One token, three sections: identity, preferred nodes, trusted peers.
    // The SECRET KEY is NOT in this token - it's the public profile card.
    // ------------------------------------------------------------------------

    /** Build the public profile token (no secret key). */
    getProfileToken() {
        const kp = this.getKeypair();
        return JSON.stringify({
            v: 1,
            id: {
                pk: kp.publicKey,
                name: kp.displayName || 'Anonymous',
                created: kp.createdAt,
            },
            nodes: this.getNodes(),
            ring: [],  // populated later when trust ring is established
        });
    },

    /** Render a QR code into a target DOM element. */
    renderQR(targetId, data, size) {
        const el = document.getElementById(targetId);
        if (!el || typeof qrcode === 'undefined') return;
        // qrcode-generator library: typeNumber=0 (auto), errorCorrection='M'
        const qr = qrcode(0, 'M');
        qr.addData(data);
        qr.make();
        el.innerHTML = qr.createSvgTag({ cellSize: size || 4, margin: 2 });
    },

    /** Render the profile QR (public card). */
    renderProfileQR(targetId) {
        this.renderQR(targetId, this.getProfileToken(), 3);
    },

    /** Parse a scanned/imported profile token. Returns parsed object or null. */
    parseProfileToken(json) {
        try {
            const t = JSON.parse(json);
            if (t.v !== 1 || !t.id || !t.id.pk) return null;
            return t;
        } catch (e) {
            return null;
        }
    },

    /** Import profile from a token (updates identity + nodes, NOT secret key). */
    importProfileToken(token) {
        if (!token || !token.id) return false;
        // Only update display name and nodes - don't touch keypair
        // (the profile token doesn't contain the secret key)
        if (token.id.name) this.setDisplayName(token.id.name);
        if (token.nodes && token.nodes.length > 0) this.setNodes(token.nodes);
        return true;
    },

    // ------------------------------------------------------------------------
    // Init: update UI identity indicator if present
    // ------------------------------------------------------------------------

    init() {
        const kp = this.getKeypair();
        const indicator = document.getElementById('osnova-identity');
        if (indicator) {
            const name = kp.displayName || 'Anonymous';
            const shortKey = kp.publicKey.substring(0, 8) + '...';
            indicator.textContent = name;
            indicator.setAttribute('data-shortkey', shortKey);
            indicator.title = kp.publicKey;
        }
        // Update all relative timestamps on page
        document.querySelectorAll('[data-ts]').forEach(el => {
            const ts = parseFloat(el.getAttribute('data-ts'));
            if (!isNaN(ts)) el.textContent = relativeTime(ts);
        });
    },
};

// Auto-init on DOMContentLoaded
document.addEventListener('DOMContentLoaded', () => Osnova.init());
