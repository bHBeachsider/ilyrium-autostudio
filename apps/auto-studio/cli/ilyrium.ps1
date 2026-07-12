# ilyrium.ps1 -- interactive image-generation CLI for the ilyrium studio box.
#
# Launch once:   .\ilyrium.ps1
# It boots the box (if needed), starts ComfyUI, then drops you into a prompt
# loop. Type an idea -> it generates with flux2/z-image, saves to .\renders\,
# and shows the path. Reference-image (img2img) prompts via :img.
#
# How it flows:
#   First prompt        -> a fresh image.
#   Any follow-up text  -> EDITS the current image (img2img on it, and qwen3 is
#                          given the previous prompt so 'make it darker' means
#                          'that same scene, but darker'). Keep typing changes to
#                          iterate. :new starts a clean scene.
#
# In-loop commands:
#   <any text>          fresh image if none yet, else edit the current image
#   :new [text]         start a clean scene (clears context); generate if text given
#   :fresh [text]       alias of :new
#   :edit <change>      force-edit the current image with this change
#   :edit-of <name> <change>  edit a SPECIFIC image (by renders name/number)
#   :region x1,y1,x2,y2 build a rectangular inpaint mask from coords (fractions
#                       0-1 or pixels) -- no mask file needed. e.g.
#                       :region 0.5,0.2,0.9,0.8  then  :edit-of <img> <change>
#   :region off         clear the region
#   :mask <path>        mask image for inpainting (white=change, black=keep);
#                       use with :edit-of/:img for targeted region edits
#   :mask off           clear the mask
#   :ask <question>     ask the CLI something (model/seed/size) -- no generation
#   :reset              clear the edit context (no generation)
#   :current            show the current image + prompt being edited
#   :raw <text>         use the text verbatim as the prompt (skip qwen, fresh)
#   :img <path|name>    use an image (renders name or path) as reference for NEXT
#   :img off            clear a queued reference
#   :model flux2|zimage switch model
#   :seed <n> | :seed r seed (r = random each render)
#   :denoise <0..1>     edit strength (lower = closer to the current image)
#   :subtle             preset: denoise 0.4 (small change, stays on-image)
#   :strong             preset: denoise 0.8 (big change, looser)
#   :size <w> <h>       output size (default 1024 1024)
#   :open on|off        auto-open each image in the viewer
#   :tunnel             open ComfyUI (:8188) + ollama (:11434) tunnels
#   :status             box + ComfyUI status
#   :help               show commands
#   :quit / :q          leave the loop (box keeps running)
#   :stop               stop the box (ends billing) and exit

$ErrorActionPreference = 'Stop'
$Box = Join-Path $PSScriptRoot 'box.ps1'
if (-not (Test-Path $Box)) { Write-Host "box.ps1 not found next to ilyrium.ps1" -ForegroundColor Red; exit 1 }

# --- session state -----------------------------------------------------------
$state = @{ model = 'zimage'; seed = 42; randseed = $false; denoise = 0.65;
    width = 1024; height = 1024; ref = $null; open = $false;
    lastImage = $null; lastPrompt = $null; mask = $null; region = $null }
$RendersDir = Join-Path $PSScriptRoot 'renders'

function Resolve-Render([string]$name) {
    # Turn a user-typed image name/number into a full path under renders\.
    # Accepts: full path, 'renders\foo.png', 'foo.png', 'foo', or a numeric
    # id that appears in a filename (e.g. '00002' -> zimage_42_00002_.png).
    if (-not $name) { return $null }
    if (Test-Path $name) { return (Resolve-Path $name).Path }
    $direct = Join-Path $RendersDir (Split-Path $name -Leaf)
    if (Test-Path $direct) { return (Resolve-Path $direct).Path }
    if ((Test-Path "$direct.png")) { return (Resolve-Path "$direct.png").Path }
    # numeric / substring match against files in renders\
    $hit = Get-ChildItem $RendersDir -Filter '*.png' -ErrorAction SilentlyContinue |
        Where-Object { $_.Name -like "*$name*" } |
        Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($hit) { return $hit.FullName }
    return $null
}

