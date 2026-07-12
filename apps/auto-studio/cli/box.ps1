# box.ps1 — control the ilyrium EC2 GPU box (ubuntu-qwen-gpu) from your desktop via AWS SSM.
# No SSH key needed. Run from anywhere; the AWS CLI is global.
#
#   .\box.ps1 start              # boot the box and wait until SSM is ready
#   .\box.ps1 stop               # stop the box (ENDS ~$1.20/hr billing)
#   .\box.ps1 status             # instance state + SSM ping + GPU/ollama snapshot
#   .\box.ps1 run "nvidia-smi"   # run one shell command on the box, print its output
#   .\box.ps1 shell              # open an interactive SSM shell (runs as root)
#   .\box.ps1 ip                 # print the current public IP (for SSH tunnels, ComfyUI, etc.)
#   .\box.ps1 prompt "an idea"   # qwen3-coder expands an idea into an image prompt (no render)
#   .\box.ps1 gen "an idea" [-Model zimage|flux2] [-Seed 7] [-Raw] [-Open]
#                                # qwen3-coder prompt -> ComfyUI -> PNG, auto-scp'd into .\renders\
#   .\box.ps1 tunnel             # open SSH tunnels: 8188 (ComfyUI) + 11434 (ollama), background
#   .\box.ps1 tunnel-down        # close the SSH tunnels
#
# The box is SSM-managed via the ilyrium-qwen-ssm-role instance profile.
# 'gen'/'prompt' ship ilyrium_gen.py to the box and run it with the ComfyUI venv python.
# 'gen' pulls the finished PNG down over scp (using the PEM) into the local renders\ folder.

param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'stop', 'status', 'run', 'shell', 'ip', 'gen', 'prompt', 'tunnel', 'tunnel-down')]
    [string]$Action = 'status',

    [Parameter(Position = 1, ValueFromRemainingArguments = $true)]
    [string[]]$Rest,

    [ValidateSet('zimage', 'flux2', 'flux2-klein-9b-uncensored')]
    [string]$Model = 'zimage',

    [int]$Seed = 42,

    [switch]$Raw,

    [switch]$Open   # gen: open the pulled image in the default viewer
)

$ErrorActionPreference = 'Stop'
$InstanceId = 'i-04b439af98c8faf5e'   # ubuntu-qwen-gpu, g6.2xlarge, NVIDIA L4
$Pem        = 'C:\Users\bradu\.ssh\ubuntu-qwen-gpu.pem'
$SshUser    = 'ubuntu'
$RendersDir = Join-Path $PSScriptRoot 'renders'
# Common SSH opts: no host-key prompt, no known_hosts churn (matches start_studio.ps1).
$SshOpts    = @('-o', 'StrictHostKeyChecking=no', '-o', 'UserKnownHostsFile=/dev/null', '-o', 'LogLevel=ERROR')

function Get-State {
    aws ec2 describe-instances --instance-ids $InstanceId `
        --query "Reservations[].Instances[].State.Name" --output text
}

function Get-Ip {
    aws ec2 describe-instances --instance-ids $InstanceId `
        --query "Reservations[].Instances[].PublicIpAddress" --output text
}

function Get-TunnelPids([int]$LocalPort) {
    # ssh.exe processes forwarding this local port.
    Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
        Where-Object { $_.CommandLine -match "$LocalPort`:" }
}

function Open-Tunnel {
    if (-not (Test-Path $Pem)) { Write-Host "PEM not found: $Pem" -ForegroundColor Red; return $false }
    if ((Get-State) -ne 'running') { Write-Host "Box is not running. Run  .\box.ps1 start  first." -ForegroundColor Yellow; return $false }
    $ip = Get-Ip
    $forwards = @{ 8188 = 'ComfyUI'; 11434 = 'ollama' }
    foreach ($port in $forwards.Keys) {
        if (Get-TunnelPids $port) { Write-Host "Tunnel :$port already up ($($forwards[$port]))." -ForegroundColor DarkGray; continue }
        $a = $SshOpts + @('-o', 'ServerAliveInterval=60', '-i', $Pem, '-N',
            '-L', "$port`:127.0.0.1:$port", "$SshUser@$ip")
        $p = Start-Process ssh -ArgumentList $a -WindowStyle Hidden -PassThru
        Write-Host "Tunnel :$port -> $($forwards[$port])  (ssh PID $($p.Id))" -ForegroundColor Green
    }
    return $true
}

