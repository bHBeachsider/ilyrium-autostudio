-- CreateSchema
CREATE SCHEMA IF NOT EXISTS "public";

-- CreateTable
CREATE TABLE "adapter_calls" (
    "id" BIGSERIAL NOT NULL,
    "agent_run_id" UUID,
    "capability" TEXT NOT NULL,
    "vendor" TEXT NOT NULL,
    "cost_cents" INTEGER,
    "latency_ms" INTEGER,
    "status" TEXT,
    "attempt" INTEGER DEFAULT 1,
    "fallback_chain" TEXT[],
    "occurred_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "adapter_calls_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "agent_runs" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "agent_name" TEXT NOT NULL,
    "plane" TEXT NOT NULL,
    "input_ref" TEXT,
    "output_ref" TEXT,
    "model_used" TEXT,
    "tokens_in" INTEGER,
    "tokens_out" INTEGER,
    "latency_ms" INTEGER,
    "cost_cents" INTEGER,
    "human_gate_status" TEXT,
    "started_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "completed_at" TIMESTAMPTZ(6),

    CONSTRAINT "agent_runs_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "assets" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "shot_id" UUID,
    "asset_type" TEXT,
    "model_id" TEXT,
    "prompt_id" UUID,
    "uri" TEXT NOT NULL,
    "version" INTEGER DEFAULT 1,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "assets_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "audit_log" (
    "id" BIGSERIAL NOT NULL,
    "actor" TEXT NOT NULL,
    "action" TEXT NOT NULL,
    "entity_type" TEXT NOT NULL,
    "entity_id" UUID,
    "before_json" JSONB,
    "after_json" JSONB,
    "occurred_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "audit_log_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "characters" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "name" TEXT NOT NULL,
    "bible_md" TEXT,
    "voice_ref_asset_id" UUID,
    "visual_refs" UUID[],
    "canon_rules_md" TEXT,
    "prohibited_uses_md" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "characters_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "concepts" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "logline" TEXT NOT NULL,
    "treatment_md" TEXT,
    "genre" TEXT[],
    "audience" TEXT[],
    "hook_emotional" TEXT,
    "hook_visual" TEXT,
    "ip_risk_score" INTEGER,
    "persona_score" JSONB,
    "greenlight_level" TEXT DEFAULT 'G0',
    "created_by" UUID,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "concepts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "cost_caps" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "scope_type" TEXT NOT NULL,
    "scope_id" TEXT NOT NULL,
    "period" TEXT NOT NULL,
    "cap_cents" INTEGER NOT NULL,
    "current_cents" INTEGER NOT NULL DEFAULT 0,
    "alert_threshold_pct" INTEGER DEFAULT 80,
    "created_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "cost_caps_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "event_log" (
    "id" BIGSERIAL NOT NULL,
    "event_type" TEXT NOT NULL,
    "event_version" INTEGER NOT NULL DEFAULT 1,
    "producer_plane" TEXT NOT NULL,
    "idempotency_key" TEXT,
    "payload" JSONB NOT NULL,
    "occurred_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "event_log_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "gate_approvals" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "agent_run_id" UUID,
    "gate_type" TEXT NOT NULL,
    "entity_type" TEXT NOT NULL,
    "entity_id" UUID NOT NULL,
    "required_role" TEXT NOT NULL,
    "required_cosigners" TEXT[],
    "state" TEXT NOT NULL DEFAULT 'pending',
    "sla_hours" INTEGER NOT NULL DEFAULT 24,
    "requested_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "resolved_at" TIMESTAMPTZ(6),
    "resolved_by" UUID,
    "resolution_note" TEXT,
    "trace_reviewed" BOOLEAN DEFAULT false,

    CONSTRAINT "gate_approvals_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "greenlight_scores" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "concept_id" UUID,
    "level" TEXT NOT NULL,
    "scored_by" UUID,
    "scored_at" TIMESTAMPTZ(6) DEFAULT CURRENT_TIMESTAMP,
    "creative_score" INTEGER,
    "audience_score" INTEGER,
    "risk_score" INTEGER,
    "business_score" INTEGER,
    "decision" TEXT NOT NULL,
    "notes" TEXT,

    CONSTRAINT "greenlight_scores_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "locations" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "name" TEXT NOT NULL,
    "description" TEXT,
    "visual_refs" UUID[],
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "locations_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "performance_metrics" (
    "id" BIGSERIAL NOT NULL,
    "release_id" UUID,
    "captured_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,
    "retention_curve_json" JSONB,
    "sentiment_score" REAL,
    "share_rate" REAL,
    "save_rate" REAL,
    "completion_rate" REAL,
    "cpm" REAL,

    CONSTRAINT "performance_metrics_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "projects" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "title" TEXT NOT NULL,
    "type" TEXT NOT NULL,
    "status" TEXT NOT NULL DEFAULT 'active',
    "owner_id" UUID,
    "budget_cents" INTEGER NOT NULL DEFAULT 0,
    "greenlight_level" TEXT DEFAULT 'G0',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "projects_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "prompts" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "text" TEXT NOT NULL,
    "negative_text" TEXT,
    "reference_assets" UUID[],
    "model_id" TEXT,
    "settings_json" JSONB,
    "success_score" REAL,
    "reuse_tag" TEXT,
    "text_embedding" vector,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "prompts_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "releases" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "master_asset_id" UUID,
    "platform" TEXT,
    "version_variant" TEXT,
    "hook_variant" TEXT,
    "scheduled_at" TIMESTAMPTZ(6),
    "published_at" TIMESTAMPTZ(6),
    "status" TEXT DEFAULT 'scheduled',
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "releases_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "rights_records" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "asset_id" UUID,
    "source_type" TEXT,
    "creator" TEXT,
    "model_used" TEXT,
    "license_type" TEXT,
    "commercial_use_allowed" BOOLEAN,
    "third_party_refs" TEXT[],
    "likeness_risk" TEXT DEFAULT 'none',
    "music_risk" TEXT DEFAULT 'none',
    "trademark_risk" TEXT DEFAULT 'none',
    "synthetic_performer_flag" BOOLEAN DEFAULT false,
    "digital_replica_flag" BOOLEAN DEFAULT false,
    "training_data_outbound_flag" BOOLEAN DEFAULT false,
    "sag_aftra_notice_filed_at" TIMESTAMPTZ(6),
    "risk_level" TEXT DEFAULT 'low',
    "release_required" BOOLEAN DEFAULT false,
    "release_status" TEXT DEFAULT 'pending',
    "legal_notes" TEXT,
    "approved_for_release" BOOLEAN DEFAULT false,
    "approved_by" UUID,
    "approved_at" TIMESTAMPTZ(6),

    CONSTRAINT "rights_records_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "scenes" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "scene_number" INTEGER,
    "description" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "scenes_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "shots" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "project_id" UUID,
    "scene_id" UUID,
    "shot_number" INTEGER NOT NULL,
    "description" TEXT NOT NULL,
    "camera" TEXT,
    "characters" UUID[],
    "location_id" UUID,
    "status" TEXT NOT NULL DEFAULT 'pending',
    "approved_take_id" UUID,
    "cost_cents" INTEGER DEFAULT 0,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "shots_pkey" PRIMARY KEY ("id")
);

-- CreateTable
CREATE TABLE "users" (
    "id" UUID NOT NULL DEFAULT gen_random_uuid(),
    "email" TEXT NOT NULL,
    "display_name" TEXT,
    "role" TEXT NOT NULL,
    "clerk_id" TEXT,
    "created_at" TIMESTAMPTZ(6) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "users_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "adapter_calls_capability_idx" ON "adapter_calls"("capability", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "adapter_calls_vendor_idx" ON "adapter_calls"("vendor", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "agent_runs_agent_idx" ON "agent_runs"("agent_name", "started_at" DESC);

-- CreateIndex
CREATE INDEX "agent_runs_status_idx" ON "agent_runs"("human_gate_status", "started_at" DESC);

-- CreateIndex
CREATE INDEX "assets_project_idx" ON "assets"("project_id");

-- CreateIndex
CREATE INDEX "assets_shot_idx" ON "assets"("shot_id");

-- CreateIndex
CREATE INDEX "audit_log_actor_idx" ON "audit_log"("actor", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "audit_log_entity_idx" ON "audit_log"("entity_type", "entity_id", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "characters_project_idx" ON "characters"("project_id");

-- CreateIndex
CREATE INDEX "concepts_greenlight_idx" ON "concepts"("greenlight_level");

-- CreateIndex
CREATE INDEX "concepts_project_idx" ON "concepts"("project_id");

-- CreateIndex
CREATE INDEX "cost_caps_scope_idx" ON "cost_caps"("scope_type", "scope_id");

-- CreateIndex
CREATE UNIQUE INDEX "event_log_idempotency_key_key" ON "event_log"("idempotency_key");

-- CreateIndex
CREATE INDEX "event_log_type_time_idx" ON "event_log"("event_type", "occurred_at" DESC);

-- CreateIndex
CREATE INDEX "gate_entity_idx" ON "gate_approvals"("entity_type", "entity_id");

-- CreateIndex
CREATE INDEX "gate_state_idx" ON "gate_approvals"("state", "requested_at");

-- CreateIndex
CREATE INDEX "greenlight_concept_idx" ON "greenlight_scores"("concept_id", "scored_at" DESC);

-- CreateIndex
CREATE INDEX "perf_release_idx" ON "performance_metrics"("release_id", "captured_at" DESC);

-- CreateIndex
CREATE INDEX "projects_greenlight_idx" ON "projects"("greenlight_level");

-- CreateIndex
CREATE INDEX "projects_status_idx" ON "projects"("status");

-- CreateIndex
CREATE INDEX "prompts_project_idx" ON "prompts"("project_id");

-- CreateIndex
CREATE INDEX "prompts_reuse_tag_idx" ON "prompts"("reuse_tag");

-- CreateIndex
CREATE INDEX "releases_platform_idx" ON "releases"("platform");

-- CreateIndex
CREATE INDEX "releases_project_idx" ON "releases"("project_id");

-- CreateIndex
CREATE INDEX "releases_published_idx" ON "releases"("published_at" DESC);

-- CreateIndex
CREATE INDEX "rights_records_asset_idx" ON "rights_records"("asset_id");

-- CreateIndex
CREATE INDEX "rights_records_release_idx" ON "rights_records"("approved_for_release");

-- CreateIndex
CREATE INDEX "shots_project_idx" ON "shots"("project_id");

-- CreateIndex
CREATE INDEX "shots_status_idx" ON "shots"("status");

-- CreateIndex
CREATE UNIQUE INDEX "users_email_key" ON "users"("email");

-- CreateIndex
CREATE UNIQUE INDEX "users_clerk_id_key" ON "users"("clerk_id");

-- AddForeignKey
ALTER TABLE "adapter_calls" ADD CONSTRAINT "adapter_calls_agent_run_id_fkey" FOREIGN KEY ("agent_run_id") REFERENCES "agent_runs"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "assets" ADD CONSTRAINT "assets_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "assets" ADD CONSTRAINT "assets_prompt_id_fkey" FOREIGN KEY ("prompt_id") REFERENCES "prompts"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "assets" ADD CONSTRAINT "assets_shot_id_fkey" FOREIGN KEY ("shot_id") REFERENCES "shots"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "characters" ADD CONSTRAINT "characters_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "concepts" ADD CONSTRAINT "concepts_created_by_fkey" FOREIGN KEY ("created_by") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "concepts" ADD CONSTRAINT "concepts_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "gate_approvals" ADD CONSTRAINT "gate_approvals_agent_run_id_fkey" FOREIGN KEY ("agent_run_id") REFERENCES "agent_runs"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "gate_approvals" ADD CONSTRAINT "gate_approvals_resolved_by_fkey" FOREIGN KEY ("resolved_by") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "greenlight_scores" ADD CONSTRAINT "greenlight_scores_concept_id_fkey" FOREIGN KEY ("concept_id") REFERENCES "concepts"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "greenlight_scores" ADD CONSTRAINT "greenlight_scores_scored_by_fkey" FOREIGN KEY ("scored_by") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "locations" ADD CONSTRAINT "locations_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "performance_metrics" ADD CONSTRAINT "performance_metrics_release_id_fkey" FOREIGN KEY ("release_id") REFERENCES "releases"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "projects" ADD CONSTRAINT "projects_owner_id_fkey" FOREIGN KEY ("owner_id") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "prompts" ADD CONSTRAINT "prompts_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "releases" ADD CONSTRAINT "releases_master_asset_id_fkey" FOREIGN KEY ("master_asset_id") REFERENCES "assets"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "releases" ADD CONSTRAINT "releases_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "rights_records" ADD CONSTRAINT "rights_records_approved_by_fkey" FOREIGN KEY ("approved_by") REFERENCES "users"("id") ON DELETE NO ACTION ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "rights_records" ADD CONSTRAINT "rights_records_asset_id_fkey" FOREIGN KEY ("asset_id") REFERENCES "assets"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "scenes" ADD CONSTRAINT "scenes_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "shots" ADD CONSTRAINT "shots_location_id_fkey" FOREIGN KEY ("location_id") REFERENCES "locations"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "shots" ADD CONSTRAINT "shots_project_id_fkey" FOREIGN KEY ("project_id") REFERENCES "projects"("id") ON DELETE CASCADE ON UPDATE NO ACTION;

-- AddForeignKey
ALTER TABLE "shots" ADD CONSTRAINT "shots_scene_id_fkey" FOREIGN KEY ("scene_id") REFERENCES "scenes"("id") ON DELETE SET NULL ON UPDATE NO ACTION;

