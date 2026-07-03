#!/usr/bin/env node
// Local runner for the continuous idea loop. In production prefer a platform
// scheduler (e.g. Vercel cron hitting GET /api/loop/tick). Usage:
//   STUDIO_URL=http://localhost:3000 LOOP_INTERVAL_SECONDS=900 node scripts/loop.mjs
// The tick endpoint itself enforces the kill switch (STUDIO_LOOP_ENABLED) and
// LOOP_SECRET auth — this script is just a clock.

const base = process.env.STUDIO_URL ?? "http://localhost:3000"
const intervalSeconds = Math.max(60, Number(process.env.LOOP_INTERVAL_SECONDS) || 900)
const secret = process.env.LOOP_SECRET

async function tick() {
  try {
    const res = await fetch(`${base}/api/loop/tick`, {
      method: "POST",
      headers: secret ? { Authorization: `Bearer ${secret}` } : {},
    })
    const body = await res.json().catch(() => ({}))
    console.log(new Date().toISOString(), res.status, JSON.stringify(body).slice(0, 400))
  } catch (err) {
    console.error(new Date().toISOString(), "tick failed:", err.message ?? err)
  }
}

console.log(`[loop] ticking ${base}/api/loop/tick every ${intervalSeconds}s (Ctrl+C to stop)`)
await tick()
setInterval(tick, intervalSeconds * 1000)
