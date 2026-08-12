[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('status', 'claim', 'verify', 'complete', 'audit', 'recover', 'release')]
    [string]$Action,
    [string]$QueueRoot,
    [string]$EvidenceRoot,
    [string]$TemplateRoot,
    [string]$SchemaPath,
    [string]$Owner = $env:USERNAME,
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$ClaimToken,
    [string]$CompletionNote,
    [switch]$AuthorizeLive,
    [string]$AuthorizationNote,
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
if (-not $QueueRoot) { $QueueRoot = Join-Path $repoRoot 'waves' }
if (-not $EvidenceRoot) { $EvidenceRoot = Join-Path $repoRoot '.agent-runs\evidence' }
if (-not $TemplateRoot) { $TemplateRoot = Join-Path $scriptRoot 'wave-templates' }
if (-not $SchemaPath) { $SchemaPath = Join-Path $scriptRoot 'packet-verdict.schema.json' }
$QueueRoot = [IO.Path]::GetFullPath($QueueRoot)
$EvidenceRoot = [IO.Path]::GetFullPath($EvidenceRoot)
$TemplateRoot = [IO.Path]::GetFullPath($TemplateRoot)
$SchemaPath = [IO.Path]::GetFullPath($SchemaPath)
$waitingRoot = Join-Path $QueueRoot 'waiting'
$doneRoot = Join-Path $QueueRoot 'done'
$stateRoot = Join-Path $QueueRoot '.state'
$claimPath = Join-Path $stateRoot 'claim.json'
$lockPath = Join-Path $stateRoot 'queue.lock'

function Write-Utf8([string]$Path, [string]$Text) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    $temporary = Join-Path $parent ('.' + [IO.Path]::GetFileName($Path) + '.' + [guid]::NewGuid().ToString('N') + '.tmp')
    [IO.File]::WriteAllText($temporary, $Text, $utf8NoBom)
    Move-Item -LiteralPath $temporary -Destination $Path -Force
}

function Read-Json([string]$Path) {
    if (-not (Test-Path -LiteralPath $Path)) { return $null }
    return (Get-Content -Raw -LiteralPath $Path | ConvertFrom-Json)
}

function Get-WaveInfo([IO.FileInfo]$File) {
    if ($File.Name -notmatch '^wave_(\d{2})_[a-z0-9_]+\.md$') {
        throw "Malformed wave filename: $($File.Name)"
    }
    return [pscustomobject]@{ Number = [int]$matches[1]; Id = "WAVE_$($matches[1])"; File = $File; Name = $File.Name }
}

function Get-Catalog {
    if (-not (Test-Path -LiteralPath $TemplateRoot)) { throw "Template root does not exist: $TemplateRoot" }
    $items = @(Get-ChildItem -LiteralPath $TemplateRoot -Filter 'wave_*.md' -File | Sort-Object Name)
    if ($items.Count -eq 0) { throw 'No canonical wave templates were found.' }
    $infos = @($items | ForEach-Object { Get-WaveInfo $_ })
    $numbers = @($infos | ForEach-Object { $_.Number })
    if (($numbers | Select-Object -Unique).Count -ne $numbers.Count) { throw 'Duplicate wave numbers exist in the template catalog.' }
    for ($index = 0; $index -lt $infos.Count; $index++) {
        if ($infos[$index].Number -ne ($index + 1)) { throw 'Template wave numbers must be contiguous from 01.' }
    }
    return $infos
}

function Get-QueueFiles([string]$Root) {
    if (-not (Test-Path -LiteralPath $Root)) { return @() }
    return @(Get-ChildItem -LiteralPath $Root -Filter 'wave_*.md' -File | Sort-Object Name)
}

function Get-ManifestStatus([string]$Path) {
    $text = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8)
    $match = [regex]::Match($text, '(?m)^Status:\s*(.+)$')
    if (-not $match.Success) { throw "Manifest has no Status field: $Path" }
    return $match.Groups[1].Value.Trim()
}

