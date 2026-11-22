import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Emits .next/standalone with a self-contained server.js, so the container
  // image doesn't need node_modules. See the Dockerfile for the static/public
  // copy step this requires.
  output: "standalone",
};

export default nextConfig;
