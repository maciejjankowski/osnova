"""Osnova FastAPI application factory and entry point."""
from __future__ import annotations

import argparse
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from osnova.api.routes import router
from osnova.api.pages import pages_router
from osnova.config import load_config
from osnova.crypto.identity import (
    generate_keypair,
    load_keypair,
    public_key_hex,
    save_keypair,
)
from osnova.gossip.sync import GossipService
from osnova.rings.manager import RingManager
from osnova.storage.log import ContentLog

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent


def _build_lifespan(config):
    """Return an asynccontextmanager lifespan for the given NodeConfig."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # ----------------------------------------------------------------
        # Startup
        # ----------------------------------------------------------------
        data_dir = Path(config.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)

        # --- Keypair ---
        key_path = data_dir / "identity.key"
        if key_path.exists():
            signing_key = load_keypair(key_path)
            logger.info("Loaded existing keypair from %s", key_path)
        else:
            signing_key, _ = generate_keypair()
            save_keypair(signing_key, key_path)
            logger.info("Generated new keypair at %s", key_path)

        node_public_key = public_key_hex(signing_key.verify_key)

        # --- Storage ---
        content_log = ContentLog(str(data_dir / "content.db"))
        await content_log.initialize()
        logger.info("ContentLog initialized at %s", data_dir / "content.db")

        # --- Rings ---
        ring_manager = RingManager(str(data_dir / "rings.db"))
        await ring_manager.initialize()
        logger.info("RingManager initialized at %s", data_dir / "rings.db")

        # --- Gossip ---
        gossip_service = GossipService(
            content_log=content_log,
            ring_manager=ring_manager,
            node_public_key=node_public_key,
        )
        await gossip_service.start_gossip_loop(
            interval_seconds=config.gossip_interval_seconds
        )
        logger.info(
            "GossipService started (interval=%ds)", config.gossip_interval_seconds
        )

        # --- Signal storage (in-memory list, survives for the session) ---
        app.state.received_signals = []

        # --- Discovery storage ---
        app.state.triads = []
        app.state.received_keys = []

        # --- Store in app.state for route access ---
        app.state.content_log = content_log
        app.state.ring_manager = ring_manager
        app.state.gossip_service = gossip_service
        app.state.signing_key = signing_key
        app.state.node_public_key = node_public_key
        app.state.display_name = config.display_name
        app.state.config = config

        # --- Jinja2 templates ---
        templates_dir = _BASE_DIR / "templates"
        if templates_dir.exists():
            app.state.templates = Jinja2Templates(directory=str(templates_dir))
        else:
            app.state.templates = None

        logger.info(
            "Osnova node started: %s (%s...)", config.display_name, node_public_key[:12]
        )

        yield  # --- application runs ---

        # ----------------------------------------------------------------
        # Shutdown
        # ----------------------------------------------------------------
        await gossip_service.stop_gossip_loop()
        await content_log.close()
        await ring_manager.close()
        logger.info("Osnova node shut down cleanly")

    return lifespan


def create_app(config_path: str | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    config_path: path to a JSON config file (NodeConfig schema).
    Falls back to OSNOVA_CONFIG env var, then built-in defaults.
    """
    if config_path is None:
        config_path = os.environ.get("OSNOVA_CONFIG")

    config = load_config(config_path)

    app = FastAPI(
        title="Osnova",
        description="Decentralized truth network with Dunbar-capped trust rings and PARDES integrity",
        version="0.1.0",
        lifespan=_build_lifespan(config),
    )

    app.include_router(router)
    app.include_router(pages_router)

    static_dir = _BASE_DIR / "static"
    if static_dir.exists():
        app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    return app


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Run an Osnova node")
    parser.add_argument(
        "--config",
        metavar="PATH",
        default=None,
        help="Path to JSON config file (NodeConfig schema). "
             "Also reads OSNOVA_CONFIG env var.",
    )
    parser.add_argument("--host", default=None, help="Override listen host")
    parser.add_argument("--port", type=int, default=None, help="Override listen port")
    args = parser.parse_args()

    config_path = args.config or os.environ.get("OSNOVA_CONFIG")
    config = load_config(config_path)

    host = args.host or config.host
    port = args.port or config.port

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    uvicorn.run(
        "osnova.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=False,
    )


if __name__ == "__main__":
    main()
