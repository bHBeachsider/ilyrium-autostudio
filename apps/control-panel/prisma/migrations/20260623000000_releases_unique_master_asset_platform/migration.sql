-- Relay distribution v1 (slice 2) — DISTRIBUTION_DESIGN.md §4.
-- Enforce "one release per (asset, platform)".
--
-- PARTIAL index because public.releases.master_asset_id is NULLABLE, but the distribution
-- spine only ever writes a NON-NULL master_asset_id (distribute() runs on a release-approved
-- asset that has a real master — the decide() precondition). So this index constrains exactly
-- the rows the spine produces; with a plain UNIQUE, null rows would be unconstrained (Postgres
-- treats NULLs as distinct), which would be a silent duplicate-row gap.
CREATE UNIQUE INDEX IF NOT EXISTS releases_master_asset_platform_uniq
  ON public.releases (master_asset_id, platform)
  WHERE master_asset_id IS NOT NULL;
