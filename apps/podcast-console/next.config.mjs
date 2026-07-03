/** @type {import('next').NextConfig} */
const nextConfig = {
  // Allow loading dev HMR/client resources when the app is opened via 127.0.0.1
  // (not just localhost). Without this, Next 16 blocks /_next dev resources and
  // the client never hydrates — the page renders but every button is dead.
  allowedDevOrigins: ["127.0.0.1"],
  serverExternalPackages: ["ffmpeg-static"],
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
}

export default nextConfig
