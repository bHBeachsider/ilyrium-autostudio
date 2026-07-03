import type { EpisodeRow } from "@/lib/db"
import { envFlag, type Publisher, type PublishResult } from "./types"

// Transistor.fm publisher — mirrors PermitHub's proven TransistorPublisher flow:
// authorize upload -> PUT mp3 -> find-by-title (idempotent) -> create/update
// episode -> optionally publish. SAFETY: episodes are created as DRAFTS unless
// TRANSISTOR_PUBLISH=true, so test runs never air on the live RSS feed.

const BASE = "https://api.transistor.fm/v1"

function headers(): Record<string, string> {
  return { "x-api-key": process.env.TRANSISTOR_API_KEY ?? "", "Content-Type": "application/json" }
}

async function api(path: string, init?: RequestInit): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}${path}`, { ...init, headers: { ...headers(), ...init?.headers } })
  if (!res.ok) {
    const detail = await res.text().catch(() => "")
    throw new Error(`Transistor ${init?.method ?? "GET"} ${path} failed (${res.status}): ${detail.slice(0, 200)}`)
  }
  return (await res.json()) as Record<string, unknown>
}

type TransistorResource = { id: string; attributes: Record<string, unknown> }

async function resolveShow(): Promise<TransistorResource> {
  const configured = process.env.TRANSISTOR_SHOW_ID
  const body = await api("/shows")
  const shows = (body.data ?? []) as TransistorResource[]
  if (shows.length === 0) throw new Error("Transistor account has no shows.")
  if (configured) {
    const match = shows.find((s) => s.id === configured)
    if (!match) throw new Error(`TRANSISTOR_SHOW_ID ${configured} not found in account.`)
    return match
  }
  return shows[0]
}

async function uploadAudio(audioUrl: string): Promise<string> {
  const source = await fetch(audioUrl)
  if (!source.ok) throw new Error(`Could not fetch episode audio (${source.status}) from ${audioUrl}`)
  const audio = Buffer.from(await source.arrayBuffer())

  const auth = await api(`/episodes/authorize_upload?filename=episode.mp3`)
  const attrs = (auth.data as TransistorResource).attributes as { upload_url: string; audio_url: string }
  const put = await fetch(attrs.upload_url, {
    method: "PUT",
    headers: { "Content-Type": "audio/mpeg" },
    body: new Uint8Array(audio),
  })
  if (!put.ok) throw new Error(`Transistor audio upload failed (${put.status}).`)
  return attrs.audio_url
}

export const transistorPublisher: Publisher = {
  id: "transistor",
  enabled() {
    return envFlag("PUBLISH_TRANSISTOR_ENABLED") && !!process.env.TRANSISTOR_API_KEY
  },
  disabledReason() {
    if (!envFlag("PUBLISH_TRANSISTOR_ENABLED")) return "PUBLISH_TRANSISTOR_ENABLED is not 'true'."
    return "TRANSISTOR_API_KEY is not set."
  },
  async publish(episode: EpisodeRow): Promise<PublishResult> {
    if (!episode.audio_url) throw new Error("Episode has no audio_url to upload.")
    const show = await resolveShow()
    const audioUrl = await uploadAudio(episode.audio_url)

    // Idempotent by title: update the existing Transistor episode if one matches.
    const listing = await api(`/episodes?show_id=${show.id}`)
    const existing = ((listing.data ?? []) as TransistorResource[]).find(
      (e) => (e.attributes.title as string) === episode.title,
    )

    const fields = {
      title: episode.title,
      summary: episode.description ?? "",
      description: episode.show_notes ?? episode.description ?? "",
      audio_url: audioUrl,
      ...(episode.season ? { season: episode.season } : {}),
      ...(episode.episode_number ? { number: episode.episode_number } : {}),
    }
    // Transistor rejects show_id on updates (episode already belongs to a show).
    const saved = existing
      ? await api(`/episodes/${existing.id}`, { method: "PATCH", body: JSON.stringify({ episode: fields }) })
      : await api(`/episodes`, { method: "POST", body: JSON.stringify({ episode: { show_id: show.id, ...fields } }) })
    const resource = saved.data as TransistorResource

    const feedUrl = (show.attributes.feed_url as string | undefined) ?? null
    const shouldPublish = envFlag("TRANSISTOR_PUBLISH")
    if (shouldPublish) {
      await api(`/episodes/${resource.id}/publish`, {
        method: "PATCH",
        body: JSON.stringify({ episode: { status: "published" } }),
      })
    }

    return {
      status: shouldPublish ? "published" : "draft",
      externalId: resource.id,
      url: (resource.attributes.share_url as string | undefined) ?? null,
      detail: {
        showId: show.id,
        feedUrl,
        note: shouldPublish
          ? "Published to the live feed."
          : "Created as DRAFT (set TRANSISTOR_PUBLISH=true to publish to the live feed).",
      },
    }
  },
}
