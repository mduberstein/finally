import type { NextConfig } from "next";

// Static export: FastAPI serves the build output directly, so the whole app
// lives on one origin/port and no CORS configuration exists anywhere.
const nextConfig: NextConfig = {
  output: 'export',
  images: { unoptimized: true },
  trailingSlash: true,
};

export default nextConfig;
