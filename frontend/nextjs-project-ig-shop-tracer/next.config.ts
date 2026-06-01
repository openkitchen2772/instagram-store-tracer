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
      }
    ],
  },
  async rewrites() {
    return {
      beforeFiles: [
        {
          source: '/backend-static/:path*',
          destination: `${process.env.BACKEND_BASE_URL}/:path*`,
        },
      ],
      afterFiles: [],
      fallback: [],
    };
    // return [
    //   {
    //     source: '/backend-static/:path*',
    //     destination: `${process.env.BACKEND_BASE_URL}/:path*`, 
    //   },
    // ];
  },
};

export default nextConfig;