function Close-Tunnel {
    foreach ($port in 8188, 11434) {
        Get-TunnelPids $port | ForEach-Object {
            Stop-Process -Id $_.ProcessId -Force
            Write-Host "Closed tunnel :$port (PID $($_.ProcessId))"
        }
    }
}

function Copy-Render([string]$RemotePath) {
    # scp a single rendered PNG from the box into the local renders\ folder.
    if (-not (Test-Path $RendersDir)) { New-Item -ItemType Directory -Path $RendersDir | Out-Null }
    $ip = Get-Ip
    $leaf = Split-Path $RemotePath -Leaf
    # Prefix with model+seed+timestamp-free counter uniqueness via remote leaf; if clash, add suffix.
    $dest = Join-Path $RendersDir $leaf
    if (Test-Path $dest) {
        $base = [IO.Path]::GetFileNameWithoutExtension($leaf); $ext = [IO.Path]::GetExtension($leaf)
        $n = 1; while (Test-Path (Join-Path $RendersDir "$base`_$n$ext")) { $n++ }
        $dest = Join-Path $RendersDir "$base`_$n$ext"
    }
    & scp @SshOpts -i $Pem "$SshUser@${ip}:$RemotePath" $dest 2>$null
    if ($LASTEXITCODE -eq 0 -and (Test-Path $dest)) {
        $kb = [math]::Round((Get-Item $dest).Length / 1KB)
        Write-Host "SAVED    : renders\$(Split-Path $dest -Leaf)  (${kb} KB)" -ForegroundColor Green
        return $dest
    }
    Write-Host "scp failed for $RemotePath (exit $LASTEXITCODE)" -ForegroundColor Yellow
    return $null
}

function Push-Reference([string]$LocalImg) {
    # Upload a local reference image to ComfyUI /input via its /upload/image
    # endpoint (over the box's scp), returning the name to pass as --img.
    if (-not (Test-Path $LocalImg)) { Write-Host "reference not found: $LocalImg" -ForegroundColor Yellow; return $null }
    $ip = Get-Ip
    $leaf = 'ref_' + [IO.Path]::GetFileName($LocalImg)
    # scp the file to /tmp on the box, then curl it into ComfyUI's input dir.
    & scp @SshOpts -i $Pem $LocalImg "$SshUser@${ip}:/tmp/$leaf" 2>$null
    if ($LASTEXITCODE -ne 0) { Write-Host "scp of reference failed" -ForegroundColor Yellow; return $null }
    $up = "curl -s -F image=@/tmp/$leaf -F overwrite=true http://127.0.0.1:8188/upload/image"
    $resp = Invoke-BoxCommand @($up)
    if ($resp -match '"name":\s*"([^"]+)"') { return $Matches[1] }
    Write-Host "upload to ComfyUI failed: $resp" -ForegroundColor Yellow
    return $null
}

