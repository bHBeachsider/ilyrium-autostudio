import { neon } from "@neondatabase/serverless"

// Neon HTTP driver, bound to DATABASE_URL. Suitable for Next route handlers (serverless,
// one round-trip per query). Set DATABASE_URL in .env.local to a Neon connection string
// (the pooled URL is fine). When unset, persistence is disabled and routes return 503 so
// the UI can fall back to session-only state instead of crashing.
const url = process.env.DATABASE_URL
const client = url ? neon(url) : null

export function dbReady(): boolean {
  return !!client
}

/** Returns the SQL tag, or throws a typed error the routes translate to 503. */
export function requireSql() {
  if (!client) throw new DbNotConfiguredError()
  return client
}

export class DbNotConfiguredError extends Error {
  constructor() {
    super("DATABASE_URL is not set. Add a Neon connection string to apps/podcast-console/.env.local.")
    this.name = "DbNotConfiguredError"
  }
}

export type Segment = { speaker: string; text: string }

/** Where an episode came from. `generated` = the console's own pipeline. */
export type EpisodeSource = "generated" | "imported_local" | "imported_api" | "imported_rss"

export type ProjectRow = { id: string; name: string; created_at: string }
export type EpisodeRow = {
  id: string
  project_id: string | null
  project_name: string | null
  title: string
  description: string | null
  estimated_minutes: number | null
  segments: Segment[]
  status: string
  audio_url: string | null
  video_url: string | null
  created_at: string
  source: EpisodeSource
  guid: string | null
  week_of: string | null
  jurisdiction: string | null
  episode_number: number | null
  season: number | null
  duration_seconds: number | null
  show_notes: string | null
  idea_id: string | null
}

export type IdeaStatus =
  | "proposed"
  | "approved"
  | "rejected"
  | "needs_changes"
  | "producing"
  | "produced"
  | "published"

export type IdeaRow = {
  id: string
  project_id: string | null
  title: string
  summary: string | null
  stage: string
  sources: number
  created_at: string
  angle: string | null
  rationale: string | null
  source_refs: string[]
  status: IdeaStatus
  score: number | null
  created_by: string | null
  reviewer: string | null
  review_note: string | null
  decided_at: string | null
  episode_id: string | null
}

export type ScriptStatus = "draft" | "approved" | "rejected" | "needs_changes"

export type ScriptRow = {
  id: string
  idea_id: string
  segments: Segment[]
  title: string | null
  description: string | null
  estimated_minutes: number | null
  status: ScriptStatus
  version: number
  reviewer: string | null
  review_note: string | null
  created_at: string
  decided_at: string | null
}

export type JobStep = "script" | "audio" | "images" | "video" | "finalize" | "done"
export type JobStatus = "queued" | "running" | "failed" | "done"

export type JobArtifacts = {
  script?: { title: string; description: string; estimatedMinutes: number; segments: Segment[] }
  audioKey?: string
  audioUrl?: string
  imageKeys?: string[]
  weights?: number[]
  imagesSkipped?: string
  videoKey?: string
  videoUrl?: string
}

export type JobRow = {
  id: string
  idea_id: string
  episode_id: string | null
  step: JobStep
  status: JobStatus
  artifacts: JobArtifacts
  error: string | null
  created_at: string
  updated_at: string
}

export type DistributionChannel = "transistor" | "sitebox" | "youtube" | "clips"
export type DistributionStatus = "pending" | "draft" | "published" | "assets_ready" | "manual" | "failed"

export type DistributionRow = {
  id: string
  episode_id: string
  channel: DistributionChannel
  external_id: string | null
  url: string | null
  status: DistributionStatus
  detail: Record<string, unknown>
  error: string | null
  published_at: string | null
  created_at: string
}

export type ContentSourceRow = {
  id: string
  kind: "local" | "permithub_api" | "rss" | "manual"
  name: string
  config: Record<string, unknown>
  enabled: boolean
  last_synced_at: string | null
  created_at: string
}

