// PrismaClient for the SQLite-backed takes / audio-element / cut layer.
//
// Uses the generated client from prisma/takes.prisma (via prisma.takes.config.ts).
// TAKES_DATABASE_URL must be set (default: file:./takes-dev.db).
//
// In Prisma 7 all database access goes through a driver adapter.
// For the SQLite dev DB we use @prisma/adapter-libsql.
//
// NOTE: prisma/generated/takes-client does not exist until you run:
//   npx prisma migrate dev --config prisma.takes.config.ts --name add-take-cut-audio

import { PrismaClient } from "../prisma/generated/takes-client";
import { PrismaLibSql } from "@prisma/adapter-libsql";

const takesClientSingleton = () => {
  const url = process.env.TAKES_DATABASE_URL ?? "file:./takes-dev.db";
  const adapter = new PrismaLibSql({ url });
  return new PrismaClient({ adapter } as any);
};

declare global {
  var takesPrismaGlobal: undefined | ReturnType<typeof takesClientSingleton>;
}

const takesDb: ReturnType<typeof takesClientSingleton> =
  globalThis.takesPrismaGlobal ?? takesClientSingleton();

export default takesDb;

if (process.env.NODE_ENV !== "production") globalThis.takesPrismaGlobal = takesDb;
