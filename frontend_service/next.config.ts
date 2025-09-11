import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',

  // Environment variables that should be available to the client
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000',
    NEXT_PUBLIC_WEBSOCKET_URL: process.env.NEXT_PUBLIC_WEBSOCKET_URL || 'ws://localhost:8003',
  },

  // Disable TypeScript strict checking for build
  typescript: {
    ignoreBuildErrors: true,
  },

  // Disable ESLint during build
  eslint: {
    ignoreDuringBuilds: true,
  },

  // Enable experimental features for better development experience
  experimental: {
    // Enable faster refresh in development
    optimizePackageImports: ['react', 'react-dom'],
  },

  // Configure headers for API communication
  async headers() {
    return [
      {
        source: '/api/:path*',
        headers: [
          { key: 'Access-Control-Allow-Origin', value: '*' },
          { key: 'Access-Control-Allow-Methods', value: 'GET,POST,PUT,DELETE,OPTIONS' },
          { key: 'Access-Control-Allow-Headers', value: 'Content-Type, Authorization' },
        ],
      },
    ];
  },
};

export default nextConfig;
