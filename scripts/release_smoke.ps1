param(
    [Parameter(Mandatory = $true)]
    [string]$ExePath
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$resolvedExe = (Resolve-Path $ExePath).Path
if (-not (Test-Path -LiteralPath $resolvedExe -PathType Leaf)) {
    throw "Release smoke test could not find EXE: $ExePath"
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

Write-Host "Release smoke: PASS"
