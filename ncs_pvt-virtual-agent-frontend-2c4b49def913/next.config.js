const createNextPluginPreval = require("next-plugin-preval/config");
const withNextPluginPreval = createNextPluginPreval();

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: false,
  output: 'standalone', // Enable standalone output for Docker
  images: {
    domains: [
      'd-id.com',
      'api.d-id.com',
      'd-id-public-bucket.s3.us-west-2.amazonaws.com',
      'create-images-results.d-id.com'
    ],
  },
};

module.exports = withNextPluginPreval(nextConfig);
