#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== HARD DEPLOY: full DB reset + fresh deploy ==="
echo ""

echo "=== Pull latest ==="
git pull

echo ""
echo "=== Stop stack and DELETE all data (volume) ==="
docker compose down -v --remove-orphans

echo ""
echo "=== Rebuild images (no cache) ==="
docker compose build --no-cache

echo ""
echo "=== Start stack ==="
docker compose up -d

echo ""
echo "=== Waiting for app to be ready ==="
sleep 10

echo ""
echo "=== Status ==="
docker compose ps

echo ""
echo "=== Done. Database is EMPTY. Re-upload CSVs from /informes. ==="
