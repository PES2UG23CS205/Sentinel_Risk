/** @type {import('next').NextConfig} */
const nextConfig = {
  /* Proxy API calls to the FastAPI backend */
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
