import { S3Client, PutObjectCommand, GetObjectCommand } from "@aws-sdk/client-s3"

// Durable media storage on Cloudflare R2, sharing the bucket + env contract of
// apps/auto-studio/utils/storage_manager.py (R2_ENDPOINT, R2_ACCESS_KEY_ID,
// R2_SECRET_ACCESS_KEY, R2_BUCKET, R2_PUBLIC_HOST). When unconfigured the studio
// degrades gracefully: importers fall back to remote source URLs where they exist.

const endpoint = process.env.R2_ENDPOINT
const accessKeyId = process.env.R2_ACCESS_KEY_ID
const secretAccessKey = process.env.R2_SECRET_ACCESS_KEY
const bucket = process.env.R2_BUCKET || "ilyrium-assets"

const client =
  endpoint && accessKeyId && secretAccessKey
    ? new S3Client({
        region: "auto",
        endpoint,
        credentials: { accessKeyId, secretAccessKey },
      })
    : null

export function blobReady(): boolean {
  return !!client
}

export class BlobNotConfiguredError extends Error {
  constructor() {
    super(
      "R2 storage is not configured. Set R2_ENDPOINT, R2_ACCESS_KEY_ID and R2_SECRET_ACCESS_KEY (plus optional R2_BUCKET, R2_PUBLIC_HOST) in apps/podcast-console/.env.local.",
    )
    this.name = "BlobNotConfiguredError"
  }
}

/** Browser-facing URL for a stored key. Without R2_PUBLIC_HOST the S3 endpoint
 * form is returned, which 403s on anonymous GETs — same caveat as auto-studio. */
export function publicUrl(key: string): string {
  const host = process.env.R2_PUBLIC_HOST
  if (host) {
    const base = host.startsWith("http") ? host : `https://${host}`
    return `${base.replace(/\/+$/, "")}/${key}`
  }
  console.warn("[blob] R2_PUBLIC_HOST unset; returning non-public endpoint URL for", key)
  return `${(endpoint ?? "").replace(/\/+$/, "")}/${bucket}/${key}`
}

/** Upload a buffer and return its public URL. */
export async function putObject(key: string, body: Buffer | Uint8Array, contentType: string): Promise<string> {
  if (!client) throw new BlobNotConfiguredError()
  await client.send(new PutObjectCommand({ Bucket: bucket, Key: key, Body: body, ContentType: contentType }))
  return publicUrl(key)
}

/** Download a stored object (used by production/distribution steps). */
export async function getObject(key: string): Promise<Buffer> {
  if (!client) throw new BlobNotConfiguredError()
  const res = await client.send(new GetObjectCommand({ Bucket: bucket, Key: key }))
  if (!res.Body) throw new Error(`R2 object ${key} has no body`)
  return Buffer.from(await res.Body.transformToByteArray())
}

/** Reverse of publicUrl(): the R2 key for a URL this module could have minted, else null. */
export function keyFromUrl(url: string): string | null {
  const prefixes: string[] = []
  const host = process.env.R2_PUBLIC_HOST
  if (host) {
    const base = host.startsWith("http") ? host : `https://${host}`
    prefixes.push(`${base.replace(/\/+$/, "")}/`)
  }
  if (endpoint) prefixes.push(`${endpoint.replace(/\/+$/, "")}/${bucket}/`)
  for (const prefix of prefixes) {
    if (url.startsWith(prefix)) return url.slice(prefix.length)
  }
  return null
}

/** Fetch media by URL, going through credentialed R2 reads for our own storage.
 * Without R2_PUBLIC_HOST, stored URLs are the S3-endpoint form that 403s on
 * anonymous GETs — so publishers must never plain-fetch their own media. */
export async function fetchMedia(url: string): Promise<Buffer> {
  const key = client ? keyFromUrl(url) : null
  if (key) return getObject(key)
  const res = await fetch(url)
  if (!res.ok) throw new Error(`Could not fetch media (${res.status}) from ${url}`)
  return Buffer.from(await res.arrayBuffer())
}
