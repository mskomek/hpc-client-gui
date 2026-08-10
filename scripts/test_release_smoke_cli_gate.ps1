param()

$ErrorActionPreference = "Stop"

$releaseSmoke = Join-Path $PSScriptRoot "release_smoke.ps1"

function Get-PwshPath {
    param()
    $candidates = [System.Collections.Generic.List[string]]::new()
    if ($PSVersionTable.PSEdition -eq "Core") {
        $candidates.Add((Join-Path $PSHOME "pwsh.exe"))
    }
    $resolved = Get-Command pwsh -ErrorAction SilentlyContinue
    if ($resolved) {
        $candidates.Add($resolved.Source)
    }
    $candidates.Add((Join-Path $env:ProgramFiles "PowerShell\7\pwsh.exe"))
    $candidates.Add((Join-Path ${env:ProgramFiles(x86)} "PowerShell\7\pwsh.exe"))
    foreach ($candidate in $candidates) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return $candidate
        }
    }
    throw "Could not locate pwsh.exe; the packaged EXE CLI gate requires ProcessStartInfo.ArgumentList, which Windows PowerShell 5.1 does not provide."
}

$pwsh = Get-PwshPath

$tempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("release_smoke_cli_gate_" + [System.Guid]::NewGuid().ToString("N"))
$tempCreated = $false
try {
    New-Item -ItemType Directory -Path $tempDir | Out-Null
    $tempCreated = $true

    $tokens = $null
    $parseErrors = $null
    [void][System.Management.Automation.Language.Parser]::ParseFile($releaseSmoke, [ref]$tokens, [ref]$parseErrors)
    if ($parseErrors -and $parseErrors.Count -gt 0) {
        Write-Host "FAIL: $releaseSmoke has parse errors:"
        foreach ($parseError in $parseErrors) {
            Write-Host ("  " + $parseError.Message)
        }
        exit 1
    }
    Write-Host "PASS: $releaseSmoke parses without errors"

    $okCmdText = @'
@echo off
if "%1"=="--format" (echo {"commands":[{"path":"hpc-client-gui"},{"path":"version"}]}) else echo ARGS: %*
echo STDERR-LINE 1>&2
exit /b 0
'@
    $okExe = Join-Path $tempDir "fake_exe_ok.cmd"
    Set-Content -LiteralPath $okExe -Value $okCmdText -Encoding Ascii

    $failCmdText = @'
@echo off
if "%1"=="--format" (echo {"commands":[{"path":"hpc-client-gui"},{"path":"version"}]}) else echo ARGS: %*
echo STDERR-LINE 1>&2
if "%1"=="version" exit /b 7
exit /b 0
'@
    $failExe = Join-Path $tempDir "fake_exe_fail.cmd"
    Set-Content -LiteralPath $failExe -Value $failCmdText -Encoding Ascii

    $helpDir = Join-Path $tempDir "help"
    New-Item -ItemType Directory -Path $helpDir | Out-Null
    foreach ($helpFile in @("HELP_tr.md", "HELP_en.md", "CLI_GUIDE_tr.md", "CLI_GUIDE_en.md")) {
        Set-Content -LiteralPath (Join-Path $helpDir $helpFile) -Value "version" -Encoding UTF8
    }

    $commonArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", $releaseSmoke)

    function Invoke-SmokeCli {
        param(
            [Parameter(Mandatory = $true)]
            [string]$Exe,
            [Parameter(Mandatory = $true)]
            [string]$ErrFile
        )
        $saved = $ErrorActionPreference
        $ErrorActionPreference = "Continue"
        try {
            $stdoutLines = & $pwsh @commonArgs -ExePath $Exe -CliOnly 2> $ErrFile
            $code = $LASTEXITCODE
        }
        finally {
            $ErrorActionPreference = $saved
        }
        $combined = (($stdoutLines | Out-String) + [System.Environment]::NewLine +
            [string](Get-Content -LiteralPath $ErrFile -Raw -ErrorAction SilentlyContinue))
        return @{ ExitCode = $code; Output = $combined }
    }

    $okErrFile = Join-Path $tempDir "child_ok_stderr.txt"
    $okResult = Invoke-SmokeCli -Exe $okExe -ErrFile $okErrFile
    if ($okResult.ExitCode -ne 0) {
        Write-Host "FAIL: ok stand-in gate invocation exited with code $($okResult.ExitCode)"
        Write-Host $okResult.Output
        exit 1
    }
    foreach ($needle in @("--help", "version", "doctor environment", "STDERR-LINE", "Release smoke: PASS")) {
        if ($okResult.Output.IndexOf($needle, [System.StringComparison]::OrdinalIgnoreCase) -lt 0) {
            Write-Host "FAIL: ok stand-in output is missing '$needle'"
            Write-Host $okResult.Output
            exit 1
        }
    }
    Write-Host "PASS: ok stand-in exits 0 and echoes all three invocation argument sets (stdout and stderr)"

    $failErrFile = Join-Path $tempDir "child_fail_stderr.txt"
    $failResult = Invoke-SmokeCli -Exe $failExe -ErrFile $failErrFile
    if ($failResult.ExitCode -eq 0) {
        Write-Host "FAIL: failing stand-in unexpectedly exited 0"
        Write-Host $failResult.Output
        exit 1
    }
    if ($failResult.Output.IndexOf("Release smoke: PASS", [System.StringComparison]::Ordinal) -ge 0) {
        Write-Host "FAIL: 'Release smoke: PASS' banner appeared despite a failing invocation"
        Write-Host $failResult.Output
        exit 1
    }
    foreach ($needle in @("version", "ARGS: version", "STDERR-LINE")) {
        if ($failResult.Output.IndexOf($needle, [System.StringComparison]::Ordinal) -lt 0) {
            Write-Host "FAIL: failing invocation output is missing '$needle'"
            Write-Host $failResult.Output
            exit 1
        }
    }
    Write-Host "PASS: failing stand-in exits non-zero, reaches no PASS banner, and preserves the failing invocation's stdout and stderr"

    Write-Host "PASS"
    exit 0
}
finally {
    if ($tempCreated -and (Test-Path -LiteralPath $tempDir)) {
        Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
}
