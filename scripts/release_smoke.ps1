param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath,
    [switch]$CliOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$resolvedExe = (Resolve-Path $ExePath).Path
if (-not (Test-Path -LiteralPath $resolvedExe -PathType Leaf)) {
    throw "Release smoke test could not find EXE: $ExePath"
}

function Invoke-ReleaseExeCli {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path,
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments
    )

    $psi = [System.Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $Path
    $psi.WorkingDirectory = Split-Path -Parent $Path
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $psi.Environment["QT_QPA_PLATFORM"] = "offscreen"
    # ProcessStartInfo.ArgumentList is unreliable under Windows PowerShell
    # 5.1's older .NET Framework (it can silently be $null rather than an
    # initialized collection, crashing on .Add()); build a single quoted
    # command-line string instead, which every PowerShell/.NET version supports.
    $psi.Arguments = ($Arguments | ForEach-Object {
        if ($_ -match '[\s"]') { '"' + ($_ -replace '"', '\"') + '"' } else { $_ }
    }) -join ' '

    $process = [System.Diagnostics.Process]::Start($psi)
    if (-not $process) {
        throw "Release smoke: packaged EXE CLI invocation '$($Arguments -join ' ')' failed to start (Process.Start returned `$null)."
    }
    $stdoutTask = $process.StandardOutput.ReadToEndAsync()
    $stderrTask = $process.StandardError.ReadToEndAsync()
    if (-not $process.WaitForExit(60000)) {
        $process.Kill()
        $process.WaitForExit(5000)
        throw "Release smoke: packaged EXE CLI invocation '$($Arguments -join ' ')' timed out after 60 seconds."
    }

    $stdout = $stdoutTask.GetAwaiter().GetResult()
    $stderr = $stderrTask.GetAwaiter().GetResult()

    Write-Host "Release smoke: packaged EXE CLI stdout:"
    Write-Host $stdout
    Write-Host "Release smoke: packaged EXE CLI stderr:"
    Write-Host $stderr

    if ($process.ExitCode -ne 0) {
        throw "Release smoke: packaged EXE CLI invocation '$($Arguments -join ' ')' failed with exit code $($process.ExitCode)."
    }
}

function Invoke-PackagedExeCliGate {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    Write-Host "Release smoke: packaged EXE --help"
    Invoke-ReleaseExeCli -Path $Path -Arguments @("--help")
    Write-Host "Release smoke: packaged EXE version"
    Invoke-ReleaseExeCli -Path $Path -Arguments @("version")
    Write-Host "Release smoke: packaged EXE doctor environment"
    Invoke-ReleaseExeCli -Path $Path -Arguments @("doctor", "environment")
}

if ($CliOnly) {
    Invoke-PackagedExeCliGate -Path $resolvedExe
    Write-Host "Release smoke: PASS"
    exit 0
}

Write-Host "Release smoke: source diagnostics"
$env:PYTHONPATH = "src"
python scripts/smoke_test.py
if ($LASTEXITCODE -ne 0) {
    throw "Source smoke test failed."
}

Write-Host "Release smoke: disposable FTP upload/download integrity test"
python scripts/ftp_transfer_stress.py --mode smoke --parallel 4 --timeout 120
if ($LASTEXITCODE -ne 0) {
    throw "FTP transfer smoke test failed."
}

Write-Host "Release smoke: packaged EXE startup"
$psi = [System.Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $resolvedExe
$psi.WorkingDirectory = Split-Path -Parent $resolvedExe
$psi.UseShellExecute = $false
$psi.Environment["QT_QPA_PLATFORM"] = "offscreen"
$process = [System.Diagnostics.Process]::Start($psi)
try {
    Start-Sleep -Seconds 8
    if ($process.HasExited) {
        throw "Packaged EXE exited during startup smoke test (exit code $($process.ExitCode))."
    }
}
finally {
    if (-not $process.HasExited) {
        $process.Kill()
        $process.WaitForExit(5000)
    }
}
# Give Windows a moment to fully release the just-killed EXE's file handle
# before relaunching the same file for the CLI gate below.
Start-Sleep -Milliseconds 750

Invoke-PackagedExeCliGate -Path $resolvedExe

Write-Host "Release smoke: PASS"
