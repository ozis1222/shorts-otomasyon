/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: {
    serverComponentsExternalPackages: ['playwright-core', 'sharp', 'archiver'],
  },
  webpack(config) {
    // The engine (src/) uses explicit .js ESM import specifiers that point at
    // .ts files — teach webpack to resolve them.
    config.resolve.extensionAlias = {
      '.js': ['.ts', '.tsx', '.js'],
      '.mjs': ['.mts', '.mjs'],
    };
    return config;
  },
};
export default nextConfig;
