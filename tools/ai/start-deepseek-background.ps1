[CmdletBinding()]
param(
    [ValidateSet('analyze', 'implement', 'review', 'smoke-test', 'dry-run')]
    [string]$Mode,
    [string]$TaskFile,
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Wave,
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Card,
    [string]$WorktreePath,
    [ValidateRange(0, 120)]
    [int]$TimeoutMinutes = 0,
    [string[]]$ContextFiles,
    [switch]$InternalRun,
    [string]$SpecFile
)

$ErrorActionPreference = 'Stop'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path

function Write-Utf8([string]$Path, [string]$Text) {
    $parent = Split-Path -Parent $Path
    if (-not (Test-Path -LiteralPath $parent)) { New-Item -ItemType Directory -Path $parent -Force | Out-Null }
    [IO.File]::WriteAllText($Path, $Text, $utf8NoBom)
}

if ($InternalRun) {
    if (-not $SpecFile -or -not (Test-Path -LiteralPath $SpecFile)) { throw 'Internal run requires an existing -SpecFile.' }
    $spec = Get-Content -Raw -LiteralPath $SpecFile | ConvertFrom-Json
    $exitCode = 1
    try {
        & powershell -NoProfile -File ([string]$spec.worker) @($spec.workerArguments) *> ([string]$spec.logFile)
        $exitCode = $LASTEXITCODE
    } catch {
        Add-Content -LiteralPath ([string]$spec.logFile) -Value ($_ | Out-String)
    } finally {
        $signal = [ordered]@{
            status = 'completed'
            exitCode = $exitCode
            processId = $PID
            completedAt = (Get-Date).ToString('o')
            logFile = [string]$spec.logFile
        }
        $temporary = [string]$spec.signalFile + '.' + [guid]::NewGuid().ToString('N') + '.tmp'
        Write-Utf8 $temporary ($signal | ConvertTo-Json)
        Move-Item -LiteralPath $temporary -Destination ([string]$spec.signalFile) -Force
    }
    exit $exitCode
}

if (-not $Mode) { throw '-Mode is required.' }
$requiresTask = $Mode -in @('analyze', 'implement', 'review')
if ($requiresTask -and -not $TaskFile) { throw "$Mode requires -TaskFile." }
if ($requiresTask -and (-not $Wave -or -not $Card)) { throw "$Mode requires -Wave and -Card." }
if ($Mode -eq 'implement' -and -not $WorktreePath) { throw 'implement requires -WorktreePath.' }

$worker = Join-Path $PSScriptRoot 'deepseek-worker.ps1'
$taskPath = if ($TaskFile) { (Resolve-Path -LiteralPath $TaskFile).Path } else { $null }
$timeout = if ($TimeoutMinutes) { $TimeoutMinutes } else {
    switch ($Mode) { 'implement' { 30 } 'smoke-test' { 10 } 'dry-run' { 10 } default { 20 } }
}
$workerArguments = @('-Mode', $Mode, '-TimeoutMinutes', [string]$timeout)
if ($taskPath) { $workerArguments += @('-TaskFile', $taskPath) }
if ($Wave) { $workerArguments += @('-Wave', $Wave) }
if ($Card) { $workerArguments += @('-Card', $Card) }
if ($WorktreePath) { $workerArguments += @('-WorktreePath', (Resolve-Path -LiteralPath $WorktreePath).Path) }
if ($ContextFiles) { $workerArguments += '-ContextFiles'; $workerArguments += $ContextFiles }

$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$label = (@($Wave, $Card, $Mode) | Where-Object { $_ }) -join '-'
$runRoot = Join-Path $repoRoot ".agent-runs\background\$stamp-$label"
New-Item -ItemType Directory -Path $runRoot -Force | Out-Null
$logFile = Join-Path $runRoot 'run.log'
$signalFile = Join-Path $runRoot 'completed.json'
$specPath = Join-Path $runRoot 'launch.json'
Write-Utf8 $logFile ''
Write-Utf8 $specPath ([ordered]@{
    worker = $worker
    workerArguments = $workerArguments
    logFile = $logFile
    signalFile = $signalFile
} | ConvertTo-Json -Depth 4)

$self = $MyInvocation.MyCommand.Path
$runner = Start-Process powershell -ArgumentList @(
    '-NoProfile', '-File', "`"$self`"", '-InternalRun', '-SpecFile', "`"$specPath`""
) -WindowStyle Hidden -PassThru
Start-Process powershell -ArgumentList @(
    '-NoProfile', '-File', "`"$(Join-Path $PSScriptRoot 'tail-and-close.ps1')`"",
    '-LogFile', "`"$logFile`"", '-MatchCommandLine', "`"$specPath`""
) -WindowStyle Minimized | Out-Null

[pscustomobject]@{
    processId = $runner.Id
    logFile = $logFile
    signalFile = $signalFile
    firstCheckDueAt = (Get-Date).AddMinutes(5).ToString('o')
} | ConvertTo-Json
