# OSNOVA - Decentralized Truth Network

## What Is This
P2P social network with Dunbar-capped trust rings, PARDES-structured content integrity (holographic + Einstein riddle encoding), multi-transport by design. Like Threads but decentralized and ephemeral.

## Tech Stack (MVP)
- **Python 3.11+** with venv
- **FastAPI** - API server (each node is a FastAPI instance)
- **SQLite** - local append-only log per node
- **PyNaCl** - Ed25519 identity + signing
- **HTMX** - frontend (no React/Vue/Next)
- **Jinja2** - templates
- **httpx** - async HTTP for gossip between nodes

## Architecture
- Each user runs a node (FastAPI server on a port)
- Identity = Ed25519 keypair (PyNaCl)
- Content = signed JSON entries in append-only SQLite log
- Trust rings = peer public keys with ring level (core/inner/middle/outer)
- Gossip = pull-based HTTP sync between peers
- No blockchain, no global state, no consensus

## Rules
- No React/Next/Vue - HTMX only
- No microservices - single process per node
- No blockchain/tokens - reputation-based
- No global state - each node has its own view
- Source: ~/code/zbigniew-protocol/_tools/ for riddle encoder
- Tests with pytest
- Type hints everywhere

## Project Structure
```
osnova/
  osnova/           # Python package
    crypto/         # Identity, signing, verification
    storage/        # SQLite append-only log
    rings/          # Trust ring management
    gossip/         # Peer discovery + sync
    integrity/      # PARDES metadata + riddle encoding
    api/            # FastAPI routes
    schemas.py      # Pydantic models
    config.py       # Node configuration
  static/           # CSS, JS (HTMX)
  templates/        # Jinja2 templates
  tests/            # pytest
  docs/             # Design decisions, architecture
```
