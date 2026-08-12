#!/usr/bin/env bash
# Build (if needed) and run the FinAlly container. Safe to run repeatedly.
# Usage: ./scripts/start_mac.sh [--build]
set -euo pipefail

IMAGE=finally
CONTAINER=finally
VOLUME=finally-data
PORT=8000

cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "No .env found. Copy .env.example to .env and add your keys."
  exit 1
fi

BUILD=false
if [ "${1:-}" = "--build" ]; then
  BUILD=true
fi

if [ "$BUILD" = true ] || ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Building image $IMAGE"
  docker build -t "$IMAGE" .
fi

if [ "$BUILD" = false ] && [ -n "$(docker ps -q -f "name=^${CONTAINER}$")" ]; then
  echo "Container $CONTAINER is already running at http://localhost:$PORT"
  exit 0
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

docker run -d \
  --name "$CONTAINER" \
  -p "$PORT:8000" \
  -v "$VOLUME:/app/db" \
  --env-file .env \
  "$IMAGE" >/dev/null

echo "FinAlly is running at http://localhost:$PORT"
