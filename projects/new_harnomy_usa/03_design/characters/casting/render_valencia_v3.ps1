$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $here "_render_v3.log"
$out  = Join-Path $here "RESULTS_valencia_v3.json"
$dest = Join-Path $here "valencia_v3"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }
$C05 = Join-Path $here "valencia_v2\VAL-C05.png"
$C06 = Join-Path $here "valencia_v2\VAL-C06.png"

# What is being kept from C05 and what is being softened toward C06.
$KEEP = "a young woman in her late twenties of deliberately ambiguous ethnicity, features that do not resolve to any one part of the world, heavy dark brows and a strong nose framing steady dark eyes, real gravity in the face, dark hair worn practically, slight build, secondhand layering worn as a work uniform, a thrifted cardigan over a plain tee"
$SOFT = "the jaw unset and relaxed, the mouth soft and unpressed rather than held, faint shadows of tiredness under the eyes, the armour off - grave but not defended, an open face that could break"
$FRAME = "head-and-shoulders portrait framed just below the collarbone, hands out of frame, straight-on to camera, plain unlit grey backdrop, mouth closed with the lips together, eyes steady on the lens, expression neutral and still, blank unmarked clothing with no printed graphics"
$LOOK = "even neutral daylight-balanced exposure, soft frontal key, shadows open and detailed, natural skin tones, sharp focus on the eyes, photographic realism, documentary portrait, shot on a 85mm lens, no irony, no winking"

$jobs = @(
 @{id="VAL-H01"; model="nano_banana_pro"; refs=@($C05,$C06);
   prompt="Blend these two women into one person. Take the bone structure, heavy dark brows, strong nose and grave steady presence of the first. Take the tiredness, the softness around the mouth and the unguarded quality of the second. $KEEP, $SOFT, $FRAME, $LOOK"}
 @{id="VAL-H02"; model="soul_cinematic"; refs=@($C05);
   prompt="$KEEP, $SOFT, $FRAME, $LOOK"}
 @{id="VAL-H03"; model="soul_cinematic"; refs=@($C05);
   prompt="$KEEP, $SOFT, visibly tired at the end of a long shift, a face that has been awake too long, $FRAME, $LOOK"}
 @{id="VAL-H04"; model="soul_cinematic"; refs=@($C05);
   prompt="$KEEP, $SOFT, a fuller softer mouth and a gentler jawline while the brows and nose stay strong, $FRAME, $LOOK"}
 @{id="VAL-H05"; model="soul_cinematic"; refs=@();
   prompt="$KEEP, $SOFT, $FRAME, $LOOK"}
)

$results = @()
foreach ($j in $jobs) {
    "{0} ({1}) creating..." -f $j.id, $j.model | Out-File $log -Append -Encoding ascii
    try {
        $args = @("generate","create",$j.model,"--prompt",$j.prompt,"--aspect-ratio","3:2","--wait","--wait-timeout","8m","--json")
        if ($j.model -eq "nano_banana_pro") { $args += @("--resolution","2k") } else { $args += @("--quality","2k") }
        foreach ($r in $j.refs) { $args += @("--image-references",$r) }
        $raw = & higgsfield @args 2>&1 | Out-String
        $job = ($raw | ConvertFrom-Json)[0]
        $results += [pscustomobject]@{ id=$j.id; model=$j.model; job_id=$job.id; seed=$job.params.seed; result_url=$job.result_url; status=$job.status }
        "{0} {1}" -f $j.id, $job.status | Out-File $log -Append -Encoding ascii
        if ($job.result_url) { Invoke-WebRequest -Uri $job.result_url -OutFile (Join-Path $dest ("{0}.png" -f $j.id)) -UseBasicParsing -TimeoutSec 120 }
    } catch {
        $results += [pscustomobject]@{ id=$j.id; model=$j.model; status="ERROR"; error=$_.Exception.Message }
        "{0} ERROR {1}" -f $j.id, $_.Exception.Message | Out-File $log -Append -Encoding ascii
    }
    $results | ConvertTo-Json -Depth 5 | Set-Content $out -Encoding ascii
}
"DONE {0}/5" -f ($results | Where-Object { $_.status -eq "completed" }).Count | Out-File $log -Append -Encoding ascii