function Say($msg, $color = 'Gray') { Write-Host $msg -ForegroundColor $color }

function Ensure-Ready {
    # box.ps1 start is idempotent (says 'Already running' if up), waits for SSM,
    # and now auto-starts ComfyUI + waits for its API. Nothing else needed here.
    & $Box start | Out-Host
}

function Show-Banner {
    Say ""
    Say "==== ILYRIUM STUDIO CLI ====" Cyan
    Say "model=$($state.model)  seed=$(if($state.randseed){'random'}else{$state.seed})  size=$($state.width)x$($state.height)  denoise=$($state.denoise)  ref=$(if($state.ref){Split-Path $state.ref -Leaf}else{'none'})" DarkGray
    Say "Type an idea to start. Follow-ups EDIT that image (:new for a fresh one)." DarkGray
    Say ":help for commands, :quit to leave." DarkGray
    Say ""
}

function Do-Generate([string]$idea, [bool]$raw, [bool]$edit) {
    # $edit = true means "modify the current image": use the last output as the
    # img2img reference AND give qwen3 the last prompt as context.
    if (-not $idea) { Say "(empty prompt)" Yellow; return }
    if ($state.randseed) { $state.seed = Get-Random -Minimum 1 -Maximum 2147483647 }

    $genArgs = @('gen', $idea, '-Model', $state.model, '-Seed', $state.seed)
    if ($raw) { $genArgs += '-Raw' }
    if ($state.open) { $genArgs += '-Open' }

    $env:ILY_WIDTH = $state.width; $env:ILY_HEIGHT = $state.height
    $env:ILY_DENOISE = $state.denoise

    # Reference image: explicit :img wins; otherwise, in edit mode, the last image.
    $refPath = if ($state.ref) { $state.ref }
               elseif ($edit -and $state.lastImage) { $state.lastImage }
               else { '' }
    $env:ILY_REF = $refPath

    # Prompt context: in edit mode, hand qwen3 the previous prompt.
    $env:ILY_BASEPROMPT = if ($edit -and $state.lastPrompt) { $state.lastPrompt } else { '' }

    # Mask / region -> inpainting (only that area changes). Needs a reference.
    $env:ILY_MASK = if ($state.mask -and $refPath) { $state.mask } else { '' }
    $env:ILY_REGION = if ($state.region -and $refPath) { $state.region } else { '' }

    if ($env:ILY_REGION) {
        Say "inpainting region $($state.region) of $(Split-Path $refPath -Leaf)" DarkCyan
    } elseif ($env:ILY_MASK) {
        Say "inpainting $(Split-Path $refPath -Leaf) with mask $(Split-Path $state.mask -Leaf)" DarkCyan
    } elseif ($edit -and $refPath) {
        Say "editing $(Split-Path $refPath -Leaf) (denoise $($state.denoise))" DarkCyan
    }

    # Capture box.ps1 output so we can remember the new image + prompt.
    $captured = & $Box @genArgs 2>&1 | ForEach-Object { $_ | Out-Host; $_ }
    $text = ($captured | Out-String)

    if ($text -match 'PROMPT:\s*(.+)') { $state.lastPrompt = $Matches[1].Trim() }
    $saved = ($text -split "`n") | Where-Object { $_ -match 'SAVED\s*:\s*(renders\\[^\s]+)' } | Select-Object -Last 1
    if ($saved -and $saved -match 'SAVED\s*:\s*(renders\\[^\s]+)') {
        $rel = $Matches[1].Trim()
        $abs = Join-Path $PSScriptRoot $rel
        if (Test-Path $abs) { $state.lastImage = (Resolve-Path $abs).Path }
    }
    # A one-off :img reference and :mask are consumed after a single use;
    # edit-chaining then continues from the produced image.
    if ($state.ref) { $state.ref = $null }
    if ($state.mask) { $state.mask = $null }
    if ($state.region) { $state.region = $null }
}

# --- boot --------------------------------------------------------------------
Ensure-Ready
Show-Banner