function Set-ManifestStatus([string]$Path, [string]$Status) {
    $text = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8)
    if ($text -notmatch '(?m)^Status:\s*.+$') { throw "Manifest has no Status field: $Path" }
    $updated = [regex]::Replace($text, '(?m)^Status:\s*.+$', "Status: $Status")
    Write-Utf8 $Path $updated
}

function Enter-QueueLock {
    if (-not (Test-Path -LiteralPath $stateRoot)) { New-Item -ItemType Directory -Path $stateRoot -Force | Out-Null }
    try {
        return [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
    } catch [IO.IOException] {
        throw '[BUSY] Another wave-queue operation holds the exclusive lock.'
    }
}

function Get-Claim { return Read-Json $claimPath }

function Assert-Claim([object]$Claim) {
    if (-not $Claim) { throw '[BLOCKED] No active wave claim exists.' }
    if ([string]::IsNullOrWhiteSpace($ClaimToken) -or $Claim.token -ne $ClaimToken) {
        throw '[BLOCKED] The supplied claim token does not own the active wave.'
    }
    $manifest = Join-Path $waitingRoot $Claim.waveFile
    if (-not (Test-Path -LiteralPath $manifest)) { throw '[INVALID] The claimed manifest is not in waves/waiting.' }
    if ((Get-ManifestStatus $manifest) -ne 'active') { throw '[INVALID] The claimed manifest is not marked active.' }
    return $manifest
}

function Assert-QueueIntegrity {
    $catalog = @(Get-Catalog)
    $waiting = @(Get-QueueFiles $waitingRoot)
    $done = @(Get-QueueFiles $doneRoot)
    $all = @($waiting + $done)
    foreach ($file in $all) { [void](Get-WaveInfo $file) }
    foreach ($template in $catalog) {
        $count = @($all | Where-Object { $_.Name -eq $template.Name }).Count
        if ($count -ne 1) { throw "[INVALID] $($template.Name) must exist exactly once in waiting or done; observed $count." }
    }
    foreach ($file in $all) {
        if (-not ($catalog.Name -contains $file.Name)) { throw "[INVALID] Non-catalog wave file detected: $($file.Name)" }
    }
    $doneNumbers = @($done | ForEach-Object { (Get-WaveInfo $_).Number })
    for ($number = 1; $number -le $doneNumbers.Count; $number++) {
        if ($doneNumbers -notcontains $number) { throw '[INVALID] Done waves are not a contiguous prefix.' }
    }
    foreach ($file in $done) {
        if ((Get-ManifestStatus $file.FullName) -ne 'done') { throw "[INVALID] Manually archived manifest is not marked done: $($file.Name)" }
    }
    $claim = Get-Claim
    $active = @($waiting | Where-Object { (Get-ManifestStatus $_.FullName) -eq 'active' })
    if ($claim) {
        if ($active.Count -ne 1 -or $active[0].Name -ne $claim.waveFile) { throw '[INVALID] Claim and active manifest state disagree.' }
    } elseif ($active.Count -ne 0) {
        throw '[INVALID] Active manifest exists without a claim.'
    }
    return [pscustomobject]@{ Catalog = $catalog; Waiting = $waiting; Done = $done; Claim = $claim }
}

function Assert-Predecessors([int]$WaveNumber, [object[]]$DoneFiles) {
    $doneNumbers = @($DoneFiles | ForEach-Object { (Get-WaveInfo $_).Number })
    for ($number = 1; $number -lt $WaveNumber; $number++) {
        if ($doneNumbers -notcontains $number) { throw "[BLOCKED] Wave $WaveNumber requires Wave $number under waves/done." }
    }
}

function Get-Packets([string]$ManifestPath) {
    $packets = New-Object System.Collections.Generic.List[object]
    foreach ($line in [IO.File]::ReadAllLines($ManifestPath, [Text.Encoding]::UTF8)) {
        if ($line -notmatch '^###\s+((?:DS|SEC|LIVE)-[A-Z0-9]+)\s+') { continue }
        $id = $matches[1]
        $size = if ($id -match '^(SEC|LIVE)-') { 'Reserved' } elseif ($line -match '\(Audit') { 'Audit' } elseif ($line -match '\(Small') { 'Small' } elseif ($line -match '\(Medium') { 'Medium' } else { throw "Packet size is missing from manifest header: $line" }
        $packets.Add([pscustomobject]@{ Id = $id; Size = $size })
    }
    if ($packets.Count -eq 0) { throw "No packets found in manifest: $ManifestPath" }
    return $packets.ToArray()
}

function Assert-JsonSchema([string]$VerdictPath) {
    $validator = "import json,sys; from jsonschema import Draft202012Validator; schema=json.loads(open(sys.argv[2],'rb').read()); data=json.loads(open(sys.argv[1],'rb').read()); Draft202012Validator(schema).validate(data)"
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $validationOutput = @(& python -c $validator $VerdictPath $SchemaPath 2>&1)
        $validationExitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($validationExitCode -ne 0) {
        $preferredDetail = @($validationOutput | ForEach-Object { [string]$_ } | Where-Object { $_ -match '(ValidationError|SchemaError|JSONDecodeError|Error):' } | Select-Object -Last 1)
        $detail = if ($preferredDetail.Count) { $preferredDetail[0] } elseif ($validationOutput.Count) { [string]$validationOutput[-1] } else { 'unknown schema validation failure' }
        throw "[INVALID] Verdict does not match schema: $VerdictPath ($detail)"
    }
}

function Assert-Capacity([object]$Verdict, [string]$ExpectedSize, [string]$PacketId) {
    if (-not $Verdict.capacity) { throw "[INVALID] $PacketId verdict has no machine-readable capacity evidence." }
    $limits = @{
        Audit = @{ Files = 0; Lines = 0 }
        Small = @{ Files = 3; Lines = 200 }
        Medium = @{ Files = 5; Lines = 400 }
        Reserved = @{ Files = 0; Lines = 0 }
    }
    if ($Verdict.capacity.size -ne $ExpectedSize) { throw "[INVALID] $PacketId capacity size does not match its manifest." }
    $limit = $limits[$ExpectedSize]
    if ([int]$Verdict.capacity.maxFiles -ne $limit.Files -or [int]$Verdict.capacity.maxChangedLines -ne $limit.Lines) { throw "[INVALID] $PacketId capacity ceilings are incorrect." }
    if ([int]$Verdict.capacity.observedFiles -gt $limit.Files -or [int]$Verdict.capacity.observedChangedLines -gt $limit.Lines -or -not [bool]$Verdict.capacity.withinLimit) {
        throw "[BLOCKED] $PacketId exceeds its $ExpectedSize capacity ceiling."
    }
    if ($ExpectedSize -notin @('Audit', 'Reserved') -and @($Verdict.observedPaths).Count -ne [int]$Verdict.capacity.observedFiles) {
        throw "[INVALID] $PacketId observedFiles does not match observedPaths."
    }
}

function Verify-Wave([object]$Claim, [string]$ManifestPath, [object[]]$DoneFiles) {
    $waveNumber = [int]$Claim.waveNumber
    Assert-Predecessors $waveNumber $DoneFiles
    if ($waveNumber -eq 9 -and (-not [bool]$Claim.liveAuthorized -or [string]::IsNullOrWhiteSpace($Claim.authorizationNote))) {
        throw '[BLOCKED] Wave 09 has no recorded explicit user authorization.'
    }
    $packets = @(Get-Packets $ManifestPath)
    foreach ($packet in $packets) {
        $verdictPath = Join-Path (Join-Path (Join-Path $EvidenceRoot $Claim.waveId) $packet.Id) 'verdict.json'
        if (-not (Test-Path -LiteralPath $verdictPath)) { throw "[BLOCKED] Missing verdict: $verdictPath" }
        Assert-JsonSchema $verdictPath
        $verdict = Read-Json $verdictPath
        if ($verdict.wave -ne $Claim.waveId -or $verdict.packet -ne $packet.Id) { throw "[INVALID] Verdict identity mismatch: $verdictPath" }
        if ($verdict.verdict -ne 'PASS') { throw "[BLOCKED] $($packet.Id) verdict is $($verdict.verdict), not PASS." }
        Assert-Capacity $verdict $packet.Size $packet.Id
    }
    return $packets
}

function New-Claim([object]$Info, [string]$Token) {
    return [pscustomobject]@{
        schemaVersion = 1
        waveId = $Info.Id
        waveNumber = $Info.Number
        waveFile = $Info.Name
        status = 'active'
        owner = $Owner
        token = $Token
        machine = $env:COMPUTERNAME
        startedAt = (Get-Date).ToString('o')
        liveAuthorized = [bool]$AuthorizeLive
        authorizationNote = if ($AuthorizeLive) { $AuthorizationNote } else { $null }
    }
}

function Write-Result([object]$Value) { $Value | ConvertTo-Json -Depth 6 }

$lock = $null
try {
    if (-not (Test-Path -LiteralPath $waitingRoot)) { New-Item -ItemType Directory -Path $waitingRoot -Force | Out-Null }
    if (-not (Test-Path -LiteralPath $doneRoot)) { New-Item -ItemType Directory -Path $doneRoot -Force | Out-Null }
    $lock = Enter-QueueLock
    switch ($Action) {
        'recover' {
            if ((Get-Claim) -and -not $Force) { throw '[BLOCKED] Recovery is refused while a claim exists.' }
            $catalog = @(Get-Catalog)
            $restored = New-Object System.Collections.Generic.List[string]
            foreach ($template in $catalog) {
                $waitingPath = Join-Path $waitingRoot $template.Name
                $donePath = Join-Path $doneRoot $template.Name
                if (-not (Test-Path -LiteralPath $waitingPath) -and -not (Test-Path -LiteralPath $donePath)) {
                    Copy-Item -LiteralPath $template.File.FullName -Destination $waitingPath
                    $restored.Add($template.Name)
                }
            }
            [void](Assert-QueueIntegrity)
            Write-Result ([pscustomobject]@{ action = 'recover'; restored = @($restored.ToArray()); result = 'PASS' })
        }
        'audit' {
            $state = Assert-QueueIntegrity
            Write-Result ([pscustomobject]@{ action = 'audit'; result = 'PASS'; waiting = @($state.Waiting | ForEach-Object { $_.Name }); done = @($state.Done | ForEach-Object { $_.Name }); active = if ($state.Claim) { $state.Claim.waveFile } else { $null } })
        }
        'status' {
            $state = Assert-QueueIntegrity
            $first = @($state.Waiting | Where-Object { (Get-ManifestStatus $_.FullName) -ne 'active' } | Select-Object -First 1)
            Write-Result ([pscustomobject]@{ action = 'status'; waitingCount = $state.Waiting.Count; doneCount = $state.Done.Count; next = if ($first) { $first[0].Name } else { $null }; claim = $state.Claim })
        }
        'claim' {
            $state = Assert-QueueIntegrity
            if ($state.Claim) {
                if ($ClaimToken -and $state.Claim.token -eq $ClaimToken -and $state.Claim.owner -eq $Owner) {
                    Write-Result ([pscustomobject]@{ action = 'claim'; result = 'RESUMED'; claim = $state.Claim })
                    break
                }
                throw '[BLOCKED] A wave is already claimed. Supply its token to resume or release it explicitly.'
            }
            $candidate = @($state.Waiting | Select-Object -First 1)
            if (-not $candidate) { throw '[BLOCKED] No waiting wave remains.' }
            $info = Get-WaveInfo $candidate[0]
            Assert-Predecessors $info.Number $state.Done
            if ($info.Number -eq 9 -and (-not $AuthorizeLive -or [string]::IsNullOrWhiteSpace($AuthorizationNote))) {
                throw '[BLOCKED] Wave 09 requires -AuthorizeLive and a non-empty -AuthorizationNote.'
            }
            $token = [guid]::NewGuid().ToString('N')
            Set-ManifestStatus $candidate[0].FullName 'active'
            $claim = New-Claim $info $token
            Write-Utf8 $claimPath ($claim | ConvertTo-Json -Depth 4)
            Write-Result ([pscustomobject]@{ action = 'claim'; result = 'CLAIMED'; claim = $claim })
        }
        'verify' {
            $state = Assert-QueueIntegrity
            $manifest = Assert-Claim $state.Claim
            $packets = @(Verify-Wave $state.Claim $manifest $state.Done)
            Write-Result ([pscustomobject]@{ action = 'verify'; result = 'PASS'; waveId = $state.Claim.waveId; packets = @($packets.Id) })
        }
        'complete' {
            if ([string]::IsNullOrWhiteSpace($CompletionNote)) { throw '[BLOCKED] -CompletionNote is required for archive evidence.' }
            $state = Assert-QueueIntegrity
            $manifest = Assert-Claim $state.Claim
            $packets = @(Verify-Wave $state.Claim $manifest $state.Done)
            $previousPreference = $ErrorActionPreference
            $ErrorActionPreference = 'Continue'
            try {
                $diffCheck = @(& git -C $repoRoot diff --check 2>&1)
                $diffExitCode = $LASTEXITCODE
                $gitStatusRaw = @(& git -C $repoRoot status --short 2>&1)
                $statusExitCode = $LASTEXITCODE
            } finally {
                $ErrorActionPreference = $previousPreference
            }
            if ($diffExitCode -ne 0) { throw "[BLOCKED] git diff --check failed: $($diffCheck -join ' ')" }
            if ($statusExitCode -ne 0) { throw "[BLOCKED] git status --short failed: $($gitStatusRaw -join ' ')" }
            $gitStatus = @($gitStatusRaw | Where-Object { [string]$_ -match '^[ MADRCU?!]{2} ' })
            $text = [IO.File]::ReadAllText($manifest, [Text.Encoding]::UTF8)
            if ($text -notmatch '(?m)^## Completion Notes\s*$') { throw '[INVALID] Manifest has no Completion Notes section.' }
            $text = [regex]::Replace($text, '(?m)^Status:\s*.+$', 'Status: done')
            $closeout = "- Queue closeout: $CompletionNote`r`n- Archived at: $((Get-Date).ToString('o'))`r`n- Claim token: $ClaimToken`r`n- Packet verdicts: $($packets.Id -join ', ')`r`n- Git status entries observed: $($gitStatus.Count)"
            $text = [regex]::Replace($text, '(?m)^## Completion Notes\s*$', "## Completion Notes`r`n`r`n$closeout", 1)
            Write-Utf8 $manifest $text
            $destination = Join-Path $doneRoot $state.Claim.waveFile
            if (Test-Path -LiteralPath $destination) { throw '[INVALID] Archive destination already exists.' }
            Move-Item -LiteralPath $manifest -Destination $destination
            Remove-Item -LiteralPath $claimPath -Force
            [void](Assert-QueueIntegrity)
            Write-Result ([pscustomobject]@{ action = 'complete'; result = 'ARCHIVED'; waveId = $state.Claim.waveId; destination = $destination; gitStatusEntries = $gitStatus.Count })
        }
        'release' {
            $state = Assert-QueueIntegrity
            if (-not $state.Claim) { throw '[BLOCKED] No claim exists to release.' }
            if (-not $Force -and ([string]::IsNullOrWhiteSpace($ClaimToken) -or $ClaimToken -ne $state.Claim.token)) { throw '[BLOCKED] Claim token is required to release the active wave.' }
            $manifest = Join-Path $waitingRoot $state.Claim.waveFile
            $template = Join-Path $TemplateRoot $state.Claim.waveFile
            $originalStatus = Get-ManifestStatus $template
            Set-ManifestStatus $manifest $originalStatus
            Remove-Item -LiteralPath $claimPath -Force
            Write-Result ([pscustomobject]@{ action = 'release'; result = 'RELEASED'; waveId = $state.Claim.waveId })
        }
    }
} catch {
    [Console]::Error.WriteLine($_.Exception.Message)
    if ($_.Exception.Message -like '[[]BUSY[]]*') { exit 2 }
    if ($_.Exception.Message -like '[[]BLOCKED[]]*') { exit 3 }
    exit 1
} finally {
    if ($lock) { $lock.Dispose() }
}
