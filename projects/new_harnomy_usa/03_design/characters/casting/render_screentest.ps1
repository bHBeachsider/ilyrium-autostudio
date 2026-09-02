$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $here "_screentest.log"
$dest = Join-Path $here "valencia_screentest"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
$H01 = Join-Path $here "valencia_v3\VAL-H01.png"

# BEAT 5 of the finale (v11 sec.X). One step downstage, into her own light. She opens
# the mauve book she has been holding, looks at it, closes it, lets it fall. Then one
# line to the house: "What won't you do?"
# This is a SHOT, not a casting still - the kernel grade applies here.
$p = "This exact woman, same face, in her late twenties. Alone on a dark empty stage in a single narrow pool of warm low light, everything behind her in total blackness, the theatre unseen beyond. She has just let a mauve hardback book fall from her open hand - it is on the floor near her feet, still settling. Her head is lifted and turned slightly out toward the house, her mouth open mid-phrase, singing one quiet line to people she cannot see. Not shouting, not weeping - a question offered. Her eyes are wet but nothing has fallen. Plain worn practical clothes. Wide medium shot from the house, slightly low, the darkness taking up most of the frame. Prestige political drama, single-source warm key, deep browns and charcoals, faint cool blue only in the deepest blacks, anamorphic, slight 35mm grain, photographic realism, cinematic, no on-screen text, no caption, no watermark"

"[{0}] beat 5 screen test" -f (Get-Date -Format o) | Out-File $log -Encoding ascii
$raw = higgsfield generate create nano_banana_pro --prompt $p --image-references $H01 --aspect-ratio "21:9" --resolution 2k --wait --wait-timeout 8m --json 2>&1 | Out-String
$raw | Out-File (Join-Path $here "_screentest_raw.json") -Encoding ascii
try {
  $job = ($raw | ConvertFrom-Json)[0]
  "{0} {1}" -f $job.id, $job.status | Out-File $log -Append -Encoding ascii
  if ($job.result_url) { Invoke-WebRequest -Uri $job.result_url -OutFile (Join-Path $dest "VAL-BEAT5.png") -UseBasicParsing -TimeoutSec 180 }
  "saved" | Out-File $log -Append -Encoding ascii
} catch { "ERROR {0}" -f $_.Exception.Message | Out-File $log -Append -Encoding ascii }
