/** @type {import('next').NextConfig} */
const { version } = require('./package.json');

const nextConfig = {
  reactStrictMode: true,
  output: 'standalone',
  env: {
    APP_VERSION: version,
  },
};

module.exports = nextConfig;
