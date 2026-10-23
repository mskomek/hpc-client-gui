param(
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version = '1.5.9',
    [string]$OutputDirectory = 'dist/installer',
    [switch]$AcceptanceIdentity,
    [switch]$AcceptanceMachineIdentity
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root

& (Join-Path $PSScriptRoot 'check_release_consistency.ps1') -Version $Version
if (-not $?) { throw 'Release consistency check failed.' }

$requiredPaths = @(
    'dist/hpc-client-gui/hpc-client-gui.exe',
    'dist/hpc-client-cli/hpc-client-cli.exe',
    'templates'
)
foreach ($relativePath in $requiredPaths) {
    if (-not (Test-Path -LiteralPath (Join-Path $root $relativePath))) {
        throw "Installer input is missing: $relativePath. Build the Windows onedir artifacts first."
    }
}

$compiler = (Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue).Source
if (-not $compiler) {
    $programFilesX86 = [Environment]::GetEnvironmentVariable('ProgramFiles(x86)')
    $candidates = @(
        (Join-Path $env:LOCALAPPDATA 'Programs/Inno Setup 6/ISCC.exe'),
        (Join-Path $env:ProgramFiles 'Inno Setup 6/ISCC.exe'),
        (Join-Path $programFilesX86 'Inno Setup 6/ISCC.exe')
    )
    $compiler = $candidates | Where-Object { Test-Path -LiteralPath $_ -PathType Leaf } | Select-Object -First 1
}
if (-not $compiler) {
    throw 'Inno Setup 6 compiler (ISCC.exe) was not found.'
}

$iss = Join-Path $root 'build/windows/hpc-client-gui.iss'
$outputPath = [IO.Path]::GetFullPath((Join-Path $root $OutputDirectory))
New-Item -ItemType Directory -Path $outputPath -Force | Out-Null
$identity = 'HPC Client GUI'
$suffix = ''
$compilerArguments = @("/DAppVersion=$Version")
if ($AcceptanceIdentity -and $AcceptanceMachineIdentity) {
    throw 'Choose only one acceptance installer identity.'
}
if ($AcceptanceMachineIdentity) {
    $identity = 'HPC Client GUI Machine Acceptance'
    $suffix = '-machine-acceptance'
    $compilerArguments += '/DAcceptanceMachineIdentity'
} elseif ($AcceptanceIdentity) {
    $identity = 'HPC Client GUI Acceptance'
    $suffix = '-acceptance'
    $compilerArguments += '/DAcceptanceIdentity'
}
$outputName = "hpc-client-gui-setup-$Version-x64$suffix"
$compilerArguments += @("/O$outputPath", "/F$outputName", $iss)
& $compiler @compilerArguments
if ($LASTEXITCODE -ne 0) {
    throw "Inno Setup compilation failed (exit=$LASTEXITCODE)."
}

$installer = Join-Path $outputPath "$outputName.exe"
if (-not (Test-Path -LiteralPath $installer -PathType Leaf)) {
    throw "Inno Setup did not produce the expected installer: $installer"
}
$hash = (Get-FileHash -LiteralPath $installer -Algorithm SHA256).Hash.ToLowerInvariant()
Write-Output ([pscustomobject]@{
    Version = $Version
    Identity = $identity
    Installer = $installer
    Sha256 = $hash
    Signature = 'unsigned test artifact'
})
