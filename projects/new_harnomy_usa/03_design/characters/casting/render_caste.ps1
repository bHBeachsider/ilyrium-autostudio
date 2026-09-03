$ErrorActionPreference = "Continue"
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$log  = Join-Path $here "_render_caste.log"
$out  = Join-Path $here "RESULTS_caste.json"
$dest = Join-Path $here "caste"
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Path $dest -Force | Out-Null }

# THE CASTE BLOCK - shared by Summer, Pengold and Dick. Valencia never gets it.
# They are one class, not three individuals: same schools, same gym, same dentist,
# same certainty. The satire reads as structural only if the surface is uniform.
$CASTE = "the product of elite schools and a good gym - a lean maintained physique under the clothes, excellent upright posture, expensive orthodontics, clear well-rested skin with regular professional maintenance, a good haircut, groomed brows, no visible wear of any kind, no lines earned from worry; a completely untroubled face that has never been seriously contradicted and does not know that is unusual; the settled physical ease of someone who has never once worried about money"

# Wildean law guard, phrased positively. Certainty, never smugness - a smug face is a
# wink to the audience, and v11 forbids winks.
$LAW = "pleasant, serene and entirely certain, calm and unbothered, an open untroubled expression, well-rested and comfortable"

$FRAME = "head-and-shoulders portrait framed just below the collarbone, hands out of frame, straight-on to camera, plain unlit grey backdrop, mouth closed with the lips together, jaw relaxed, eyes steady on the lens, blank unmarked clothing with no printed graphics"
$LOOK = "even neutral daylight-balanced exposure, soft frontal key, shadows open and detailed, natural skin tones, sharp focus on the eyes, photographic realism, documentary portrait, shot on a 85mm lens"

$sets = @(
 @{p="SUM"; core="a woman in her early forties maintained to read younger, patrician bearing, slim and strong, a well-cut dark blazer over a fine plain knit in expensive unpatterned fabric, no logo, one minimal earring";
   vars=@("dark hair drawn back with salon precision, narrow face, flawless",
          "ash-blonde in a low chignon, narrow face, lightly tanned",
          "chestnut at the shoulder, medium-width face, glowing skin",
          "sleek jaw-length bob, medium-width face, discreetly cosmetically maintained")}
 @{p="PEN"; core="a man in his late forties, tall and heavy through the shoulders in the way of a man who lifts, immaculate dark suiting in fine wool, a crisp white shirt, every detail correct";
   vars=@("full hair greying handsomely at the temples, square jaw, deep even tan",
          "close-cropped silvering hair, thick neck, athletic bulk under the suit",
          "dark hair combed back with care, strong brow, clean-shaven and gleaming",
          "receding hairline worn confidently, broad frame, expensively maintained")}
 @{p="DIC"; core="a man in his early thirties, athletic and lean, visibly gym-built shoulders under a beautifully cut heritage workwear jacket over a plain fitted tee, costly clothes styled to look casual";
   vars=@("collar-length hair with an expensive cut, thin wire-frame glasses, perfect teeth",
          "shoulder-length hair tucked behind the ears, no glasses, tanned and clear",
          "chin-length waves, wire-frame glasses, boyish and immaculate",
          "shorter grown-out hair pushed back, no glasses, strong jaw and open smile-free face")}
)

$results = @()
foreach ($s in $sets) {
  for ($i=1; $i -le $s.vars.Count; $i++) {
    $id = "{0}-K{1:D2}" -f $s.p, $i
    $prompt = ($s.core, $CASTE, $s.vars[$i-1], $LAW, $FRAME, $LOOK) -join ", "
    "{0} creating..." -f $id | Out-File $log -Append -Encoding ascii
    try {
      $raw = higgsfield generate create soul_cinematic --prompt $prompt --aspect-ratio "3:2" --quality 2k --wait --wait-timeout 6m --json 2>&1 | Out-String
      $job = ($raw | ConvertFrom-Json)[0]
      $results += [pscustomobject]@{ id=$id; job_id=$job.id; seed=$job.params.seed; result_url=$job.result_url; status=$job.status }
      "{0} {1}" -f $id, $job.status | Out-File $log -Append -Encoding ascii
      if ($job.result_url) { Invoke-WebRequest -Uri $job.result_url -OutFile (Join-Path $dest ("{0}.png" -f $id)) -UseBasicParsing -TimeoutSec 120 }
    } catch {
      $results += [pscustomobject]@{ id=$id; status="ERROR"; error=$_.Exception.Message }
      "{0} ERROR {1}" -f $id, $_.Exception.Message | Out-File $log -Append -Encoding ascii
    }
    $results | ConvertTo-Json -Depth 5 | Set-Content $out -Encoding ascii
  }
}
"DONE {0}/12" -f ($results | Where-Object { $_.status -eq "completed" }).Count | Out-File $log -Append -Encoding ascii
