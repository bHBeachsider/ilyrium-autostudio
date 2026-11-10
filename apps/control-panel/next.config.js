// Force this project's .env to win over any inherited DATABASE_URL (e.g. a
// stray User-scope env var pointing at another DB). `override: true` makes
// .env values overwrite anything already in process.env. Runs in the Node
// server process, so route handlers see the corrected value.
//
// Skipped under Playwright (ILYRIUM_CONSOLE_FIXTURE set): the test server must
// never be handed the real DATABASE_URL, and `override: true` would do exactly that.
if (!process.env.ILYRIUM_CONSOLE_FIXTURE) {
  require("dotenv").config({
    path: require("path").join(__dirname, ".env"),
    override: true,
  });
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Don't let webpack bundle these. Bundling `ws` breaks its conditional
  // require of the masking helper -> "bufferUtil.mask is not a function"
  // when @neondatabase/serverless sends a WebSocket frame. Loading them as
  // normal Node modules at runtime fixes it.
  // (Top-level key since Next 15; `experimental.serverComponentsExternalPackages`
  // is rejected as invalid by Next 16.)
  serverExternalPackages: [
    "ws",
    "@neondatabase/serverless",
    "@prisma/adapter-neon",
    "@prisma/client",
  ],
  // Config redirects run before the filesystem and before any render, so the console
  // layout's data load never runs for them. 307 (permanent: false) so no browser caches
  // the target while the console's page list is still changing.
  async redirects() {
    return [
      { source: "/", destination: "/studio/console/run", permanent: false },
      { source: "/studio/console", destination: "/studio/console/run", permanent: false },
    ];
  },
};

module.exports = nextConfig;
