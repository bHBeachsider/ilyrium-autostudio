// Prisma client for the canonical studio asset graph (prisma/studio.prisma).
//
// Mirrors lib/db.ts (the campaign client) but imports the SEPARATE studio client
// and uses a distinct global singleton, so both clients coexist in one app. Same
// Neon driver-adapter pattern (Prisma 7: new PrismaNeon({ connectionString })).
//
// NOTE: ../prisma/generated/studio-client does not exist until you generate it:
//   npx prisma generate --schema prisma/studio.prisma

import { PrismaClient } from '../prisma/generated/studio-client'
import { neonConfig } from '@neondatabase/serverless'
import { PrismaNeon } from '@prisma/adapter-neon'
import ws from 'ws'

// Required for the Node.js environment to talk to Neon via WebSockets.
neonConfig.webSocketConstructor = ws

const studioClientSingleton = () => {
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not set - restart `npm run dev` after editing .env")
  }
  const adapter = new PrismaNeon({ connectionString: process.env.DATABASE_URL })
  return new PrismaClient({ adapter })
}

declare global {
  // Distinct from the campaign client's prismaGlobal so the two don't collide.
  var studioPrismaGlobal: undefined | ReturnType<typeof studioClientSingleton>
}

type StudioClient = ReturnType<typeof studioClientSingleton>

// Module-scope cache covers production; the global covers dev hot-reload.
let cached: StudioClient | undefined

function getStudioDb(): StudioClient {
  const client = cached ?? globalThis.studioPrismaGlobal ?? studioClientSingleton()
  cached = client
  if (process.env.NODE_ENV !== 'production') globalThis.studioPrismaGlobal = client
  return client
}

// Lazy: the client is built on first property access, not at import. `next build`
// imports every route module to collect page data, and must not need DATABASE_URL
// to do so. A missing DATABASE_URL still throws - on first use, with the same message.
const studioDb = new Proxy({} as StudioClient, {
  get(_target, prop) {
    const client = getStudioDb()
    const value = Reflect.get(client, prop, client)
    return typeof value === 'function' ? value.bind(client) : value
  },
})

export default studioDb
