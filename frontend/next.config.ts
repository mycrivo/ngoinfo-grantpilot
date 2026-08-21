import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "ngoinfo.org",
      },
    ],
  },
};

export default nextConfig;
