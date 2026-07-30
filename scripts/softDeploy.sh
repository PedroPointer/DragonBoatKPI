#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== SOFT DEPLOY: clear test data, keep users, then deploy ==="
echo ""

echo "=== Pull latest ==="
git pull

echo ""
echo "=== Stop stack ==="
docker compose down --remove-orphans

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
echo "=== Resetting test data (keeping users, categories, boats) ==="
docker compose exec web python scripts/reset_pruebas.py --yes

echo ""
echo "=== Done. Users preserved. Re-upload CSVs from /informes. ==="
