[CmdletBinding()]
param([switch]$KeepTemporaryFiles)

$ErrorActionPreference = 'Stop'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$manager = Join-Path $PSScriptRoot 'wave-queue.ps1'
$templates = Join-Path $PSScriptRoot 'wave-templates'
$schema = Join-Path $PSScriptRoot 'packet-verdict.schema.json'
$results = [System.Collections.Generic.List[object]]::new()
$temporaryParent = [IO.Path]::GetFullPath([IO.Path]::GetTempPath()).TrimEnd('\') + '\'
$fixtureRoot = Join-Path ([IO.Path]::GetTempPath()) ('trubagui-wave-queue-' + [guid]::NewGuid().ToString('N'))
$fixtureRoot = [IO.Path]::GetFullPath($fixtureRoot)
if (-not $fixtureRoot.StartsWith($temporaryParent, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe temporary fixture path.' }
$queueRoot = Join-Path $fixtureRoot 'waves'
$evidenceRoot = Join-Path $fixtureRoot 'evidence'
$repoStatusBefore = @(& git -C $root status --short) -join "`n"

function Record([string]$Name, [scriptblock]$Action) {
    try {
        & $Action
        $script:results.Add([pscustomobject]@{ Test = $Name; Result = 'PASS'; Detail = '' })
    } catch {
        $script:results.Add([pscustomobject]@{ Test = $Name; Result = 'FAIL'; Detail = $_.Exception.Message })
    }
}

function Invoke-Queue([string[]]$Arguments, [int]$ExpectedExit = 0) {
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        $output = & powershell -NoProfile -File $manager @Arguments 2>&1 | Out-String
        $exitCode = $LASTEXITCODE
    } finally {
        $ErrorActionPreference = $previousPreference
    }
    if ($exitCode -ne $ExpectedExit) { throw "Expected queue exit $ExpectedExit, observed $exitCode. Output: $output" }
    return $output
}

function Write-Utf8([string]$Path, [string]$Text) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    [IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

function Set-FixtureStatus([string]$Path, [string]$Status) {
    $text = [IO.File]::ReadAllText($Path, [Text.Encoding]::UTF8)
    $text = [regex]::Replace($text, '(?m)^Status:\s*.+$', "Status: $Status")
    Write-Utf8 $Path $text
}

function Write-Verdict(
    [string]$Wave,
    [string]$Packet,
    [string]$Size,
    [int]$MaxFiles,
    [int]$MaxLines,
    [int]$ObservedFiles,
    [int]$ObservedLines,
    [bool]$WithinLimit = $true
) {
    $paths = @()
    for ($index = 1; $index -le $ObservedFiles; $index++) { $paths += "file-$index.txt" }
    $data = [ordered]@{
        schemaVersion = 1
        wave = $Wave
        packet = $Packet
        verdict = 'PASS'
        verifiedBy = 'Codex test fixture'
        verifiedAt = (Get-Date).ToUniversalTime().ToString('o')
        relatedRunIds = @("run-$Packet")
        allowedPaths = @($paths)
        observedPaths = @($paths)
        diffStat = @("$ObservedFiles files, $ObservedLines lines")
        testsRun = @()
        evidenceFiles = @()
        reviewFindings = @()
        resolutions = @()
        remainingUncertainty = @()
        capacity = [ordered]@{
            size = $Size
            maxFiles = $MaxFiles
            maxChangedLines = $MaxLines
            observedFiles = $ObservedFiles
            observedChangedLines = $ObservedLines
            withinLimit = $WithinLimit
        }
        nextPermittedPacket = $null
    }
    $path = Join-Path (Join-Path (Join-Path $evidenceRoot $Wave) $Packet) 'verdict.json'
    Write-Utf8 $path ($data | ConvertTo-Json -Depth 8)
}

function Base-Arguments([string]$Action) {
    return @('-Action', $Action, '-QueueRoot', $queueRoot, '-EvidenceRoot', $evidenceRoot, '-TemplateRoot', $templates, '-SchemaPath', $schema, '-Owner', 'offline-test')
}

try {
    New-Item -ItemType Directory -Path $fixtureRoot -Force | Out-Null

    Record 'Manager parses in Windows PowerShell' {
        $tokens = $null; $errors = $null
        [void][Management.Automation.Language.Parser]::ParseFile($manager, [ref]$tokens, [ref]$errors)
        if ($errors.Count) { throw ($errors | Out-String) }
    }

    Record 'Recover recreates all ignored manifests from canonical templates' {
        $result = Invoke-Queue (Base-Arguments 'recover') | ConvertFrom-Json
        if ($result.result -ne 'PASS' -or @($result.restored).Count -ne 9) { throw 'recover did not restore all nine waves' }
        if (@(Get-ChildItem (Join-Path $queueRoot 'waiting') -Filter 'wave_*.md').Count -ne 9) { throw 'waiting queue count mismatch' }
    }

    Record 'Initial audit enforces a complete ordered queue' {
        $result = Invoke-Queue (Base-Arguments 'audit') | ConvertFrom-Json
        if ($result.result -ne 'PASS' -or @($result.done).Count -ne 0) { throw 'initial audit mismatch' }
    }

    Record 'Status reports the first waiting wave and no active claim' {
        $result = Invoke-Queue (Base-Arguments 'status') | ConvertFrom-Json
        if ($result.next -notlike 'wave_01_*' -or $result.waitingCount -ne 9 -or $result.doneCount -ne 0 -or $result.claim) { throw 'initial status contract mismatch' }
    }

    $claimToken = $null
    Record 'Claim selects only Wave 01 and returns a token' {
        $result = Invoke-Queue (Base-Arguments 'claim') | ConvertFrom-Json
        if ($result.result -ne 'CLAIMED' -or $result.claim.waveId -ne 'WAVE_01') { throw 'Wave 01 was not selected' }
        $script:claimToken = $result.claim.token
        if ([string]::IsNullOrWhiteSpace($script:claimToken)) { throw 'claim token is missing' }
    }

    Record 'Second owner cannot claim the active wave' {
        $args = Base-Arguments 'claim'; $args[-1] = 'other-owner'
        [void](Invoke-Queue $args 3)
    }

    Record 'Token and owner resume the existing claim' {
        $args = Base-Arguments 'claim'; $args += @('-ClaimToken', $script:claimToken)
        $result = Invoke-Queue $args | ConvertFrom-Json
        if ($result.result -ne 'RESUMED') { throw 'claim did not resume' }
    }

    Record 'Verify blocks when packet verdicts are missing' {
        $args = Base-Arguments 'verify'; $args += @('-ClaimToken', $script:claimToken)
        [void](Invoke-Queue $args 3)
    }

    Record 'Schema-invalid verdict fails with an actionable manager diagnostic' {
        Write-Verdict 'WAVE_01' 'DS-01A' 'Audit' 0 0 0 0
        $path = Join-Path $evidenceRoot 'WAVE_01\DS-01A\verdict.json'
        $data = Get-Content -Raw $path | ConvertFrom-Json
        $data.PSObject.Properties.Remove('capacity')
        Write-Utf8 $path ($data | ConvertTo-Json -Depth 8)
        $args = Base-Arguments 'verify'; $args += @('-ClaimToken', $script:claimToken)
        $output = Invoke-Queue $args 1
        if ($output -notmatch '\[INVALID\] Verdict does not match schema' -or $output -match 'Traceback') { throw 'schema diagnostic is not actionable or leaked a traceback' }
    }

    Write-Verdict 'WAVE_01' 'DS-01A' 'Audit' 0 0 0 0
    Write-Verdict 'WAVE_01' 'DS-01B' 'Small' 3 200 2 120
    Write-Verdict 'WAVE_01' 'DS-01C' 'Small' 3 200 2 80

    Record 'Verify accepts schema-valid PASS verdicts within capacity' {
        $args = Base-Arguments 'verify'; $args += @('-ClaimToken', $script:claimToken)
        $result = Invoke-Queue $args | ConvertFrom-Json
        if ($result.result -ne 'PASS' -or @($result.packets).Count -ne 3) { throw 'valid Wave 01 evidence was rejected' }
    }

    Record 'Changed-line capacity overrun blocks completion' {
        Write-Verdict 'WAVE_01' 'DS-01C' 'Small' 3 200 2 201 $false
        $args = Base-Arguments 'verify'; $args += @('-ClaimToken', $script:claimToken)
        [void](Invoke-Queue $args 3)
        Write-Verdict 'WAVE_01' 'DS-01C' 'Small' 3 200 2 80
    }

    Record 'Wrong token cannot archive a wave' {
        $args = Base-Arguments 'complete'; $args += @('-ClaimToken', 'wrong-token', '-CompletionNote', 'offline closeout')
        [void](Invoke-Queue $args 3)
    }

    Record 'Guarded completion archives only the verified Wave 01' {
        $args = Base-Arguments 'complete'; $args += @('-ClaimToken', $script:claimToken, '-CompletionNote', 'offline closeout')
        $result = Invoke-Queue $args | ConvertFrom-Json
        if ($result.result -ne 'ARCHIVED' -or -not (Test-Path (Join-Path $queueRoot 'done\wave_01_cli_contracts_and_current_state_audit.md'))) { throw 'Wave 01 was not archived' }
        if (Test-Path (Join-Path $queueRoot '.state\claim.json')) { throw 'claim survived archive' }
    }

    $wave2Token = $null
    Record 'Next claim advances to Wave 02 only after Wave 01 is done' {
        $result = Invoke-Queue (Base-Arguments 'claim') | ConvertFrom-Json
        if ($result.claim.waveId -ne 'WAVE_02') { throw 'queue did not advance to Wave 02' }
        $script:wave2Token = $result.claim.token
    }

    Record 'Release requires ownership and restores the waiting status' {
        $wrong = Base-Arguments 'release'; $wrong += @('-ClaimToken', 'wrong-token')
        [void](Invoke-Queue $wrong 3)
        $right = Base-Arguments 'release'; $right += @('-ClaimToken', $script:wave2Token)
        $result = Invoke-Queue $right | ConvertFrom-Json
        if ($result.result -ne 'RELEASED') { throw 'owned claim was not released' }
        if ((Get-Content -Raw (Join-Path $queueRoot 'waiting\wave_02_profile_lifecycle_and_session_security.md')) -notmatch '(?m)^Status: waiting$') { throw 'waiting status was not restored' }
    }

    Record 'Audit detects a manually moved unfinished wave' {
        $wave2 = Join-Path $queueRoot 'waiting\wave_02_profile_lifecycle_and_session_security.md'
        $badDone = Join-Path $queueRoot 'done\wave_02_profile_lifecycle_and_session_security.md'
        Move-Item -LiteralPath $wave2 -Destination $badDone
        [void](Invoke-Queue (Base-Arguments 'audit') 1)
        Move-Item -LiteralPath $badDone -Destination $wave2
    }

    Record 'Audit detects a done-status wave archived out of order' {
        $wave3 = Join-Path $queueRoot 'waiting\wave_03_file_contracts_and_conflict_policy.md'
        $badDone = Join-Path $queueRoot 'done\wave_03_file_contracts_and_conflict_policy.md'
        Move-Item -LiteralPath $wave3 -Destination $badDone
        Set-FixtureStatus $badDone 'done'
        [void](Invoke-Queue (Base-Arguments 'audit') 1)
        Move-Item -LiteralPath $badDone -Destination $wave3
        Set-FixtureStatus $wave3 'waiting'
    }

    Record 'Recover restores one deleted waiting wave byte-for-byte' {
        $wave3 = Join-Path $queueRoot 'waiting\wave_03_file_contracts_and_conflict_policy.md'
        Remove-Item -LiteralPath $wave3
        $result = Invoke-Queue (Base-Arguments 'recover') | ConvertFrom-Json
        if (@($result.restored) -notcontains 'wave_03_file_contracts_and_conflict_policy.md') { throw 'Wave 03 was not restored' }
        $expected = [IO.File]::ReadAllBytes((Join-Path $templates 'wave_03_file_contracts_and_conflict_policy.md'))
        $actual = [IO.File]::ReadAllBytes($wave3)
        if ([Convert]::ToBase64String($expected) -ne [Convert]::ToBase64String($actual)) { throw 'recovered manifest differs from its template' }
    }

    Record 'Exclusive lock returns BUSY without queue mutation' {
        $lockPath = Join-Path $queueRoot '.state\queue.lock'
        $held = [IO.File]::Open($lockPath, [IO.FileMode]::OpenOrCreate, [IO.FileAccess]::ReadWrite, [IO.FileShare]::None)
        try { [void](Invoke-Queue (Base-Arguments 'status') 2) } finally { $held.Dispose() }
    }

    Record 'Wave 09 cannot be claimed without explicit authorization' {
        $authorizationFixture = Join-Path $fixtureRoot 'authorization-waves'
        New-Item -ItemType Directory -Path (Join-Path $authorizationFixture 'waiting'),(Join-Path $authorizationFixture 'done') -Force | Out-Null
        foreach ($template in Get-ChildItem $templates -Filter 'wave_*.md' | Sort-Object Name) {
            if ($template.Name -like 'wave_09_*') {
                Copy-Item $template.FullName (Join-Path $authorizationFixture 'waiting')
            } else {
                $destination = Join-Path (Join-Path $authorizationFixture 'done') $template.Name
                Copy-Item $template.FullName $destination
                Set-FixtureStatus $destination 'done'
            }
        }
        $base = @('-Action','claim','-QueueRoot',$authorizationFixture,'-EvidenceRoot',$evidenceRoot,'-TemplateRoot',$templates,'-SchemaPath',$schema,'-Owner','offline-test')
        [void](Invoke-Queue $base 3)
        $authorized = $base + @('-AuthorizeLive','-AuthorizationNote','explicit offline fixture authorization')
        $result = Invoke-Queue $authorized | ConvertFrom-Json
        if ($result.claim.waveId -ne 'WAVE_09' -or -not $result.claim.liveAuthorized) { throw 'authorized Wave 09 claim failed' }
        Write-Verdict 'WAVE_09' 'LIVE-09' 'Reserved' 0 0 0 0
        $verify = @('-Action','verify','-QueueRoot',$authorizationFixture,'-EvidenceRoot',$evidenceRoot,'-TemplateRoot',$templates,'-SchemaPath',$schema,'-Owner','offline-test','-ClaimToken',$result.claim.token)
        $verified = Invoke-Queue $verify | ConvertFrom-Json
        if ($verified.result -ne 'PASS') { throw 'Reserved LIVE-09 capacity evidence was rejected' }
    }

    Record 'SEC and LIVE reject Audit capacity classification' {
        $authorizationFixture = Join-Path $fixtureRoot 'authorization-waves'
        $claim = Get-Content -Raw (Join-Path $authorizationFixture '.state\claim.json') | ConvertFrom-Json
        Write-Verdict 'WAVE_09' 'LIVE-09' 'Audit' 0 0 0 0
        $verify = @('-Action','verify','-QueueRoot',$authorizationFixture,'-EvidenceRoot',$evidenceRoot,'-TemplateRoot',$templates,'-SchemaPath',$schema,'-Owner','offline-test','-ClaimToken',$claim.token)
        $output = Invoke-Queue $verify 1
        if ($output -notmatch 'capacity size does not match') { throw 'Audit mismatch did not produce the expected rejection' }
        Write-Verdict 'WAVE_09' 'LIVE-09' 'Reserved' 0 0 0 0
    }

    Record 'Reserved packet rejects any observed delivery capacity' {
        $authorizationFixture = Join-Path $fixtureRoot 'authorization-waves'
        $claim = Get-Content -Raw (Join-Path $authorizationFixture '.state\claim.json') | ConvertFrom-Json
        Write-Verdict 'WAVE_09' 'LIVE-09' 'Reserved' 0 0 1 1 $false
        $verify = @('-Action','verify','-QueueRoot',$authorizationFixture,'-EvidenceRoot',$evidenceRoot,'-TemplateRoot',$templates,'-SchemaPath',$schema,'-Owner','offline-test','-ClaimToken',$claim.token)
        [void](Invoke-Queue $verify 3)
        Write-Verdict 'WAVE_09' 'LIVE-09' 'Reserved' 0 0 0 0
    }

    Record 'Force release is explicit and restores queue state' {
        $result = Invoke-Queue (Base-Arguments 'claim') | ConvertFrom-Json
        $args = Base-Arguments 'release'; $args += '-Force'
        $released = Invoke-Queue $args | ConvertFrom-Json
        if ($released.result -ne 'RELEASED' -or $released.waveId -ne $result.claim.waveId) { throw 'force release failed' }
    }

    Record 'Queue tests leave the primary worktree status unchanged' {
        $after = @(& git -C $root status --short) -join "`n"
        if ($after -ne $repoStatusBefore) { throw 'primary worktree status changed during fixture tests' }
    }
} finally {
    $results | Format-Table -AutoSize
    if ($results.Result -contains 'FAIL') { $results | Where-Object Result -eq 'FAIL' | Format-List }
    if (-not $KeepTemporaryFiles -and (Test-Path -LiteralPath $fixtureRoot)) {
        $resolved = [IO.Path]::GetFullPath($fixtureRoot)
        if (-not $resolved.StartsWith($temporaryParent, [StringComparison]::OrdinalIgnoreCase)) { throw 'Refusing unsafe fixture cleanup.' }
        Remove-Item -LiteralPath $resolved -Recurse -Force
    } elseif ($KeepTemporaryFiles) {
        Write-Host "Temporary fixture retained: $fixtureRoot"
    }
}

if ($results.Result -contains 'FAIL') { exit 1 }
