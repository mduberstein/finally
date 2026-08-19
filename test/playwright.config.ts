import { execFileSync } from "node:child_process";

import { defineConfig } from "@playwright/test";

// Spec files are numerically prefixed (01-fresh-start.spec.ts, ...) and run
// in filename order under a single worker (fullyParallel: false, workers: 1)
// so the fresh-start scenario always runs first against the pristine seeded
// database, before any later scenario mutates cash or positions.

// BASE_URL is set to the compose service DNS name (http://app:8000) by
// test/docker-compose.test.yml. Falls back to localhost for a manual
// host-side run against a locally started container.
const rawBaseURL = process.env.BASE_URL ?? "http://localhost:8000";

/**
 * Chromium's HTTPS-Upgrades navigation throttle intercepts the very first
 * top-level navigation to any hostname that is neither "localhost" nor an
 * IP literal, and silently redirects it to https:// on the same port
 * before the request ever reaches the network. This app only ever speaks
 * plain HTTP, so that redirect hard-fails with net::ERR_SSL_PROTOCOL_ERROR.
 * `--disable-features=HttpsUpgrades` does NOT stop this in the Chromium
 * build shipped with mcr.microsoft.com/playwright:v1.62.1-noble (verified
 * empirically — the flag is present in Playwright's own default launch
 * args and the throttle still fires), so the workaround instead resolves
 * the compose service DNS name to its container IP once here. Chromium
 * exempts IP-literal navigation targets from the throttle. This changes
 * nothing about which network path is used — the resolved address IS the
 * app container's compose-network address — it only avoids the unrelated
 * browser-side throttle triggered by an unresolved hostname. Skipped for
 * "localhost" (already exempt) and for values that are already IP
 * literals (a manual host-side run, or a future non-Chromium project).
 * Resolution runs synchronously via `getent` (present in the official
 * Playwright image) because Playwright loads this config as CommonJS,
 * where top-level `await` is unavailable; a resolution failure — e.g.
 * `getent` absent on a non-Linux host — falls back to the unresolved URL
 * rather than crashing config load.
 */
function resolveNavigableBaseURL(url: string): string {
  const parsed = new URL(url);
  const isIPLiteral = /^\d{1,3}(\.\d{1,3}){3}$/.test(parsed.hostname);
  if (parsed.hostname === "localhost" || isIPLiteral) {
    return url;
  }
  try {
    const output = execFileSync("getent", ["hosts", parsed.hostname], { encoding: "utf8" });
    const address = output.trim().split(/\s+/)[0];
    parsed.hostname = address;
    return parsed.toString();
  } catch {
    return url;
  }
}

const baseURL = resolveNavigableBaseURL(rawBaseURL);

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  reporter: "list",
  timeout: 60_000,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL,
    trace: "retain-on-failure",
    video: "off",
  },
});