function Invoke-Generator([string]$Idea, [string]$Model, [int]$Seed, [bool]$RawFlag, [bool]$PromptOnly, [bool]$OpenFlag) {
    # Ship the CLI + the shared ComfyUI engine + the model registry to the box
    # (base64, single layer each). ilyrium_gen.py is a thin CLI over
    # comfyui_engine.py, which reads model_registry.json next to it.
    $shipFiles = [ordered]@{
        'ilyrium_gen.py'      = Join-Path $PSScriptRoot 'ilyrium_gen.py'
        'comfyui_engine.py'   = Join-Path $PSScriptRoot '..\media\comfyui_engine.py'
        'model_registry.json' = Join-Path $PSScriptRoot '..\model_registry.json'
    }
    $shipCmds = @()
    foreach ($name in $shipFiles.Keys) {
        $local = $shipFiles[$name]
        if (-not (Test-Path $local)) { Write-Host "Missing $local" -ForegroundColor Red; return }
        $b64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes($local))
        $shipCmds += "echo $b64 | base64 -d | sudo -u ubuntu tee /home/ubuntu/$name >/dev/null"
    }
    Invoke-BoxCommand $shipCmds | Out-Null

    $venv = '/home/ubuntu/ComfyUI/venv/bin/python'
    $ideaEsc = $Idea.Replace('"', '\"')
    $genArgs = "`"$ideaEsc`" --model $Model --seed $Seed"
    if ($RawFlag)    { $genArgs += " --raw" }
    if ($PromptOnly) { $genArgs += " --prompt-only" }
    # Optional size / img2img settings passed by the REPL via env vars.
    if ($env:ILY_WIDTH)  { $genArgs += " --width $($env:ILY_WIDTH)" }
    if ($env:ILY_HEIGHT) { $genArgs += " --height $($env:ILY_HEIGHT)" }
    # Iterative edit: prior scene's prompt, base64'd to dodge shell escaping.
    if ($env:ILY_BASEPROMPT) {
        $bpB64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($env:ILY_BASEPROMPT))
        $genArgs += " --base-prompt-b64 $bpB64"
    }
    if ($env:ILY_REF -and -not $PromptOnly) {
        $refName = Push-Reference $env:ILY_REF
        if ($refName) {
            $genArgs += " --img `"$refName`""
            if ($env:ILY_DENOISE) { $genArgs += " --denoise $($env:ILY_DENOISE)" }
            # Region -> build a rectangular inpaint mask on the box (no file).
            if ($env:ILY_REGION) {
                $genArgs += " --region $($env:ILY_REGION)"
                Write-Host "inpaint region: $($env:ILY_REGION) on '$refName'" -ForegroundColor DarkCyan
            }
            # Mask file -> inpainting (only the masked region changes).
            elseif ($env:ILY_MASK) {
                $maskName = Push-Reference $env:ILY_MASK
                if ($maskName) {
                    $genArgs += " --mask `"$maskName`""
                    Write-Host "inpaint: reference '$refName' + mask '$maskName'" -ForegroundColor DarkCyan
                }
            } else {
                Write-Host "img2img: reference '$refName' (denoise $($env:ILY_DENOISE))" -ForegroundColor DarkCyan
            }
        }
    }
    $cmd = "cd /home/ubuntu && sudo -u ubuntu $venv ilyrium_gen.py $genArgs 2>&1"

    # SaveImage / model load can take minutes on first run — long SSM timeout and poll.
    $cmdId = Send-SsmCommand $cmd 900
    Write-Host "Generating (model=$Model, seed=$Seed)... first load can take 1-3 min." -ForegroundColor Cyan
    for ($i = 0; $i -lt 90; $i++) {
        $st = aws ssm get-command-invocation --command-id $cmdId --instance-id $InstanceId --query "Status" --output text 2>$null
        if ($st -ne 'InProgress' -and $st -ne 'Pending') { break }
        Start-Sleep -Seconds 5
    }
    $out = aws ssm get-command-invocation --command-id $cmdId --instance-id $InstanceId --query "StandardOutputContent" --output text
    if ($out) { Write-Output $out.TrimEnd() }
    if ($st -ne 'Success') { Write-Host "[status] $st" -ForegroundColor Yellow; return }

    if ($PromptOnly) { return }

    # Parse the "IMAGE: <remote path>" line and pull it down via scp.
    $imgLine = ($out -split "`n") | Where-Object { $_ -match '^IMAGE:\s*(.+)$' } | Select-Object -Last 1
    if ($imgLine -and $imgLine -match '^IMAGE:\s*(.+?)\s*$') {
        $remote = $Matches[1]
        $local = Copy-Render $remote
        if ($local -and $OpenFlag) { Start-Process $local }
    } else {
        Write-Host "No IMAGE path in output; nothing to pull." -ForegroundColor Yellow
    }
}

function Send-SsmCommand([string]$Script, [int]$TimeoutSeconds = 600) {
    # Version-independent SSM send: base64-wrap the script so the JSON payload
    # contains ONLY base64 + a fixed decode wrapper (no shell operators, no
    # quoting hazards). Windows PowerShell 5.1's ConvertTo-Json mangles keys and
    # escapes '>' as >, which AWS rejects -- so we hand-build the JSON and
    # pass it via a temp file (file://) to dodge all shell-quoting differences.
    $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($Script))
    $wrapped = "echo $b64 | base64 -d | bash"
    # Only base64 + the wrapper -- both are pure ASCII, safe to embed verbatim.
    $payload = '{"commands":["' + $wrapped + '"]}'
    $tmp = Join-Path $env:TEMP ("ssm_" + [Guid]::NewGuid().ToString('N') + '.json')
    [IO.File]::WriteAllText($tmp, $payload, (New-Object Text.UTF8Encoding($false)))
    try {
        $cmdId = aws ssm send-command --instance-ids $InstanceId `
            --document-name "AWS-RunShellScript" --timeout-seconds $TimeoutSeconds `
            --parameters "file://$tmp" --query "Command.CommandId" --output text
    } finally { Remove-Item $tmp -Force -ErrorAction SilentlyContinue }
    return $cmdId
}

