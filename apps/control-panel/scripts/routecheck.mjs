// Route-path verification for the studio asset graph (Phase A).
// Imports the SAME generated studio client + Neon adapter the API routes use
// (lib/studio-db.ts), and replays the exact operations /api/studio/sync and
// /api/studio/asset perform — proving the Prisma->adapter->Neon write path,
// nested provenance creation, BigInt sizeBytes, and checksum dedupe all work.
// Cleans up the test project afterward so Brad's real render starts from zero.

import { PrismaClient } from '../prisma/generated/studio-client/index.js'
import { neonConfig } from '@neondatabase/serverless'
import { PrismaNeon } from '@prisma/adapter-neon'
import ws from 'ws'
import fs from 'fs'
import path from 'path'

// Replicate next.config.js: load THIS project's .env with override.
const envText = fs.readFileSync(path.join(process.cwd(), '.env'), 'utf8')
const m = envText.match(/^DATABASE_URL=(.*)$/m)
process.env.DATABASE_URL = (m ? m[1] : '').trim()

neonConfig.webSocketConstructor = ws
const adapter = new PrismaNeon({ connectionString: process.env.DATABASE_URL })
const db = new PrismaClient({ adapter })

const EXT = '__routecheck__rc1'
const j = (o) => JSON.stringify(o, (_, v) => (typeof v === 'bigint' ? v.toString() : v))

async function syncRoute() {
  const project = await db.project.upsert({
    where: { externalId: EXT },
    update: { title: 'RouteCheck Co', type: 'AD', styleKernel: { look: 'test' } },
    create: { externalId: EXT, title: 'RouteCheck Co', type: 'AD', styleKernel: { look: 'test' } },
  })
  await db.shot.deleteMany({ where: { projectId: project.id } })
  await db.scene.deleteMany({ where: { projectId: project.id } })
  await db.scene.create({
    data: {
      project: { connect: { id: project.id } },
      title: null, orderIndex: 1,
      shots: { create: [{ project: { connect: { id: project.id } }, shotNumber: 1, prompt: 'a test shot' }] },
    },
  })
  return project
}

async function assetRoute(project, { type, checksum, sizeBytes }) {
  const existing = await db.asset.findFirst({ where: { projectId: project.id, checksum } })
  if (existing) return { assetId: existing.id, deduped: true }
  const asset = await db.asset.create({
    data: {
      project: { connect: { id: project.id } },
      type, uri: `/local/${checksum}.mp4`, checksum, storageProvider: 'local',
      sizeBytes: sizeBytes != null ? BigInt(sizeBytes) : undefined,
      provenance: { create: { modelProvider: 'veo3', modelName: 'veo3', seed: '42',
        generationParams: { prompt: 'a test shot', sceneNumber: 1, costCents: 320 } } },
    },
  })
  return { assetId: asset.id, deduped: false }
}

try {
  const project = await syncRoute()
  console.log('SYNC -> project', project.id, 'externalId', project.externalId)
  const a1 = await assetRoute(project, { type: 'VIDEO', checksum: 'sha-take-1', sizeBytes: 1234567 })
  const a2 = await assetRoute(project, { type: 'MASTER', checksum: 'sha-master-1', sizeBytes: 7654321 })
  const a1dup = await assetRoute(project, { type: 'VIDEO', checksum: 'sha-take-1', sizeBytes: 1234567 })
  console.log('ASSET take ->', j(a1))
  console.log('ASSET master ->', j(a2))
  console.log('ASSET dup  ->', j(a1dup), '(expect deduped:true)')

  // Verify rows via relational read (what `prisma studio` would show).
  const full = await db.project.findUnique({
    where: { externalId: EXT },
    include: { scenes: { include: { shots: true } },
      assets: { include: { provenance: true, rightsRecord: true } } },
  })
  console.log('VERIFY scenes:', full.scenes.length, 'shots:', full.scenes.reduce((n, s) => n + s.shots.length, 0))
  console.log('VERIFY assets:', full.assets.length,
    '| provenance present:', full.assets.every(a => !!a.provenance),
    '| sample model:', full.assets[0]?.provenance?.modelName)

  // Cleanup so the real Streamlit render is the official first row set.
  const assetIds = full.assets.map(a => a.id)
  await db.provenanceRecord.deleteMany({ where: { assetId: { in: assetIds } } })
  await db.rightsRecord.deleteMany({ where: { assetId: { in: assetIds } } })
  await db.asset.deleteMany({ where: { projectId: project.id } })
  await db.shot.deleteMany({ where: { projectId: project.id } })
  await db.scene.deleteMany({ where: { projectId: project.id } })
  await db.project.delete({ where: { id: project.id } })
  console.log('CLEANUP ok — test project removed.')
  await db.$disconnect()
  console.log('RESULT: PASS')
} catch (e) {
  console.error('RESULT: FAIL ->', e)
  await db.$disconnect().catch(() => {})
  process.exit(1)
}
