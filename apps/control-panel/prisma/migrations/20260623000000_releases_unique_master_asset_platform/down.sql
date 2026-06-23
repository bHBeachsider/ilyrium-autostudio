-- Down-migration for 20260623000000_releases_unique_master_asset_platform.
-- Reverses the partial unique index added in migration.sql. Idempotent.
DROP INDEX IF EXISTS public.releases_master_asset_platform_uniq;
