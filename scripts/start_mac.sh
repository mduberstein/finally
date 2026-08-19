#!/usr/bin/env bash
# Idempotent one-command launcher for macOS/Linux. Builds the finally image
# if it is missing (or if --build is passed), seeds .env from the template
# on a clean checkout, starts (or reuses) one container named "finally",
# polls /api/health instead of sleeping a fixed amount, then opens the
# browser once the app is confirmed ready.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

CONTAINER_NAME="finally"
IMAGE_NAME="finally"

BUILD_REQUESTED=false
if [[ "${1:-}" == "--build" ]]; then
  BUILD_REQUESTED=true
fi

if [ "$BUILD_REQUESTED" = true ] || ! docker image inspect "$IMAGE_NAME" >/dev/null 2>&1; then
  echo "Building the $IMAGE_NAME image..."
  docker build -t "$IMAGE_NAME" "$REPO_ROOT"
fi

if [ ! -f "$REPO_ROOT/.env" ]; then
  cp "$REPO_ROOT/.env.example" "$REPO_ROOT/.env"
  echo "Created .env from .env.example. Add your OpenRouter API key before AI chat will work."
fi

if ! STATE=$(docker inspect -f '{{.State.Status}}' "$CONTAINER_NAME" 2>/dev/null); then
  # A nonexistent container makes some Docker CLI versions emit a stray blank
  # line to stdout before the template-parse error, so any partial output is
  # discarded here rather than folded into STATE.
  STATE="absent"
fi

case "$STATE" in
  running)
    echo "$CONTAINER_NAME is already running at http://localhost:8000"
    ;;
  exited|created)
    docker start "$CONTAINER_NAME" >/dev/null
    echo "Started the existing $CONTAINER_NAME container."
    ;;
  absent)
    docker run -d --name "$CONTAINER_NAME" \
      -p 127.0.0.1:8000:8000 \
      -v "$REPO_ROOT/db:/app/db" \
      --env-file "$REPO_ROOT/.env" \
      "$IMAGE_NAME" >/dev/null
    echo "Created and started the $CONTAINER_NAME container."
    ;;
esac

for i in $(seq 1 30); do
  if curl -sf http://localhost:8000/api/health >/dev/null 2>&1; then
    echo "finally is ready at http://localhost:8000"
    open http://localhost:8000
    exit 0
  fi
  sleep 1
done

echo "finally did not become healthy in time. Check container logs with: docker logs $CONTAINER_NAME" >&2
exit 1
