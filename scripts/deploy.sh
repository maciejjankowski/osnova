#!/bin/bash
# Deploy Osnova (PHP) to va.evil1.org
# MyDevil.net: standard PHP hosting, files in public_html

set -e

REMOTE_USER="evil1"
REMOTE_HOST="s3.mydevil.net"
REMOTE_DIR="~/domains/va.evil1.org/public_html"
SSH_OPTS="-o ConnectTimeout=30 -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"
PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)/php"

echo "=== OSNOVA DEPLOY to va.evil1.org ==="
echo "Source: $PROJECT_DIR"
echo "Remote: $REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR"

# 1. Syntax check
echo ""
echo "[1/3] Checking PHP syntax..."
for f in "$PROJECT_DIR"/*.php "$PROJECT_DIR"/lib/*.php "$PROJECT_DIR"/api/*.php; do
    php -l "$f" > /dev/null || { echo "Syntax error in $f"; exit 1; }
done
echo "All files OK"

# 2. Upload
echo ""
echo "[2/3] Uploading..."
rsync -avz --delete \
  --exclude=data \
  --exclude=.DS_Store \
  -e "ssh $SSH_OPTS" \
  "$PROJECT_DIR/" "$REMOTE_USER@$REMOTE_HOST:$REMOTE_DIR/"

# 3. Verify
echo ""
echo "[3/3] Verifying..."
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "https://va.evil1.org/api/identity" 2>/dev/null)
if [ "$RESPONSE" = "200" ]; then
    echo ""
    echo "DEPLOYED SUCCESSFULLY"
    echo "  https://va.evil1.org"
    echo ""
    curl -s "https://va.evil1.org/api/identity" | python3 -m json.tool 2>/dev/null || true
else
    echo "WARNING: HTTP $RESPONSE"
fi
