#!/usr/bin/env bash
# Stop and remove the FinAlly container. The finally-data volume is kept.
set -euo pipefail

CONTAINER=finally

if [ -z "$(docker ps -aq -f "name=^${CONTAINER}$")" ]; then
  echo "Container $CONTAINER does not exist. Nothing to stop."
  exit 0
fi

docker rm -f "$CONTAINER" >/dev/null
echo "Stopped and removed container $CONTAINER. Volume finally-data kept."
