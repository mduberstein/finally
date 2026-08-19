#!/usr/bin/env bash
# Stops the finally container without removing it. Data under db/ is
# never touched by this script -- stop and start are the idempotent
# pair that keeps container identity (and its logs) stable across cycles.
set -euo pipefail

CONTAINER_NAME="finally"

RUNNING=$(docker inspect -f '{{.State.Running}}' "$CONTAINER_NAME" 2>/dev/null || echo "false")

if [ "$RUNNING" = "true" ]; then
  docker stop "$CONTAINER_NAME" >/dev/null
  echo "Stopped $CONTAINER_NAME. Data under db/ is preserved."
else
  echo "$CONTAINER_NAME is not running."
fi
