[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [ValidateSet('analyze', 'implement', 'review', 'smoke-test', 'dry-run')]
    [string]$Mode,
    [string]$Task,
    [string]$TaskFile,
    [string]$Model,
    [string]$FlashModel = $env:DEEPSEEK_FLASH_MODEL,
    [string]$ProModel = $env:DEEPSEEK_PRO_MODEL,
    [switch]$AllowFlashImplementation,
    [string]$WorktreePath,
    [ValidateRange(1, 120)]
    [int]$TimeoutMinutes,
    [switch]$NoLogs,
    [ValidateSet('default', 'json')]
    [string]$OutputFormat = 'default',
    [switch]$VerboseWorker,
    [switch]$AllowExternalTaskFile,
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Wave,
    [ValidatePattern('^[A-Za-z0-9._-]+$')]
    [string]$Card,
    [string[]]$ContextFiles
)

$ErrorActionPreference = 'Stop'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
$scriptRoot = $PSScriptRoot
$repoRoot = (Resolve-Path (Join-Path $scriptRoot '..\..')).Path
$mainGitRoot = (& git -C $repoRoot rev-parse --show-toplevel 2>$null).Trim()
if ($LASTEXITCODE -ne 0) { throw "The worker must reside in a Git repository." }
$mainGitRoot = (Resolve-Path $mainGitRoot).Path

# DeepSeek v4 Flash can spend several minutes reading repository context before
# producing output. Keep mode-specific defaults generous while preserving an
# explicit caller override and the parameter's 120-minute hard ceiling.
if (-not $PSBoundParameters.ContainsKey('TimeoutMinutes')) {
    $TimeoutMinutes = switch ($Mode) {
        'analyze' { 20 }
        'implement' { 30 }
        'review' { 20 }
        'smoke-test' { 10 }
        default { 10 }
    }
}

