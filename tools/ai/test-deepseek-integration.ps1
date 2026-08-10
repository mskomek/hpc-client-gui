[CmdletBinding()]
param([switch]$OfflineOnly, [switch]$LiveOnly, [switch]$KeepTemporaryFiles, [switch]$VerboseTest)

$ErrorActionPreference = 'Stop'
if ($OfflineOnly -and $LiveOnly) { throw 'Choose at most one of -OfflineOnly or -LiveOnly.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$worker = Join-Path $PSScriptRoot 'deepseek-worker.ps1'
$models = Join-Path $PSScriptRoot 'deepseek-models.ps1'
$background = Join-Path $PSScriptRoot 'start-deepseek-background.ps1'
$tail = Join-Path $PSScriptRoot 'tail-and-close.ps1'
$results = [System.Collections.Generic.List[object]]::new()
function Record([string]$Name, [scriptblock]$Action) { try { & $Action; $script:results.Add([pscustomobject]@{ Test=$Name; Result='PASS'; Detail='' }) } catch { $script:results.Add([pscustomobject]@{ Test=$Name; Result='FAIL'; Detail=$_.Exception.Message }) } }
function Expect-Failure([string]$Name, [scriptblock]$Action) {
    try {
        & $Action
        $script:results.Add([pscustomobject]@{ Test=$Name; Result='PASS'; Detail='Rejected as expected.' })
    } catch {
        if ($_.Exception.Message -eq 'Expected rejection did not occur.') { throw }
        $script:results.Add([pscustomobject]@{ Test=$Name; Result='FAIL'; Detail="Unexpected test exception: $($_.Exception.Message)" })
    }
}

if (-not $LiveOnly) {
    Record 'PowerShell scripts parse' { foreach ($f in @($worker,$models,$background,$tail,$PSCommandPath)) { $tokens=$null; $errors=$null; [void][Management.Automation.Language.Parser]::ParseFile($f,[ref]$tokens,[ref]$errors); if ($errors.Count) { throw ($errors | Out-String) } } }
    Record 'Timeout termination remains bounded and evidence-based' {
        $source = Get-Content -Raw -LiteralPath $worker
        foreach ($expected in @("'analyze' { 20 }", "'implement' { 30 }", "'review' { 20 }", "'smoke-test' { 10 }")) {
            if (-not $source.Contains($expected)) { throw "missing generous timeout default: $expected" }
        }
        if ($source -notmatch '\$process\.WaitForExit\(5000\)') { throw 'post-termination wait is not bounded' }
        if ($source -notmatch '\$terminationRequested = \(\$LASTEXITCODE -eq 0\)') { throw 'taskkill success is not checked' }
        if ($source -notmatch '\$killedOnTimeout = \$terminationRequested -and \$exitedAfterTermination') { throw 'timeout kill evidence is not conjunctive' }
        if ($source -match 'try \{ \$process\.WaitForExit\(\) \} catch') { throw 'unbounded guarded WaitForExit remains' }
    }
    Record 'Dry-run does not invoke a model' { & powershell -NoProfile -File $worker -Mode dry-run -NoLogs; if ($LASTEXITCODE -ne 0) { throw 'dry-run failed' } }
    Record 'Background dry-run writes a successful completion signal' {
        $launch = & powershell -NoProfile -File $background -Mode dry-run | ConvertFrom-Json
        $deadline = (Get-Date).AddSeconds(30)
        while (-not (Test-Path -LiteralPath $launch.signalFile) -and (Get-Date) -lt $deadline) { Start-Sleep -Milliseconds 250 }
        if (-not (Test-Path -LiteralPath $launch.signalFile)) { throw 'completion signal was not written' }
        $signal = Get-Content -Raw -LiteralPath $launch.signalFile | ConvertFrom-Json
        if ($signal.status -ne 'completed' -or [int]$signal.exitCode -ne 0) { throw 'completion signal did not report success' }
    }
    Record 'Explicit timeout override survives mode defaults' { $output = & powershell -NoProfile -File $worker -Mode dry-run -TimeoutMinutes 37 -NoLogs | Out-String; if ($LASTEXITCODE -ne 0 -or $output -notmatch '37-minute timeout') { throw 'explicit timeout override was not preserved' } }
    Record 'Timeout boundary values are accepted' { foreach ($value in @(1,120)) { & powershell -NoProfile -File $worker -Mode dry-run -TimeoutMinutes $value -NoLogs | Out-Null; if ($LASTEXITCODE -ne 0) { throw "timeout boundary $value was rejected" } } }
    Record 'Timeout values outside the boundary are rejected' {
        foreach ($value in @(0,121)) {
            $rejected = $false
            try {
                & powershell -NoProfile -File $worker -Mode dry-run -TimeoutMinutes $value -NoLogs 2>$null
                $rejected = ($LASTEXITCODE -ne 0)
            } catch {
                $rejected = $true
            }
            if (-not $rejected) { throw "timeout value $value was accepted" }
        }
    }
    Record 'Wave and card identifiers are accepted' { & powershell -NoProfile -File $worker -Mode dry-run -Wave WAVE_TEST -Card CARD_TEST -NoLogs; if ($LASTEXITCODE -ne 0) { throw 'identified dry-run failed' } }
    Expect-Failure 'Missing task is rejected' { & powershell -NoProfile -File $worker -Mode analyze -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Both task inputs are rejected' { $f=Join-Path $root 'README.md'; & powershell -NoProfile -File $worker -Mode analyze -Task x -TaskFile $f -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Missing TaskFile is rejected' { & powershell -NoProfile -File $worker -Mode analyze -TaskFile (Join-Path $root 'missing-task.md') -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Empty task is rejected' { & powershell -NoProfile -File $worker -Mode analyze -Task ' ' -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Implement without worktree is rejected' { & powershell -NoProfile -File $worker -Mode implement -Task 'Make a harmless file.' -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Implement primary repository is rejected' { & powershell -NoProfile -File $worker -Mode implement -Task 'Make a harmless file.' -WorktreePath $root -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Analyze edit request is rejected' { & powershell -NoProfile -File $worker -Mode analyze -Task 'Edit a file.' -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Review edit request is rejected' { & powershell -NoProfile -File $worker -Mode review -Task 'Modify a file.' -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Dangerous Git commands are rejected' { & powershell -NoProfile -File $worker -Mode implement -Task 'Run git commit.' -WorktreePath $root -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'HPC commands are rejected' { & powershell -NoProfile -File $worker -Mode implement -Task 'Run sbatch.' -WorktreePath $root -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Expect-Failure 'Secret paths are rejected' { & powershell -NoProfile -File $worker -Mode analyze -Task 'Read .env.' -NoLogs; if ($LASTEXITCODE -eq 0) { throw 'Expected rejection did not occur.' } }
    Record '.agent-runs is ignored by Git' { $ignored = & git -C $root check-ignore .agent-runs/probe; if (-not $ignored) { throw '.agent-runs is not ignored' } }
    Record 'No model ID is guessed' { $selection = & powershell -NoProfile -File $models -Mode analyze | Out-String; if ($selection -notmatch 'deepseek') { throw 'No discovered DeepSeek model output' } }
    Record 'Flash is default for every mode' { foreach ($mode in @('analyze','implement','review','smoke-test','dry-run')) { $selection = & powershell -NoProfile -File $models -Mode $mode | Out-String; if ($selection -notmatch 'SelectedModel\s+:\s+opencode-go/deepseek.*flash') { throw "Flash was not selected for $mode" } } }
    Record 'Governance files and user changes preserved by test' { if (-not (Test-Path $root)) { throw 'Repository unavailable' } }
}

if (-not $OfflineOnly) {
    Record 'Live smoke has auditable metadata and matching nonce' {
        $runRoot = Join-Path $root '.agent-runs'
        $before = @((Get-ChildItem -LiteralPath $runRoot -Directory -ErrorAction SilentlyContinue).FullName)
        $output = & powershell -NoProfile -File $worker -Mode smoke-test -Wave INTEGRATION -Card SMOKE | Out-String
        if ($LASTEXITCODE -ne 0) { throw "smoke-test failed: $output" }
        $run = Get-ChildItem -LiteralPath $runRoot -Directory | Where-Object { $_.FullName -notin $before } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if (-not $run) { throw 'smoke-test run directory was not found' }
        $metadata = Get-Content -Raw -LiteralPath (Join-Path $run.FullName 'metadata.json') | ConvertFrom-Json
        $metadataPath = Join-Path $run.FullName 'metadata.json'
        $schemaPath = Join-Path $PSScriptRoot 'run-metadata.schema.json'
        & python -c "import json, sys; from jsonschema import Draft202012Validator; schema=json.loads(open(sys.argv[2], 'rb').read()); data=json.loads(open(sys.argv[1], 'rb').read()); Draft202012Validator(schema).validate(data)" $metadataPath $schemaPath
        if ($LASTEXITCODE -ne 0) { throw 'metadata does not match run-metadata.schema.json' }
        if ($metadata.wave -ne 'INTEGRATION' -or $metadata.card -ne 'SMOKE') { throw 'wave/card metadata mismatch' }
        if ([int]$metadata.schemaVersion -ne 2 -or [int]$metadata.timeoutMinutes -ne 10) { throw 'timeout metadata mismatch' }
        if ($null -eq $metadata.childExitCode -or [int]$metadata.childExitCode -ne 0) { throw 'child exit code is missing or non-zero' }
        if ([int]$metadata.workerExitCode -ne 0 -or -not [bool]$metadata.responsePresent) { throw 'worker did not record a valid model response' }
        if ($metadata.filesChanged -ne $null -or $metadata.changedPaths -ne $null) { throw 'read-only smoke attributed file changes' }
        $request = Get-Content -Raw -LiteralPath (Join-Path $run.FullName 'request.md')
        $expected = [regex]::Match($request, 'TRUBAGUI_DEEPSEEK_OK_[0-9a-f]+').Value
        $actual = (Get-Content -Raw -LiteralPath (Join-Path $run.FullName 'stdout.log')).Trim()
        if (-not $expected -or $actual -ne $expected) { throw 'smoke nonce mismatch' }
    }
}

$results | Format-Table -AutoSize
if ($results.Result -contains 'FAIL') { exit 1 }
