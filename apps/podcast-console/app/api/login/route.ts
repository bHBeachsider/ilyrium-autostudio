import { NextResponse } from "next/server"
import { AUTH_COOKIE, sessionToken } from "@/lib/auth"

export const runtime = "nodejs"

// POST /api/login { password } — sets the session cookie the proxy gate checks.
export async function POST(req: Request) {
  const password = process.env.STUDIO_PASSWORD
  if (!password) {
    return NextResponse.json({ error: "STUDIO_PASSWORD is not configured." }, { status: 503 })
  }
  const body = await req.json().catch(() => ({}))
  if (typeof body.password !== "string" || body.password !== password) {
    return NextResponse.json({ error: "Wrong password." }, { status: 401 })
  }
  const res = NextResponse.json({ ok: true })
  res.cookies.set(AUTH_COOKIE, await sessionToken(password), {
    httpOnly: true,
    secure: process.env.NODE_ENV === "production",
    sameSite: "lax",
    path: "/",
    maxAge: 60 * 60 * 24 * 30, // 30 days
  })
  return res
}
