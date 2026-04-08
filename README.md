# Osnova

**Decentralized truth network with Dunbar-capped trust rings and PARDES integrity.**

Each user runs a node. Nodes gossip signed content over HTTP. Trust is local: you decide who's in your core, inner, middle, and outer rings. No blockchain, no global state, no consensus - just signed append-only logs and pull-based sync.

**Live instance:** https://va.evil1.org

---

## Feature Status (2026-04-08)

### ✅ Core (MVP + Discovery)
- Ed25519 client-side identity
- SQLite append-only content log
- Dunbar-capped trust rings (5/15/50/95)
- Gossip-based HTTP sync
- HTMX frontend
- Triangulated discovery protocol
- Signal layer (adversarial resilience)
- Eject protocol (leave with data)

### ✅ Near-term Features (6/6)
- **PARDES auto-tagging** - Detects SEED/PARAGRAPH/PAGE/DOCUMENT/SYSTEM layers
- **Middle ring filtering** - SEEDs + PARAGRAPHs only to middle ring
- **Persistent signals/triads** - SQLite storage, survives restarts
- **Lynchpin vocabulary** - Cultural context hints (Polish proverbs, biblical refs)
- **Discovery auto-distribution** - Auto-split keys across inner ring
- **Canary trap detection** - Tracks failed challenges, identifies outsiders

### ✅ Medium-term Features (7/7)
- **Credibility flagging** - Community-driven content verification
- **Ephemeral content** - TTL-based auto-purge
- **Polls + quadratic voting** - Democratic tools, tyranny-resistant
- **Liquid delegation** - Transitive vote delegation within rings
- **Bounty system** - Information requests with Shapley value rewards
- **Key rotation** - k-of-n threshold signature coordination

### 🔜 Long-term (Resilience)
- LoRa/Meshtastic transport
- Bluetooth mesh
- Packet radio (AX.25)
- Store-carry-forward (DTN)
- IPFS transport

---

## Quick Start

```bash
# 1. Clone and install
git clone <repo-url> osnova && cd osnova
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# 2. Configure your node (or use env vars directly)
export OSNOVA_NAME="alice"
export OSNOVA_PORT="8000"
export OSNOVA_DATA_DIR="/tmp/osnova-alice"

# 3. Run
python -m osnova.app
```

Node is up at `http://127.0.0.1:8000`. Interactive API docs at `/docs`.

---

## Multi-Node Demo

Launch a 3-node cluster (alice, bob, carol) with automatic peer registration:

```bash
bash scripts/launch_cluster.sh
```

The script:
- Starts alice (8000), bob (8001), carol (8002) in the background
- Waits for all three to be healthy
- Auto-registers each node as an inner-ring peer of the others
- Prints URLs and watches logs
- Kills all nodes on Ctrl+C

Manual peer registration (if running nodes separately):

```bash
# On alice (8000): add bob as an inner ring peer
curl -s -X POST http://127.0.0.1:8000/api/rings/peers \
  -H "Content-Type: application/json" \
  -d '{
    "public_key": "<bob-public-key>",
    "display_name": "bob",
    "ring_level": "inner",
    "endpoint": "http://127.0.0.1:8001"
  }'

# Trigger a manual gossip pull
curl -s -X POST http://127.0.0.1:8000/api/sync/pull
```

---

## Architecture

Each node is a self-contained FastAPI process with:

- **Identity** - Ed25519 keypair (PyNaCl). Generated once, persisted to `data_dir/identity.key`.
- **Content log** - append-only SQLite. All entries are signed by the author's key.
- **Trust rings** - four Dunbar-capped levels: core (~5), inner (~15), middle (~50), outer (~95). You control who's in each ring.
- **Gossip** - pull-based HTTP sync. Every N seconds the node pulls new entries from its core + inner peers.
- **Signals** - canary (node compromised) and eject (voluntary disappearance with content handoff).

See `CLAUDE.md` for design decisions. Full spec: `~/code/the-template/deliverables/areas/research/protocols/2026-04-05_decentralized-truth-network-architecture.md`.

### Ring Levels

| Level  | Cap | Sync behavior |
|--------|-----|---------------|
| core   | 5   | Full real-time sync |
| inner  | 15  | Full replication |
| middle | 50  | SEEDs + PARAGRAPHs only |
| outer  | 95  | On-demand only |

