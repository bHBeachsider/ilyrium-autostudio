import { NextResponse, type NextRequest } from "next/server"
import { AUTH_COOKIE, sessionToken, tokensEqual } from "@/lib/auth"

// Login gate for the whole studio (Next 16 proxy, née middleware). Everything —
// pages AND api routes — requires the STUDIO_PASSWORD session cookie, except:
//   /login + /api/login          the login flow itself
//   /api/telegram/webhook        authed by X-Telegram-Bot-Api-Secret-Token
//   /api/loop/tick               authed by its LOOP_SECRET bearer token
// With STUDIO_PASSWORD unset: open in development, locked (503 + notice) in
// production so a mis-deployed instance fails closed, not open.

const PUBLIC_PATHS = ["/login", "/api/login", "/api/telegram/webhook", "/api/loop/tick"]

export default async function proxy(req: NextRequest) {
  const { pathname } = req.nextUrl
  if (PUBLIC_PATHS.some((p) => pathname === p)) return NextResponse.next()

  const password = process.env.STUDIO_PASSWORD
  if (!password) {
    if (process.env.NODE_ENV !== "production") return NextResponse.next()
    return new NextResponse("Studio is locked: STUDIO_PASSWORD is not configured on this deployment.", {
      status: 503,
    })
  }

  const cookie = req.cookies.get(AUTH_COOKIE)?.value
  if (cookie && tokensEqual(cookie, await sessionToken(password))) return NextResponse.next()

  if (pathname.startsWith("/api/")) {
    return NextResponse.json({ error: "Unauthorized — log in at /login." }, { status: 401 })
  }
  const login = req.nextUrl.clone()
  login.pathname = "/login"
  login.searchParams.set("from", pathname)
  return NextResponse.redirect(login)
}

export const config = {
  // Skip Next internals and static assets; everything else goes through the gate.
  matcher: ["/((?!_next/static|_next/image|favicon.ico|icon.svg|.*\\.(?:png|jpg|svg|mp4)$).*)"],
}
