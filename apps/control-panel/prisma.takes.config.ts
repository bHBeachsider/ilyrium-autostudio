// Prisma config for the SQLite-backed Take / AudioElement / Cut schema.
// Used with: npx prisma migrate dev --config prisma.takes.config.ts --name <migration>
// NEVER used against the production Neon DATABASE_URL.
import "dotenv/config";
import { defineConfig } from "@prisma/config";

export default defineConfig({
  schema: "prisma/takes.prisma",
  migrations: {
    path: "prisma/takes-migrations",
  },
  datasource: {
    url: process.env["TAKES_DATABASE_URL"] ?? "file:./takes-dev.db",
  },
});
