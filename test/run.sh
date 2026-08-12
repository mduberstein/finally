#!/usr/bin/env bash
# Run the full E2E suite against a freshly built, freshly seeded container.
# Exits with the suite's exit code.
set -euo pipefail

cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.test.yml"

cleanup() {
  $COMPOSE down -v --remove-orphans >/dev/null 2>&1 || true
}

# A previous run's containers would keep a used database and a stale image.
cleanup
trap cleanup EXIT

$COMPOSE up --build --abort-on-container-exit --exit-code-from playwright
