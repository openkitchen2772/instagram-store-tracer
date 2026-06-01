import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactCompiler: true,
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "picsum.photos",
      },
      {
        protocol: "https",
        hostname: "**.fna.fbcdn.net",
      },
      {
        protocol: 'https',
        hostname: `${process.env.BACKEND_BASE_HOSTNAME}`,
      }
    ],
  },
  async rewrites() {
    return [
      {
        source: '/backend-static/:path*',
        destination: `${process.env.BACKEND_BASE_URL}/:path*`, 
      },
    ];
  },
};

export default nextConfig;