// Lazy, idempotent migration. Runs once per server process on the first DB call so there's
// no separate migrate step. Neon is PG15+, so gen_random_uuid() is built in.
let schemaReady = false
export async function ensureSchema(): Promise<void> {
  if (!client || schemaReady) return
  await client`CREATE TABLE IF NOT EXISTS podcast_projects (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name text NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
  )`
  await client`CREATE TABLE IF NOT EXISTS podcast_episodes (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid,
    project_name text,
    title text NOT NULL,
    description text,
    estimated_minutes integer,
    segments jsonb NOT NULL DEFAULT '[]'::jsonb,
    status text NOT NULL DEFAULT 'rendered',
    audio_url text,
    video_url text,
    created_at timestamptz NOT NULL DEFAULT now()
  )`
  await client`CREATE TABLE IF NOT EXISTS podcast_ideas (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id uuid NOT NULL REFERENCES podcast_projects(id) ON DELETE CASCADE,
    title text NOT NULL,
    summary text,
    stage text NOT NULL DEFAULT 'draft',
    sources integer NOT NULL DEFAULT 0,
    created_at timestamptz NOT NULL DEFAULT now()
  )`
  // Studio extensions: imported episodes carry producer metadata and durable media URLs.
  // guid is the idempotency key for re-imports (partial index: legacy rows keep guid NULL).
  await client`ALTER TABLE podcast_episodes
    ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'generated',
    ADD COLUMN IF NOT EXISTS guid text,
    ADD COLUMN IF NOT EXISTS week_of date,
    ADD COLUMN IF NOT EXISTS jurisdiction text,
    ADD COLUMN IF NOT EXISTS episode_number integer,
    ADD COLUMN IF NOT EXISTS season integer,
    ADD COLUMN IF NOT EXISTS duration_seconds integer,
    ADD COLUMN IF NOT EXISTS show_notes text,
    ADD COLUMN IF NOT EXISTS idea_id uuid`
  await client`CREATE UNIQUE INDEX IF NOT EXISTS podcast_episodes_guid_key
    ON podcast_episodes (guid) WHERE guid IS NOT NULL`
  await client`CREATE TABLE IF NOT EXISTS podcast_content_sources (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind text NOT NULL,
    name text NOT NULL,
    config jsonb NOT NULL DEFAULT '{}'::jsonb,
    enabled boolean NOT NULL DEFAULT true,
    last_synced_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now()
  )`
  // Ideas become the studio's HITL approval queue. The legacy stage/sources columns
  // stay for back-compat; project_id becomes optional (agent ideas have no project).
  await client`ALTER TABLE podcast_ideas ALTER COLUMN project_id DROP NOT NULL`
  await client`ALTER TABLE podcast_ideas
    ADD COLUMN IF NOT EXISTS angle text,
    ADD COLUMN IF NOT EXISTS rationale text,
    ADD COLUMN IF NOT EXISTS source_refs jsonb NOT NULL DEFAULT '[]'::jsonb,
    ADD COLUMN IF NOT EXISTS status text NOT NULL DEFAULT 'proposed',
    ADD COLUMN IF NOT EXISTS score numeric,
    ADD COLUMN IF NOT EXISTS created_by text,
    ADD COLUMN IF NOT EXISTS reviewer text,
    ADD COLUMN IF NOT EXISTS review_note text,
    ADD COLUMN IF NOT EXISTS decided_at timestamptz,
    ADD COLUMN IF NOT EXISTS episode_id uuid`
  await client`CREATE TABLE IF NOT EXISTS podcast_scripts (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id uuid NOT NULL REFERENCES podcast_ideas(id) ON DELETE CASCADE,
    segments jsonb NOT NULL DEFAULT '[]'::jsonb,
    title text,
    description text,
    estimated_minutes integer,
    status text NOT NULL DEFAULT 'draft',
    version integer NOT NULL DEFAULT 1,
    reviewer text,
    review_note text,
    created_at timestamptz NOT NULL DEFAULT now(),
    decided_at timestamptz
  )`
  // Production jobs: a step-advance state machine so each HTTP request runs one
  // bounded step (script -> audio -> images -> video -> finalize) instead of one
  // request exceeding serverless time limits.
  await client`CREATE TABLE IF NOT EXISTS podcast_jobs (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    idea_id uuid NOT NULL REFERENCES podcast_ideas(id),
    episode_id uuid,
    step text NOT NULL DEFAULT 'script',
    status text NOT NULL DEFAULT 'queued',
    artifacts jsonb NOT NULL DEFAULT '{}'::jsonb,
    error text,
    created_at timestamptz NOT NULL DEFAULT now(),
    updated_at timestamptz NOT NULL DEFAULT now()
  )`
  // Distribution results: one row per (episode, channel); re-publishing updates
  // the row rather than duplicating it.
  await client`CREATE TABLE IF NOT EXISTS podcast_distributions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    episode_id uuid NOT NULL REFERENCES podcast_episodes(id) ON DELETE CASCADE,
    channel text NOT NULL,
    external_id text,
    url text,
    status text NOT NULL DEFAULT 'pending',
    detail jsonb NOT NULL DEFAULT '{}'::jsonb,
    error text,
    published_at timestamptz,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (episode_id, channel)
  )`
  await client`CREATE TABLE IF NOT EXISTS podcast_content_items (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    source_id uuid REFERENCES podcast_content_sources(id) ON DELETE CASCADE,
    external_id text NOT NULL,
    title text NOT NULL,
    summary text,
    url text,
    payload jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_id, external_id)
  )`
  schemaReady = true
}
