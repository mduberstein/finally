import type { NextConfig } from "next";

/**
 * Static export served by FastAPI from the same origin as /api/*.
 * No rewrites, no image optimizer, no server runtime.
 */
const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  // Always defined so the fixture branch in src/lib/fixtures/install.ts is a
  // static false in a normal build.
  env: { NEXT_PUBLIC_MOCK: process.env.NEXT_PUBLIC_MOCK ?? "0" },
};

export default nextConfig;
