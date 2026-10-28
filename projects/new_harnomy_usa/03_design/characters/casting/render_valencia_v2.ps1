$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $here "_render_v2.log"
$out  = Join-Path $here "RESULTS_valencia_v2.json"
$slate = Get-Content (Join-Path $here "CASTING_SLATE.json") -Raw | ConvertFrom-Json
$dest = Join-Path $here "valencia_v2"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
$results = @()
"[{0}] valencia v2 - ethnically ambiguous, hands out, neutral casting light" -f (Get-Date -Format o) | Out-File $log -Encoding ascii
foreach ($e in ($slate.entries | Where-Object { $_.character -eq "valencia" })) {
    "{0} creating..." -f $e.candidate_id | Out-File $log -Append -Encoding ascii
    try {
        $raw = higgsfield generate create soul_cinematic --prompt $e.prompt --aspect-ratio "3:2" --quality 2k --wait --wait-timeout 6m --json 2>&1 | Out-String
        $job = ($raw | ConvertFrom-Json)[0]
        $results += [pscustomobject]@{ candidate_id=$e.candidate_id; job_id=$job.id; seed=$job.params.seed; result_url=$job.result_url; status=$job.status }
        "{0} {1} seed={2}" -f $e.candidate_id, $job.status, $job.params.seed | Out-File $log -Append -Encoding ascii
        if ($job.result_url) {
            Invoke-WebRequest -Uri $job.result_url -OutFile (Join-Path $dest ("{0}.png" -f $e.candidate_id)) -UseBasicParsing -TimeoutSec 120
        }
    } catch {
        $results += [pscustomobject]@{ candidate_id=$e.candidate_id; status="ERROR"; error=$_.Exception.Message }
        "{0} ERROR {1}" -f $e.candidate_id, $_.Exception.Message | Out-File $log -Append -Encoding ascii
    }
    $results | ConvertTo-Json -Depth 5 | Set-Content $out -Encoding ascii
}
"[{0}] DONE {1}/6" -f (Get-Date -Format o), ($results | Where-Object { $_.status -eq "completed" }).Count | Out-File $log -Append -Encoding ascii