# --- REPL --------------------------------------------------------------------
while ($true) {
    Write-Host "ilyrium-autostudio> " -ForegroundColor Green -NoNewline
    $line = Read-Host
    if ($null -eq $line) { break }
    $line = $line.Trim()
    if (-not $line) { continue }

    # Plain text (no leading ':'): if we have a current image and no explicit
    # :img is queued, treat this as an EDIT of that image. Otherwise fresh.
    if ($line -notmatch '^:') {
        # Guard: input that looks like a question is probably NOT a prompt.
        if ($line -match '\?\s*$' -or $line -match '^(which|what|what''s|how|is|are|do|does|can|why|where|when|who)\b') {
            Say "That looks like a question, not an image prompt." Yellow
            Say "  - to ASK the CLI something:      :ask $line" DarkGray
            Say "  - to generate anyway:            :raw $line   (fresh) or  :edit $line   (edit current)" DarkGray
            continue
        }
        $isEdit = [bool]($state.lastImage -and -not $state.ref)
        Do-Generate $line $false $isEdit
        continue
    }

    $parts = $line -split '\s+', 2
    $cmd = $parts[0].ToLower()
    $arg = if ($parts.Count -gt 1) { $parts[1].Trim() } else { '' }

    switch ($cmd) {
        ':help'  { Get-Content $PSCommandPath | Select-String '^#   ' | ForEach-Object { Say ($_ -replace '^#   ', '  ') } }
        ':quit'  { Say "Leaving (box still running -- .\box.ps1 stop to end billing)." Cyan; break }
        ':q'     { Say "Leaving (box still running -- .\box.ps1 stop to end billing)." Cyan; break }
        ':stop'  { & $Box stop | Out-Host; break }
        ':status' { & $Box status | Out-Host }
        ':tunnel' { & $Box tunnel | Out-Host }
        ':model' {
            if ($arg -in 'flux2', 'zimage') { $state.model = $arg; Say "model -> $arg" Cyan }
            elseif (-not $arg) {
                Say "current image model: $($state.model)" Cyan
                Say "  (prompts are written by qwen3-coder on the box; images by $($state.model))" DarkGray
                Say "  switch with: :model flux2|zimage" DarkGray
            }
            else { Say "usage: :model flux2|zimage  (or :model to show current)" Yellow }
        }
        ':ask' {
            if (-not $arg) { Say "usage: :ask <question about the CLI/box>" Yellow }
            else {
                # Answer common meta questions locally; no image is generated.
                switch -regex ($arg.ToLower()) {
                    'model|connected' {
                        Say "Image model: $($state.model) (on the EC2 box's ComfyUI)." Cyan
                        Say "Prompt writer: qwen3-coder:latest via ollama on the box." Cyan
                    }
                    'seed'      { Say "seed: $(if($state.randseed){'random each render'}else{$state.seed})" Cyan }
                    'size|resolution' { Say "size: $($state.width)x$($state.height)" Cyan }
                    'denoise|strength' { Say "denoise/edit-strength: $($state.denoise)" Cyan }
                    'current|last|editing' {
                        if ($state.lastImage) { Say "current image: $(Split-Path $state.lastImage -Leaf)" Cyan }
                        else { Say "no current image yet" Yellow }
                    }
                    default { Say "I can answer: model, seed, size, denoise, current. For anything else, ask outside the REPL." Yellow }
                }
            }
        }
        ':seed' {
            if ($arg -eq 'r') { $state.randseed = $true; Say "seed -> random each render" Cyan }
            elseif ($arg -match '^\d+$') { $state.seed = [int]$arg; $state.randseed = $false; Say "seed -> $arg" Cyan }
            else { Say "usage: :seed <n> | :seed r" Yellow }
        }
        ':denoise' {
            if ($arg -match '^0?\.\d+$|^1(\.0)?$') { $state.denoise = [double]$arg; Say "denoise -> $arg" Cyan }
            else { Say "usage: :denoise 0.0-1.0" Yellow }
        }
        ':subtle' { $state.denoise = 0.4; Say "denoise -> 0.4 (subtle: stays close to the current image)" Cyan }
        ':strong' { $state.denoise = 0.8; Say "denoise -> 0.8 (strong: allows bigger changes)" Cyan }
        ':size' {
            $wh = $arg -split '\s+'
            if ($wh.Count -eq 2 -and $wh[0] -match '^\d+$' -and $wh[1] -match '^\d+$') {
                $state.width = [int]$wh[0]; $state.height = [int]$wh[1]; Say "size -> $($wh[0])x$($wh[1])" Cyan
            } else { Say "usage: :size <w> <h>" Yellow }
        }
        ':open' {
            if ($arg -eq 'on') { $state.open = $true; Say "auto-open ON" Cyan }
            elseif ($arg -eq 'off') { $state.open = $false; Say "auto-open OFF" Cyan }
            else { Say "usage: :open on|off" Yellow }
        }
        ':img' {
            if ($arg -eq 'off') { $state.ref = $null; Say "reference cleared (text-to-image)" Cyan }
            else {
                $p = Resolve-Render $arg
                if ($p) { $state.ref = $p; Say "reference -> $(Split-Path $p -Leaf) (img2img on; :denoise $($state.denoise))" Cyan }
                else { Say "usage: :img <path or renders name> | :img off  (not found: $arg)" Yellow }
            }
        }
        ':mask' {
            if ($arg -eq 'off') { $state.mask = $null; Say "mask cleared" Cyan }
            else {
                $p = Resolve-Render $arg
                if ($p) { $state.mask = $p; Say "mask -> $(Split-Path $p -Leaf) (white=change, black=keep; use with :edit-of or :img)" Cyan }
                else { Say "usage: :mask <path to mask image> | :mask off  (not found: $arg)" Yellow }
            }
        }
        ':region' {
            if ($arg -eq 'off') { $state.region = $null; Say "region cleared" Cyan }
            elseif ($arg -match '^\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*,\s*[\d.]+\s*$') {
                $state.region = ($arg -replace '\s', '')
                Say "region -> $($state.region) (rectangular inpaint mask; fractions 0-1 or pixels). Next :edit-of/:img edit only this box." Cyan
            }
            else { Say "usage: :region x1,y1,x2,y2   e.g. :region 0.5,0.2,0.9,0.8  (fractions or pixels) | :region off" Yellow }
        }
        ':raw' { Do-Generate $arg $true $false }
        ':edit' {
            if (-not $state.lastImage) { Say "no current image yet -- generate one first" Yellow }
            elseif (-not $arg) { Say "usage: :edit <change to apply>" Yellow }
            else { Do-Generate $arg $false $true }
        }
        ':edit-of' {
            # Edit a SPECIFIC image by name/number instead of the last one.
            $eparts = $arg -split '\s+', 2
            $target = Resolve-Render $eparts[0]
            $change = if ($eparts.Count -gt 1) { $eparts[1].Trim() } else { '' }
            if (-not $target) { Say "usage: :edit-of <renders name/number> <change>  (not found: $($eparts[0]))" Yellow }
            elseif (-not $change) { Say "usage: :edit-of <name> <change to apply>" Yellow }
            else {
                # Point the edit at the chosen image: set it as lastImage so
                # Do-Generate's edit path uses it; clear stale prompt context.
                $state.lastImage = $target; $state.lastPrompt = $null
                Say "editing $(Split-Path $target -Leaf)" DarkCyan
                Do-Generate $change $false $true
            }
        }
        { $_ -in ':new', ':fresh' } {
            # Start a clean scene: drop the current image/prompt context, then
            # (if text was given) generate fresh from it.
            $state.lastImage = $null; $state.lastPrompt = $null; $state.ref = $null
            if ($arg) { Do-Generate $arg $false $false }
            else { Say "context cleared -- next prompt starts a fresh image" Cyan }
        }
        ':reset' {
            $state.lastImage = $null; $state.lastPrompt = $null; $state.ref = $null
            Say "edit context cleared" Cyan
        }
        ':current' {
            if ($state.lastImage) { Say "current image : $(Split-Path $state.lastImage -Leaf)" Cyan; Say "current prompt: $($state.lastPrompt)" DarkGray }
            else { Say "no current image yet" Yellow }
        }
        default { Say "unknown command $cmd (:help for list)" Yellow }
    }
}
