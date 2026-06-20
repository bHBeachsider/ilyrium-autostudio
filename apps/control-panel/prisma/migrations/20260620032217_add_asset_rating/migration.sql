-- Phase 1: add content `rating` to assets (the ONLY column this reconciliation adds).
-- Consumed by Ilyrium Relay's decide() gate (distribution + paywall). The CHECK is
-- enforced in the DB and the TS decide() layer; Prisma does not model CHECK constraints
-- (so it is invisible to drift). NOT NULL + DEFAULT 'clean' is safe on the populated
-- table — existing rows backfill to 'clean'. Additive only; no data loss.
ALTER TABLE "public"."assets" ADD COLUMN "rating" TEXT NOT NULL DEFAULT 'clean' CHECK ("rating" IN ('clean', 'mature', 'uncensored'));
