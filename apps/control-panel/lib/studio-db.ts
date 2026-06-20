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

const studioDb = globalThis.studioPrismaGlobal ?? studioClientSingleton()

export default studioDb

if (process.env.NODE_ENV !== 'production') globalThis.studioPrismaGlobal = studioDb
