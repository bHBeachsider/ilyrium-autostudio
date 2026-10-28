# render_slate.ps1 - render the Stage-3 casting slate on Higgsfield Soul Cinematic.
# ASCII only. Detached-safe: writes progress to _render.log and results to RESULTS.json.
$ErrorActionPreference = "Continue"
$here   = Split-Path -Parent $MyInvocation.MyCommand.Path
$log    = Join-Path $here "_render.log"
$outAll = Join-Path $here "RESULTS.json"
$slate  = Get-Content (Join-Path $here "CASTING_SLATE.json") -Raw | ConvertFrom-Json

$tail = ", no on-screen text, no caption, no watermark, no logo, not a photograph of any real or famous person"

# VAL-C01 was rendered during the job-shape test - reuse it, do not pay twice.
$results = @()
$results += [pscustomobject]@{
    candidate_id = "VAL-C01"; character = "valencia"
    job_id = "e9b20253-20e5-44ac-b9f0-ecd058624761"
    seed = 595394
    result_url = "https://d8j0ntlcm91z4.cloudfront.net/user_3HvujMmkK01IpqcOy9ZsiGh1csm/hf_20260902_133310_e9b20253-20e5-44ac-b9f0-ecd058624761.png"
    status = "completed"; credits = 0.12
}

"[{0}] starting - {1} entries in slate" -f (Get-Date -Format o), $slate.entries.Count | Out-File $log -Encoding ascii
$n = 0
foreach ($e in $slate.entries) {
    $n++
    if ($e.candidate_id -eq "VAL-C01") {
        "[{0}] {1} SKIP (already rendered in test)" -f $n, $e.candidate_id | Out-File $log -Append -Encoding ascii
        continue
    }
    $prompt = $e.prompt + $tail
    "[{0}/{1}] {2} creating..." -f $n, $slate.entries.Count, $e.candidate_id | Out-File $log -Append -Encoding ascii
    try {
        $raw = higgsfield generate create soul_cinematic --prompt $prompt --aspect-ratio "3:2" --quality 2k --wait --wait-timeout 6m --json 2>&1 | Out-String
        $job = ($raw | ConvertFrom-Json)[0]
        $results += [pscustomobject]@{
            candidate_id = $e.candidate_id; character = $e.character
            job_id = $job.id; seed = $job.params.seed
            result_url = $job.result_url; status = $job.status; credits = 0.12
        }
        "[{0}] {1} {2} seed={3}" -f $n, $e.candidate_id, $job.status, $job.params.seed | Out-File $log -Append -Encoding ascii
    } catch {
        $results += [pscustomobject]@{
            candidate_id = $e.candidate_id; character = $e.character
            job_id = $null; seed = $null; result_url = $null
            status = "ERROR"; credits = 0; error = $_.Exception.Message
        }
        "[{0}] {1} ERROR {2}" -f $n, $e.candidate_id, $_.Exception.Message | Out-File $log -Append -Encoding ascii
    }
    $results | ConvertTo-Json -Depth 5 | Set-Content $outAll -Encoding ascii
}

# Download every completed still into casting/<character>/
"[{0}] downloading..." -f (Get-Date -Format o) | Out-File $log -Append -Encoding ascii
foreach ($r in $results) {
    if ($r.status -ne "completed" -or -not $r.result_url) { continue }
    $cdir = Join-Path $here $r.character
    if (-not (Test-Path $cdir)) { New-Item -ItemType Directory -Path $cdir -Force | Out-Null }
    $dest = Join-Path $cdir ("{0}.png" -f $r.candidate_id)
    try {
        Invoke-WebRequest -Uri $r.result_url -OutFile $dest -UseBasicParsing -TimeoutSec 120
        "  saved {0} ({1} KB)" -f $r.candidate_id, [math]::Round((Get-Item $dest).Length/1KB) | Out-File $log -Append -Encoding ascii
    } catch {
        "  DOWNLOAD FAIL {0}: {1}" -f $r.candidate_id, $_.Exception.Message | Out-File $log -Append -Encoding ascii
    }
}
$results | ConvertTo-Json -Depth 5 | Set-Content $outAll -Encoding ascii
$ok = ($results | Where-Object { $_.status -eq "completed" }).Count
"[{0}] DONE - {1}/{2} completed, {3} credits spent" -f (Get-Date -Format o), $ok, $results.Count, ($results | Measure-Object credits -Sum).Sum | Out-File $log -Append -Encoding ascii
