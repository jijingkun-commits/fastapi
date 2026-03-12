/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    serverActions: {
      bodySizeLimit: "10mb",
    },
  },
  async rewrites() {
    // 后端 API 地址，默认为 localhost:8000
    const backendUrl = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

    return [
      // 代理 assets API 到后端（用于 RAGFlow 图片等）
      {
        source: '/api/v1/assets/:path*',
        destination: `${backendUrl}/api/v1/assets/:path*`,
      },
      // [Fallback] 万一有组件错误请求了 Next.js 的 /api/v1/，兜底转发到后端
      {
        source: '/api/v1/:path*',
        destination: `${backendUrl}/api/v1/:path*`,
      },
    ];
  },
  webpack(config) {
    config.resolve ??= {};
    config.resolve.alias = {
      ...(config.resolve.alias ?? {}),
      canvas: false,
    };
    return config;
  },
};

export default nextConfig;
