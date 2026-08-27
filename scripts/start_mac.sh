#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker not installed. Install Docker Desktop or Docker Engine, then re-run."
  exit 1
fi

if [ ! -f .env ]; then
  cp ".env.example" ".env"
  echo "Created .env from .env.example"
fi

if [ ! -f db/.gitkeep ]; then
  mkdir -p db
fi

docker compose up --build -d

sleep 1
if command -v xdg-open >/dev/null 2>&1; then
  xdg-open http://localhost:8003 || true
elif command -v open >/dev/null 2>&1; then
  open http://localhost:8003 || true
fi
