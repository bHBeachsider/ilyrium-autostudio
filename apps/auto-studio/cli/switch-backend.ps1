# switch-backend.ps1 — flip Claude Code's backend for this project.
#
#   .\switch-backend.ps1 anthropic   # real Anthropic API (default, always works)
#   .\switch-backend.ps1 ollama      # local Ollama on the EC2 tunnel (:11435)
#   .\switch-backend.ps1             # show current backend
#
# Only the `env` + `model` keys in .claude/settings.local.json are touched.
# permissions / MCP / plugins are preserved. Restart Claude Code after switching.

param([ValidateSet('anthropic','ollama','status','')] [string]$Target = '')

$ErrorActionPreference = 'Stop'
$root     = $PSScriptRoot
$local    = Join-Path $root '.claude\settings.local.json'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path $local)) { Write-Error "Not found: $local"; exit 1 }
$cfg = Get-Content $local -Raw | ConvertFrom-Json

function Show-Current {
    $base = $cfg.env.ANTHROPIC_BASE_URL
    if ($base -like '*127.0.0.1:11435*') { $name = 'ollama (local EC2 tunnel)' }
    elseif ($base -like '*api.anthropic.com*') { $name = 'anthropic (cloud API)' }
    else { $name = 'unknown' }
    Write-Host "Current backend: $name" -ForegroundColor Cyan
    Write-Host "  BASE_URL = $base"
    Write-Host "  model    = $($cfg.model)"
}

if ($Target -eq '' -or $Target -eq 'status') { Show-Current; exit 0 }

if ($Target -eq 'anthropic') {
    $cfg.env.ANTHROPIC_BASE_URL       = 'https://api.anthropic.com'
    $cfg.env.ANTHROPIC_AUTH_TOKEN     = ''
    $cfg.env.ANTHROPIC_MODEL          = 'claude-sonnet-4-6'
    $cfg.env.ANTHROPIC_SMALL_FAST_MODEL = 'claude-haiku-4-5'
    $cfg.model                        = 'claude-sonnet-4-6'
}
elseif ($Target -eq 'ollama') {
    # Warn if the tunnel isn't up yet.
    try {
        Invoke-RestMethod -Uri 'http://127.0.0.1:11435/api/tags' -TimeoutSec 3 | Out-Null
        Write-Host "Ollama tunnel is up on :11435." -ForegroundColor Green
    } catch {
        Write-Host "WARNING: nothing is listening on :11435." -ForegroundColor Yellow
        Write-Host "Run the 'studio-up' / 'qwen-ec2' skill to start the EC2 box + SSH tunnel first." -ForegroundColor Yellow
    }
    $cfg.env.ANTHROPIC_BASE_URL       = 'http://127.0.0.1:11435'
    $cfg.env.ANTHROPIC_AUTH_TOKEN     = 'ollama'
    $cfg.env.ANTHROPIC_MODEL          = 'qwen3-coder:latest'
    $cfg.env.ANTHROPIC_SMALL_FAST_MODEL = 'qwen3-coder:latest'
    $cfg.model                        = 'qwen3-coder:latest'
}

$json = $cfg | ConvertTo-Json -Depth 20
[System.IO.File]::WriteAllText($local, $json, $utf8NoBom)
Write-Host "Switched to: $Target" -ForegroundColor Green
Show-Current
Write-Host "`nRestart Claude Code for the change to take effect." -ForegroundColor Yellow