function Invoke-BoxCommand([string[]]$Commands) {
    # Join multiple commands with newlines and run them as one script.
    $cmdId = Send-SsmCommand (($Commands) -join "`n")
    aws ssm wait command-executed --command-id $cmdId --instance-id $InstanceId 2>$null
    $status = aws ssm get-command-invocation --command-id $cmdId --instance-id $InstanceId --query "Status" --output text
    $out    = aws ssm get-command-invocation --command-id $cmdId --instance-id $InstanceId --query "StandardOutputContent" --output text
    $err    = aws ssm get-command-invocation --command-id $cmdId --instance-id $InstanceId --query "StandardErrorContent" --output text
    if ($out) { Write-Output $out.TrimEnd() }
    if ($err -and $err.Trim()) { Write-Host "[stderr] $($err.TrimEnd())" -ForegroundColor DarkYellow }
    if ($status -ne 'Success') { Write-Host "[status] $status" -ForegroundColor Yellow }
}

switch ($Action) {

    'start' {
        $state = Get-State
        if ($state -eq 'running') {
            Write-Host "Already running." -ForegroundColor Green
        } else {
            Write-Host "Starting $InstanceId (was: $state) ..."
            aws ec2 start-instances --instance-ids $InstanceId --query "StartingInstances[].CurrentState.Name" --output text | Out-Null
            aws ec2 wait instance-running --instance-ids $InstanceId
            Write-Host "Instance running. Waiting for SSM agent to register ..."
        }
        # Poll SSM up to ~2 min.
        for ($i = 0; $i -lt 12; $i++) {
            $ping = aws ssm describe-instance-information `
                --filters "Key=InstanceIds,Values=$InstanceId" `
                --query "InstanceInformationList[0].PingStatus" --output text 2>$null
            if ($ping -eq 'Online') { break }
            Start-Sleep -Seconds 10
        }
        Write-Host "SSM: $ping   IP: $(Get-Ip)" -ForegroundColor Green
        # Auto-start ComfyUI (needed for gen) and wait for its API to answer.
        if ($ping -eq 'Online') {
            Write-Host "Starting ComfyUI ..." -ForegroundColor DarkGray
            $ready = Invoke-BoxCommand @(
                'sudo systemctl start comfyui >/dev/null 2>&1; for i in $(seq 1 25); do curl -s -m 2 http://127.0.0.1:8188/system_stats >/dev/null 2>&1 && { echo comfyui-ready; break; }; sleep 3; done'
            )
            if ("$ready" -match 'comfyui-ready') { Write-Host "ComfyUI  : ready on :8188" -ForegroundColor Green }
            else { Write-Host "ComfyUI  : still starting (retry a gen in ~30s)" -ForegroundColor Yellow }
        }
        Write-Host "Ready. Use  .\box.ps1 gen `"<idea>`"  or  .\ilyrium.ps1  for the interactive CLI." -ForegroundColor Cyan
    }

    'stop' {
        Write-Host "Stopping $InstanceId (ends billing) ..."
        aws ec2 stop-instances --instance-ids $InstanceId --query "StoppingInstances[].CurrentState.Name" --output text
        Write-Host "Stop requested. Billing ends once state reaches 'stopped'." -ForegroundColor Green
    }

    'status' {
        $state = Get-State
        Write-Host "Instance : $InstanceId ($state)" -ForegroundColor Cyan
        if ($state -eq 'running') {
            $ping = aws ssm describe-instance-information `
                --filters "Key=InstanceIds,Values=$InstanceId" `
                --query "InstanceInformationList[0].PingStatus" --output text 2>$null
            Write-Host "SSM      : $ping"
            Write-Host "IP       : $(Get-Ip)"
            if ($ping -eq 'Online') {
                Write-Host "--- box snapshot ---"
                Invoke-BoxCommand @(
                    'nvidia-smi --query-gpu=name,memory.used,memory.total --format=csv,noheader 2>/dev/null || echo NO_GPU',
                    'echo ollama: $(systemctl is-active ollama 2>/dev/null)'
                )
            }
        } else {
            Write-Host "(start it with  .\box.ps1 start )"
        }
    }

    'run' {
        if (-not $Rest) { Write-Host "Usage: .\box.ps1 run `"<shell command>`"" -ForegroundColor Yellow; break }
        if ((Get-State) -ne 'running') { Write-Host "Box is not running. Run  .\box.ps1 start  first." -ForegroundColor Yellow; break }
        Invoke-BoxCommand @(($Rest -join ' '))
    }

    'shell' {
        if ((Get-State) -ne 'running') { Write-Host "Box is not running. Run  .\box.ps1 start  first." -ForegroundColor Yellow; break }
        $plugin = "C:\Program Files\Amazon\SessionManagerPlugin\bin"
        if (-not ($env:Path -split ';' | Where-Object { $_ -eq $plugin })) { $env:Path += ";$plugin" }
        Write-Host "Opening SSM shell on $InstanceId (Ctrl-D / 'exit' to leave; runs as root) ..." -ForegroundColor Cyan
        aws ssm start-session --target $InstanceId
    }

    'prompt' {
        if (-not $Rest) { Write-Host "Usage: .\box.ps1 prompt `"<idea>`" [-Model zimage|flux2]" -ForegroundColor Yellow; break }
        if ((Get-State) -ne 'running') { Write-Host "Box is not running. Run  .\box.ps1 start  first." -ForegroundColor Yellow; break }
        Invoke-Generator ($Rest -join ' ') $Model $Seed $false $true $false
    }

    'gen' {
        if (-not $Rest) { Write-Host "Usage: .\box.ps1 gen `"<idea>`" [-Model zimage|flux2] [-Seed N] [-Raw] [-Open]" -ForegroundColor Yellow; break }
        if ((Get-State) -ne 'running') { Write-Host "Box is not running. Run  .\box.ps1 start  first." -ForegroundColor Yellow; break }
        Invoke-Generator ($Rest -join ' ') $Model $Seed ([bool]$Raw) $false ([bool]$Open)
    }

    'tunnel'      { Open-Tunnel | Out-Null }
    'tunnel-down' { Close-Tunnel }

    'ip' { Get-Ip }
}