---

## Tech Stack

| Layer | Choice |
|-------|--------|
| API server | FastAPI |
| Storage | SQLite (aiosqlite) |
| Identity | PyNaCl (Ed25519) |
| HTTP client | httpx (async) |
| Frontend | HTMX + Jinja2 |
| Config | Pydantic / env vars |
| Tests | pytest + pytest-asyncio |
| Python | 3.11+ |

---

## Project Structure

```
osnova/
  osnova/               # Python package
    app.py              # FastAPI factory + CLI entry point
    config.py           # NodeConfig loader (file or env vars)
    schemas.py          # Pydantic models (ContentEntry, Peer, RingLevel, ...)
    crypto/             # Ed25519 identity, signing, verification
    storage/            # SQLite append-only content log
    rings/              # Trust ring management (Dunbar caps)
    gossip/             # Pull-based peer sync
    integrity/          # PARDES metadata + riddle encoding
    eject/              # Node eject + canary signal protocol
    api/
      routes.py         # All FastAPI endpoints
  static/               # CSS, HTMX JS
  templates/            # Jinja2 HTML templates
  tests/                # pytest (unit + integration)
  scripts/
    launch_cluster.sh   # 3-node local test cluster
  docs/                 # Design notes
  pyproject.toml
  CLAUDE.md             # Architecture decisions and rules
  BACKLOG.md            # Agent roster and phase tracker
```

---

## API Endpoints

### Identity

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/identity` | This node's public key and display name |

### Content

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/posts` | Create a signed post |
| GET | `/api/posts` | Feed (query: `limit`, `offset`, `author_key`) |
| GET | `/api/posts/{hash}` | Single post by content hash |
| POST | `/api/posts/{hash}/comment` | Add a comment to a post |
| GET | `/api/posts/{hash}/comments` | All comments on a post |
| POST | `/api/posts/{hash}/reshare` | Reshare a post |

### Rings

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/rings` | Peer count per ring level |
| GET | `/api/rings/{level}` | All peers in a ring (`core`/`inner`/`middle`/`outer`) |
| POST | `/api/rings/peers` | Add a peer to a ring |
| DELETE | `/api/rings/peers/{public_key}` | Remove a peer |
| PUT | `/api/rings/peers/{public_key}/promote` | Move peer to a new ring level |

### Sync

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/sync` | Handle incoming sync request from another node |
| POST | `/api/sync/pull` | Manually trigger a gossip round |

### Signals

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/signals/canary` | Broadcast compromised alert to all ring peers |
| POST | `/api/signals/eject` | Package content and eject from network |
| POST | `/api/signals/receive` | Receive a canary or eject signal from a peer |

Full interactive docs at `/docs` (Swagger UI) when the node is running.

---

## Running Tests

```bash
source venv/bin/activate
pytest tests/ -v
```

Run a specific module:

```bash
pytest tests/test_crypto.py -v     # 19 tests - identity + signing
pytest tests/test_storage.py -v    # 15 tests - content log
pytest tests/test_rings.py -v      # 21 tests - trust rings
pytest tests/test_gossip.py -v     # 16 tests - peer sync
pytest tests/test_api.py -v        # API endpoints
pytest tests/test_eject.py -v      # eject + canary protocols
pytest tests/test_riddle.py -v     # riddle encoder integration
```

### Node Configuration

All settings via env vars or a JSON config file (`NodeConfig` schema):

| Env var | Default | Description |
|---------|---------|-------------|
| `OSNOVA_NAME` | `anonymous` | Display name shown to peers |
| `OSNOVA_HOST` | `127.0.0.1` | Listen address |
| `OSNOVA_PORT` | `8000` | Listen port |
| `OSNOVA_DATA_DIR` | `./data` | SQLite + keypair storage |
| `OSNOVA_GOSSIP_INTERVAL` | `30` | Seconds between gossip rounds |
| `OSNOVA_CONFIG` | - | Path to JSON config file (overrides all above) |

JSON config example:

```json
{
  "display_name": "alice",
  "host": "127.0.0.1",
  "port": 8000,
  "data_dir": "/tmp/osnova-alice",
  "gossip_interval_seconds": 10
}
```

Pass it with `--config path/to/config.json` or set `OSNOVA_CONFIG`.
