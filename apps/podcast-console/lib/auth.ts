// Single-operator password auth. The session cookie is an HMAC derived from
// STUDIO_PASSWORD via Web Crypto (edge-safe, works in proxy.ts), so there is no
// session store — changing the password invalidates every session.

export const AUTH_COOKIE = "studio_auth"

export async function sessionToken(password: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(password),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  )
  const sig = await crypto.subtle.sign("HMAC", key, new TextEncoder().encode("podcast-studio-session-v1"))
  return Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("")
}

/** Constant-time-ish comparison (lengths are fixed hex digests). */
export function tokensEqual(a: string, b: string): boolean {
  if (a.length !== b.length) return false
  let diff = 0
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i)
  return diff === 0
}
