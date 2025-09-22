import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // Use Docker container name when running in container, localhost otherwise
    const backendUrl = process.env.NODE_ENV === 'production' || process.env.DOCKER_ENV 
      ? 'http://ocr-backend:8000' 
      : 'http://localhost:8000';
      
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