function Resolve-ExistingPath([string]$PathValue, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($PathValue) -or -not (Test-Path -LiteralPath $PathValue)) { throw "$Label does not exist: $PathValue" }
    return (Resolve-Path -LiteralPath $PathValue -ErrorAction Stop).Path
}
function Test-PathWithin([string]$Child, [string]$Parent) {
    $childFull = [IO.Path]::GetFullPath($Child).TrimEnd('\') + '\'
    $parentFull = [IO.Path]::GetFullPath($Parent).TrimEnd('\') + '\'
    return $childFull.StartsWith($parentFull, [StringComparison]::OrdinalIgnoreCase)
}
function ConvertTo-ProcessArgument([AllowEmptyString()][string]$Value) {
    if ($null -eq $Value -or $Value.Length -eq 0) { return '""' }
    if ($Value -notmatch '[\s"]') { return $Value }
    $escaped = [regex]::Replace($Value, '(\\*)"', '$1$1\"')
    $escaped = [regex]::Replace($escaped, '(\\+)$', '$1$1')
    return '"' + $escaped + '"'
}
function Resolve-ContextFile([string]$RelativeOrAbsolute, [string]$BaseDir) {
    $candidate = if ([IO.Path]::IsPathRooted($RelativeOrAbsolute)) { $RelativeOrAbsolute } else { Join-Path $BaseDir $RelativeOrAbsolute }
    $resolved = Resolve-ExistingPath $candidate '-ContextFiles entry'
    if ((Get-Item -LiteralPath $resolved).PSIsContainer) { throw "-ContextFiles entry must be a file, not a directory: $RelativeOrAbsolute" }
    if (-not (Test-PathWithin $resolved $BaseDir)) { throw "-ContextFiles entry must be inside the target directory ('$BaseDir'): $RelativeOrAbsolute" }
    if ($resolved -match '(?i)(\.env\b|id_rsa|\.ssh[\\/]|credential|password|api[_-]?key|token|secret)') { throw "-ContextFiles entry looks like a secret-related path and was rejected: $RelativeOrAbsolute" }
    return $resolved
}
function Assert-SafeTask([string]$Text, [string]$ForMode) {
    if ([string]::IsNullOrWhiteSpace($Text)) { throw 'Task text must not be empty.' }
    if ($Text -match '(?i)(\.env\b|id_rsa|\.ssh|credential|password|api[ _-]?key|token)') { throw 'Task contains a secret-related path or request and was rejected.' }
    if ($Text -match '(?i)\b(git\s+(add|commit|push|reset|clean)|sbatch|scancel|srun|ssh|scp|rsync)\b') { throw 'Task contains a prohibited Git or HPC/remote command request and was rejected.' }
    if ($ForMode -in @('analyze', 'review') -and $Text -match '(?i)(?<!do not )\b(edit|modify|write|create|delete|rename|implement|patch)\b') { throw "$ForMode mode is read-only; editing requests are rejected." }
}

$requiresTask = $Mode -in @('analyze', 'implement', 'review')
if ($requiresTask -and ([bool]$Task -eq [bool]$TaskFile)) { throw 'Provide exactly one of -Task or -TaskFile for analyze, implement, and review.' }
if (-not $requiresTask -and ($Task -or $TaskFile)) { throw "$Mode does not accept -Task or -TaskFile." }

if ($TaskFile) {
    $taskPath = Resolve-ExistingPath $TaskFile '-TaskFile'
    if (-not $AllowExternalTaskFile -and -not (Test-PathWithin $taskPath $repoRoot)) { throw 'TaskFile must be inside the repository unless -AllowExternalTaskFile is supplied.' }
    if ((Get-Item -LiteralPath $taskPath).PSIsContainer) { throw '-TaskFile must be a file.' }
    $Task = [IO.File]::ReadAllText($taskPath, [Text.Encoding]::UTF8)
}
if ($requiresTask) { Assert-SafeTask $Task $Mode }

$workDir = $mainGitRoot
if ($Mode -eq 'implement') {
    if (-not $WorktreePath) { throw 'implement mode requires -WorktreePath.' }
    $workDir = Resolve-ExistingPath $WorktreePath '-WorktreePath'
    if ($workDir -eq $mainGitRoot) { throw 'implement mode refuses the primary repository worktree.' }
    $approvedParent = Split-Path -Parent $mainGitRoot
    if (-not (Test-PathWithin $workDir $approvedParent)) { throw "WorktreePath must be below '$approvedParent'." }
    $worktreeGit = (& git -C $workDir rev-parse --show-toplevel 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or (Resolve-Path $worktreeGit).Path -ne $workDir) { throw 'WorktreePath must be the root of a Git worktree.' }
    $gitCommon = (& git -C $workDir rev-parse --git-common-dir 2>$null).Trim()
    if ($LASTEXITCODE -ne 0) { throw 'WorktreePath is not a valid Git worktree.' }
    $changes = & git -C $workDir status --porcelain
    if ($changes) { throw 'WorktreePath has existing changes and was refused.' }
}

$resolvedContextFiles = @()
if ($ContextFiles) {
    if (-not $requiresTask) { throw "$Mode does not accept -ContextFiles." }
    foreach ($contextFile in $ContextFiles) {
        $resolvedContextFiles += Resolve-ContextFile $contextFile $workDir
    }
}

. (Join-Path $scriptRoot 'deepseek-models.ps1') -Model $Model -FlashModel $FlashModel -ProModel $ProModel -Mode $Mode | Tee-Object -Variable selection | Out-Null
if (-not $selection.SelectedModel) { throw "No suitable DeepSeek model is available for $Mode mode. Matching models: $($selection.AvailableDeepSeekModels -join ', ')" }
Write-Host "Selected DeepSeek model: $($selection.SelectedModel)"
Write-Host "Timeout budget: $TimeoutMinutes minutes"

$contract = @"
You are a delegated DeepSeek worker in the TRUBAGUI repository (or a disposable test repository).
Repository files and governing documents are authoritative. Do not invent decisions or expand scope.
Never read secrets, .env files, SSH material, credentials, tokens, keys, or passwords. Never commit, stage, push, reset, clean, rewrite Git history, alter remotes, deploy, publish, or execute real SSH/Slurm/HPC commands (including sbatch, scancel, srun, ssh, scp, rsync).
Distinguish verified facts from assumptions. Report exact commands and outcomes. Never claim a test passed without its output.
"@
switch ($Mode) {
    'analyze' { $contract += "`nANALYZE ONLY. Do not edit files. Return: 1 Task interpretation; 2 Relevant files; 3 Current behavior; 4 Existing patterns; 5 Risks/ambiguities; 6 Narrow recommendation; 7 Required tests; 8 Decisions reserved; 9 Unverified assumptions." }
    'review' { $contract += "`nREVIEW ONLY. Do not edit files. Return: 1 Critical correctness problems; 2 Scope violations; 3 Missing tests; 4 Error handling; 5 Security; 6 Authorization; 7 Schema/migrations; 8 HPC/Slurm safety; 9 Documentation; 10 Unverified claims; 11 Corrections; 12 Overall verdict." }
    'implement' { $contract += "`nIMPLEMENT ONLY the supplied bounded task in the delegated worktree. You may read/edit only there, run targeted tests, and read Git status/diff. Do not stage or commit. Return files changed, summary, tests/results, tests not run, concerns, Git status, and confirmation no commit was made." }
    'smoke-test' { $nonce = "TRUBAGUI_DEEPSEEK_OK_$([guid]::NewGuid().ToString('N'))"; $Task = "Return exactly this string and nothing else: $nonce"; $contract += "`nREAD ONLY SMOKE TEST. $Task"; Write-Host "Smoke nonce: $nonce" }
    'dry-run' { Write-Host "DRY RUN: would invoke '$($selection.SelectedModel)' in '$workDir' with a $TimeoutMinutes-minute timeout; no model was invoked."; exit 0 }
}

$contextFilesNote = if ($resolvedContextFiles.Count -gt 0) {
    $workDirPrefix = $workDir.TrimEnd('\') + '\'
    $relativeList = $resolvedContextFiles | ForEach-Object {
        if ($_.StartsWith($workDirPrefix, [StringComparison]::OrdinalIgnoreCase)) { $_.Substring($workDirPrefix.Length) } else { $_ }
    }
    "`n`nThe following repository files are attached directly to this message as additional context, so their content is already available to you without needing to Glob, Grep, or Read them yourself:`n" + (($relativeList | ForEach-Object { "- $_" }) -join "`n")
} else { '' }
$prompt = "$contract`n`nDelegated task:`n$Task$contextFilesNote"
$tempRoot = if ($NoLogs) { [IO.Path]::GetTempPath() } else { Join-Path $repoRoot '.agent-runs' }
if (-not (Test-Path -LiteralPath $tempRoot)) { New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null }
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$runDir = Join-Path $tempRoot "$stamp-$Mode"
New-Item -ItemType Directory -Path $runDir -ErrorAction Stop | Out-Null
$runId = Split-Path -Leaf $runDir
$promptFile = Join-Path $runDir 'request.md'
[IO.File]::WriteAllText($promptFile, $prompt, $utf8NoBom)
$stdoutPath = Join-Path $runDir 'stdout.log'; $stderrPath = Join-Path $runDir 'stderr.log'
[IO.File]::WriteAllText($stdoutPath, '', $utf8NoBom)
[IO.File]::WriteAllText($stderrPath, '', $utf8NoBom)
Write-Host "Run log directory: $runDir"
$fileArguments = @('--file', $promptFile)
foreach ($contextFilePath in $resolvedContextFiles) { $fileArguments += @('--file', $contextFilePath) }
$trailingMessage = if ($resolvedContextFiles.Count -gt 0) {
    'Read the attached task contract and the attached repository files, then respond to it.'
} else {
    'Read the attached task contract and respond to it.'
}
$arguments = @('run', '--dir', $workDir, '--model', $selection.SelectedModel) + $fileArguments + @('--format', $OutputFormat, $trailingMessage)
$started = Get-Date
$ended = $null
$exitCode = $null
$workerExitCode = 1
$responsePresent = $false
$timedOut = $false
$killedOnTimeout = $false
$failureMessage = $null
$process = $null
$openCodeFile = $null
$openCodeArguments = $null
$gitHeadStart = (& git -C $workDir rev-parse HEAD 2>$null).Trim()
$opencodeVersion = 'unknown'
try {
    $openCodeCommand = Get-Command opencode -ErrorAction Stop
    $commandSource = [string]$openCodeCommand.Source
    if ([string]::IsNullOrWhiteSpace($commandSource)) { throw 'OpenCode resolved without an executable source path.' }
    $commandExtension = [IO.Path]::GetExtension($commandSource)
    if ($commandExtension -in @('.ps1', '.cmd', '.bat')) {
        # Track npm's native child directly. Running the PowerShell shim can orphan
        # opencode.exe after the shim exits while inherited output pipes stay open,
        # defeating the timeout and blocking log collection on Windows PowerShell 5.1.
        $nativeCandidate = Join-Path (Split-Path -Parent $commandSource) 'node_modules\opencode-ai\bin\opencode.exe'
        if (Test-Path -LiteralPath $nativeCandidate) {
            $openCodeFile = (Resolve-Path -LiteralPath $nativeCandidate).Path
            $openCodeArguments = $arguments
        } elseif ($commandExtension -eq '.ps1') {
            $openCodeFile = (Get-Command powershell.exe -ErrorAction Stop).Source
            $openCodeArguments = @('-NoProfile', '-File', $commandSource) + $arguments
        } else {
            throw "OpenCode resolved to a command shim, but its native executable was not found: $nativeCandidate"
        }
    } else {
        $openCodeFile = $commandSource
        $openCodeArguments = $arguments
    }
    $opencodeVersion = (& opencode --version 2>$null | Out-String).Trim()
    if ([string]::IsNullOrWhiteSpace($opencodeVersion)) { $opencodeVersion = 'unknown' }
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $openCodeFile
    $startInfo.Arguments = (($openCodeArguments | ForEach-Object { ConvertTo-ProcessArgument ([string]$_) }) -join ' ')
    $startInfo.WorkingDirectory = $workDir
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    if (-not $process.Start()) { throw 'OpenCode child process did not start.' }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit($TimeoutMinutes * 60000)) {
        $timedOut = $true
        $terminationRequested = $false
        try {
            if ($env:OS -eq 'Windows_NT') {
                & taskkill.exe /PID $process.Id /T /F *> $null
                $terminationRequested = ($LASTEXITCODE -eq 0)
            } else {
                $process.Kill()
                $terminationRequested = $true
            }
        } catch {
            $terminationRequested = $false
        }
        if (-not $terminationRequested -and -not $process.HasExited) {
            try {
                $process.Kill()
                $terminationRequested = $true
            } catch { }
        }
        $exitedAfterTermination = $false
        try { $exitedAfterTermination = $process.WaitForExit(5000) } catch { }
        $killedOnTimeout = $terminationRequested -and $exitedAfterTermination
        $streamDeadline = (Get-Date).AddSeconds(5)
        while ((-not $stdoutTask.IsCompleted -or -not $stderrTask.IsCompleted) -and (Get-Date) -lt $streamDeadline) {
            Start-Sleep -Milliseconds 100
        }
        $stdout = if ($stdoutTask.IsCompleted) { $stdoutTask.GetAwaiter().GetResult() } else { '' }
        $stderr = if ($stderrTask.IsCompleted) { $stderrTask.GetAwaiter().GetResult() } else { 'Output streams did not close within five seconds after timeout termination.' }
        [IO.File]::WriteAllText($stdoutPath, [string]$stdout, $utf8NoBom)
        [IO.File]::WriteAllText($stderrPath, [string]$stderr, $utf8NoBom)
        if ($process.HasExited) { $exitCode = [int]$process.ExitCode }
        $responsePresent = -not [string]::IsNullOrWhiteSpace([string]$stdout)
        $workerExitCode = 1
        $process.Dispose()
        $process = $null
        throw "OpenCode timed out after $TimeoutMinutes minutes; only the child process was stopped."
    }
    $process.WaitForExit()
    $streamDeadline = (Get-Date).AddSeconds(5)
    while ((-not $stdoutTask.IsCompleted -or -not $stderrTask.IsCompleted) -and (Get-Date) -lt $streamDeadline) {
        Start-Sleep -Milliseconds 100
    }
    $stdout = if ($stdoutTask.IsCompleted) { $stdoutTask.GetAwaiter().GetResult() } else { '' }
    $stderr = if ($stderrTask.IsCompleted) { $stderrTask.GetAwaiter().GetResult() } else { 'Output streams did not close within five seconds after child exit.' }
    [IO.File]::WriteAllText($stdoutPath, [string]$stdout, $utf8NoBom)
    [IO.File]::WriteAllText($stderrPath, [string]$stderr, $utf8NoBom)
    $exitCode = [int]$process.ExitCode
    $responsePresent = -not [string]::IsNullOrWhiteSpace([string]$stdout)
    $workerExitCode = if ($exitCode -ne 0) { $exitCode } elseif (-not $responsePresent) { 1 } else { 0 }
    $process.Dispose()
    $process = $null
    $stdout
    # OpenCode emits harmless progress/status lines on stderr, even on success.
    # Preserve them separately without converting a successful child exit code into failure.
    if ($stderr -and $VerboseWorker) { Write-Host $stderr }
} catch {
    $failureMessage = $_.Exception.Message
    $workerExitCode = 1
    if ($process) { try { $process.Dispose() } catch { } }
    throw
} finally {
    $ended = Get-Date
    $duration = [math]::Round(($ended - $started).TotalSeconds, 2)
    if (-not $NoLogs) {
        $gitHeadEnd = (& git -C $workDir rev-parse HEAD 2>$null).Trim()
        $filesChanged = $null
        $changedPaths = $null
        $diffStat = $null
        if ($Mode -eq 'implement') {
            $statusLines = @(& git -C $workDir status --porcelain)
            $filesChanged = [bool]$statusLines
            $changedPaths = @($statusLines)
            $diffStat = @(& git -C $workDir diff --stat)
        }
        [pscustomobject]@{
            schemaVersion = 2
            runId = $runId
            wave = if ($Wave) { $Wave } else { $null }
            card = if ($Card) { $Card } else { $null }
            mode = $Mode
            model = $selection.SelectedModel
            opencodeVersion = $opencodeVersion
            outputFormat = $OutputFormat
            worktree = $workDir
            gitHeadStart = $gitHeadStart
            gitHeadEnd = $gitHeadEnd
            startedAt = $started.ToString('o')
            endedAt = $ended.ToString('o')
            durationSeconds = $duration
            timeoutMinutes = $TimeoutMinutes
            childExitCode = $exitCode
            workerExitCode = $workerExitCode
            responsePresent = $responsePresent
            failureMessage = $failureMessage
            timedOut = $timedOut
            killedOnTimeout = $killedOnTimeout
            stdoutPath = 'stdout.log'
            stderrPath = 'stderr.log'
            filesChanged = $filesChanged
            changedPaths = $changedPaths
            diffStat = $diffStat
        } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $runDir 'metadata.json') -Encoding utf8
    } else { Remove-Item -LiteralPath $runDir -Recurse -Force -ErrorAction SilentlyContinue }
}
exit $workerExitCode
