import { PrismaClient } from '../prisma/generated/client'
import { neonConfig } from '@neondatabase/serverless'
import { PrismaNeon } from '@prisma/adapter-neon'
import ws from 'ws'

// Required for the Node.js environment to talk to Neon via WebSockets
neonConfig.webSocketConstructor = ws

const prismaClientSingleton = () => {
  // Fail fast instead of silently falling back to localhost defaults.
  // If this throws, DATABASE_URL was not in the process env when db.ts first
  // loaded -> fully restart `npm run dev` after editing .env (hot reload won't
  // rebuild the cached pool on globalThis).
  if (!process.env.DATABASE_URL) {
    throw new Error("DATABASE_URL is not set - restart `npm run dev` after editing .env")
  }

  // Prisma 7's adapter-neon takes a PoolConfig ({ connectionString }), NOT a Pool
  // instance. It manages the Neon pool internally.
  const adapter = new PrismaNeon({ connectionString: process.env.DATABASE_URL })

  return new PrismaClient({ adapter })
}

declare global {
  var prismaGlobal: undefined | ReturnType<typeof prismaClientSingleton>
}

const prisma = globalThis.prismaGlobal ?? prismaClientSingleton()

export default prisma

if (process.env.NODE_ENV !== 'production') globalThis.prismaGlobal = prisma