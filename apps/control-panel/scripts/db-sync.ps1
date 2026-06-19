# Canonical schema-sync for the studio asset graph — run on the host (Windows),
# not the sandbox, so it never touches the laggy file mount.
#
#   cd apps\control-panel ; .\scripts\db-sync.ps1
#
# Sets DATABASE_URL from .env, generates the Prisma client, and pushes DDL using
# the NON-pooled Neon host (dropping "-pooler") to avoid P1017 on schema DDL.

$ErrorActionPreference = "Stop"
$envLine = Select-String -Path .env -Pattern '^DATABASE_URL=' | Select-Object -First 1
if (-not $envLine) { Write-Error "DATABASE_URL not found in .env"; exit 1 }
$pooled = ($envLine.Line -replace '^DATABASE_URL=', '')
$direct = $pooled -replace '-pooler\.', '.'   # non-pooled host for DDL

Write-Host "Generating Prisma client (studio)..." -ForegroundColor Cyan
$env:DATABASE_URL = $pooled
npx prisma generate --schema prisma/studio.prisma

Write-Host "Pushing schema to Neon (non-pooled host)..." -ForegroundColor Cyan
$env:DATABASE_URL = $direct
npx prisma db push --schema prisma/studio.prisma

Write-Host "Done. Schema + client in sync." -ForegroundColor Green
