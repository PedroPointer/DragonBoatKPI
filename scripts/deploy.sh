#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== Pull latest ==="
git pull

echo "=== Stop stack ==="
docker compose down --remove-orphans

echo "=== Rebuild images (no cache) ==="
docker compose build --no-cache

echo "=== Start stack ==="
docker compose up -d

echo "=== Status ==="
docker compose ps

echo "=== Done ==="
