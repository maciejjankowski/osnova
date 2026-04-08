#!/usr/bin/env bash
# launch_cluster.sh - Start a local Osnova test cluster
#
# Usage:
#   bash scripts/launch_cluster.sh [N]
#
# Defaults to 3 nodes: alice (8000), bob (8001), carol (8002).
# Registers all nodes as inner-ring peers of each other, then tails logs.
# Ctrl+C kills all nodes.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV="$REPO_ROOT/venv/bin/activate"
N="${1:-3}"

# ---------------------------------------------------------------------------
# Node definitions (extend this array to add more nodes)
# ---------------------------------------------------------------------------
NODE_NAMES=("alice" "bob" "carol" "dave" "eve")
NODE_PORTS=(8000 8001 8002 8003 8004)

if [ "$N" -gt "${#NODE_NAMES[@]}" ]; then
  echo "Max supported nodes: ${#NODE_NAMES[@]}" >&2
  exit 1
fi

# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------
PIDS=()
LOG_FILES=()

cleanup() {
  echo ""
  echo "[cluster] Shutting down all nodes..."
  for pid in "${PIDS[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  # Wait briefly for clean shutdown
  sleep 1
  for pid in "${PIDS[@]}"; do
    kill -9 "$pid" 2>/dev/null || true
  done
  echo "[cluster] Done."
  exit 0
}

trap cleanup SIGINT SIGTERM

# ---------------------------------------------------------------------------
# Activate venv
# ---------------------------------------------------------------------------
if [ ! -f "$VENV" ]; then
  echo "[cluster] ERROR: venv not found at $VENV" >&2
  echo "          Run: python3 -m venv venv && source venv/bin/activate && pip install -e '.[dev]'" >&2
  exit 1
fi

source "$VENV"

# ---------------------------------------------------------------------------
# Build config files and start nodes
# ---------------------------------------------------------------------------
echo "[cluster] Starting $N nodes..."

for i in $(seq 0 $((N - 1))); do
  NAME="${NODE_NAMES[$i]}"
  PORT="${NODE_PORTS[$i]}"
  DATA_DIR="/tmp/osnova-$NAME"
  CONFIG_FILE="/tmp/osnova-$NAME.json"
  LOG_FILE="/tmp/osnova-$NAME.log"

  mkdir -p "$DATA_DIR"

  # Write JSON config
  cat > "$CONFIG_FILE" <<JSON
{
  "display_name": "$NAME",
  "host": "127.0.0.1",
  "port": $PORT,
  "data_dir": "$DATA_DIR",
  "gossip_interval_seconds": 10
}
JSON

  echo "[cluster]   $NAME -> http://127.0.0.1:$PORT  (data: $DATA_DIR, log: $LOG_FILE)"

  OSNOVA_CONFIG="$CONFIG_FILE" \
  OSNOVA_NAME="$NAME" \
  OSNOVA_PORT="$PORT" \
  OSNOVA_DATA_DIR="$DATA_DIR" \
  OSNOVA_HOST="127.0.0.1" \
    python -m uvicorn osnova.app:create_app \
      --factory \
      --host 127.0.0.1 \
      --port "$PORT" \
      --log-level info \
      >> "$LOG_FILE" 2>&1 &

  PIDS+=($!)
  LOG_FILES+=("$LOG_FILE")
done

# ---------------------------------------------------------------------------
# Wait for all nodes to be healthy
# ---------------------------------------------------------------------------
echo "[cluster] Waiting for nodes to be healthy..."

for i in $(seq 0 $((N - 1))); do
  NAME="${NODE_NAMES[$i]}"
  PORT="${NODE_PORTS[$i]}"
  URL="http://127.0.0.1:$PORT/api/identity"
  ATTEMPTS=0
  MAX_ATTEMPTS=30

  while true; do
    if curl -sf "$URL" > /dev/null 2>&1; then
      echo "[cluster]   $NAME is up at http://127.0.0.1:$PORT"
      break
    fi
    ATTEMPTS=$((ATTEMPTS + 1))
    if [ "$ATTEMPTS" -ge "$MAX_ATTEMPTS" ]; then
      echo "[cluster] ERROR: $NAME did not start within ${MAX_ATTEMPTS}s" >&2
      echo "          Check log: ${LOG_FILES[$i]}" >&2
      cleanup
    fi
    sleep 1
  done
