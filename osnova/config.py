"""Node configuration loading."""
from __future__ import annotations

import json
import os
from pathlib import Path

from osnova.schemas import NodeConfig


def load_config(config_path: str | None = None) -> NodeConfig:
    """Load node config from file or environment."""
    if config_path and Path(config_path).exists():
        with open(config_path) as f:
            return NodeConfig(**json.load(f))

    return NodeConfig(
        display_name=os.environ.get("OSNOVA_NAME", "anonymous"),
        host=os.environ.get("OSNOVA_HOST", "127.0.0.1"),
        port=int(os.environ.get("OSNOVA_PORT", "8000")),
        data_dir=os.environ.get("OSNOVA_DATA_DIR", "./data"),
        gossip_interval_seconds=int(os.environ.get("OSNOVA_GOSSIP_INTERVAL", "30")),
    )
