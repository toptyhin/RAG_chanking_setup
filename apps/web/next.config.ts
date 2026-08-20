import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",
  // next@16.2.10 probes typescript/lib/typescript.js; TS 7 (native) has no JS API.
  // Keep DEPENDENCIES pin (typescript@7.0.2); skip Next's broken auto typecheck.
  // Typecheck locally with: npx tsc --noEmit
  typescript: {
    ignoreBuildErrors: true,
  },
};

export default nextConfig;