done

# ---------------------------------------------------------------------------
# Collect public keys from each node
# ---------------------------------------------------------------------------
echo "[cluster] Collecting node identities..."

declare -A NODE_PUBKEYS

for i in $(seq 0 $((N - 1))); do
  NAME="${NODE_NAMES[$i]}"
  PORT="${NODE_PORTS[$i]}"
  PUBKEY=$(curl -sf "http://127.0.0.1:$PORT/api/identity" | python3 -c "import sys,json; print(json.load(sys.stdin)['public_key'])")
  NODE_PUBKEYS["$NAME"]="$PUBKEY"
  echo "[cluster]   $NAME pubkey: ${PUBKEY:0:16}..."
done

# ---------------------------------------------------------------------------
# Auto-register peers: each node adds all others to inner ring
# ---------------------------------------------------------------------------
echo "[cluster] Registering peers..."

for i in $(seq 0 $((N - 1))); do
  SRC_NAME="${NODE_NAMES[$i]}"
  SRC_PORT="${NODE_PORTS[$i]}"

  for j in $(seq 0 $((N - 1))); do
    if [ "$i" -eq "$j" ]; then
      continue
    fi

    PEER_NAME="${NODE_NAMES[$j]}"
    PEER_PORT="${NODE_PORTS[$j]}"
    PEER_KEY="${NODE_PUBKEYS[$PEER_NAME]}"

    RESULT=$(curl -sf -X POST "http://127.0.0.1:$SRC_PORT/api/rings/peers" \
      -H "Content-Type: application/json" \
      -d "{
        \"public_key\": \"$PEER_KEY\",
        \"display_name\": \"$PEER_NAME\",
        \"ring_level\": \"inner\",
        \"endpoint\": \"http://127.0.0.1:$PEER_PORT\"
      }" 2>&1 || echo "FAILED")

    if echo "$RESULT" | grep -q "FAILED"; then
      echo "[cluster]   WARNING: $SRC_NAME failed to add $PEER_NAME"
    else
      echo "[cluster]   $SRC_NAME added $PEER_NAME to inner ring"
    fi
  done
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
echo ""
echo "[cluster] =========================================="
echo "[cluster]  Cluster running ($N nodes)"
echo "[cluster] =========================================="
for i in $(seq 0 $((N - 1))); do
  NAME="${NODE_NAMES[$i]}"
  PORT="${NODE_PORTS[$i]}"
  echo "[cluster]   $NAME  ->  http://127.0.0.1:$PORT"
  echo "              docs:     http://127.0.0.1:$PORT/docs"
  echo "              identity: http://127.0.0.1:$PORT/api/identity"
  echo "              feed:     http://127.0.0.1:$PORT/api/posts"
  echo "              rings:    http://127.0.0.1:$PORT/api/rings"
done
echo ""
echo "[cluster]  Logs:"
for f in "${LOG_FILES[@]}"; do
  echo "              $f"
done
echo ""
echo "[cluster]  Press Ctrl+C to stop all nodes."
echo "[cluster] =========================================="

# ---------------------------------------------------------------------------
# Tail all logs until Ctrl+C
# ---------------------------------------------------------------------------
tail -f "${LOG_FILES[@]}" &
TAIL_PID=$!

# Wait for any background node to exit unexpectedly
while true; do
  for i in "${!PIDS[@]}"; do
    pid="${PIDS[$i]}"
    if ! kill -0 "$pid" 2>/dev/null; then
      NAME="${NODE_NAMES[$i]}"
      echo "[cluster] WARNING: $NAME (pid $pid) exited unexpectedly. Check ${LOG_FILES[$i]}"
    fi
  done
  sleep 5
done
