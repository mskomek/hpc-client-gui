param(
    [string]$Version = "dev",
    [string]$ReleaseRoot = "dist/releases"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

python scripts/generate_third_party_versions.py --version $Version
if ($LASTEXITCODE -ne 0) { throw "Third-party version manifest generation failed." }
python scripts/generate_sbom.py --version $Version
if ($LASTEXITCODE -ne 0) { throw "SBOM generation failed." }
python scripts/generate_qt_lgpl_sources.py
if ($LASTEXITCODE -ne 0) { throw "Qt LGPL source manifest generation failed." }

& (Join-Path $PSScriptRoot 'check_release_ci_workflow.ps1')
if (-not $?) { throw 'Release CI workflow gate failed.' }

& (Join-Path $PSScriptRoot "check_release_consistency.ps1") -Version $Version -ReleaseRoot $ReleaseRoot
if (-not $?) { throw "Release consistency check failed." }

function Get-Sha256Hex([string]$Path) {
    # Avoids depending on the Get-FileHash cmdlet, whose module can fail to
    # autoload under some Windows PowerShell 5.1 environments.
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    try {
        $stream = [System.IO.File]::OpenRead($Path)
        try {
            $bytes = $sha256.ComputeHash($stream)
        } finally {
            $stream.Dispose()
        }
    } finally {
        $sha256.Dispose()
    }
    return ([BitConverter]::ToString($bytes) -replace '-', '').ToLowerInvariant()
}

$spec = "build/windows/hpc-client-gui.spec"
Write-Host "Building with PyInstaller spec: $spec"
pyinstaller -y --clean $spec
if ($LASTEXITCODE -ne 0) {
    Write-Warning "Clean build failed, retrying without --clean"
    pyinstaller -y $spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller build failed."
    }
}

$cliSpec = "build/windows/hpc-client-cli.spec"
Write-Host "Building console CLI with PyInstaller spec: $cliSpec"
pyinstaller -y --clean $cliSpec
if ($LASTEXITCODE -ne 0) { throw "CLI PyInstaller build failed." }

$distDir = Join-Path $Root "dist/hpc-client-gui"
if (-not (Test-Path $distDir)) {
    throw "Expected ONEDIR output not found: $distDir"
}

$builtExe = Join-Path $distDir "hpc-client-gui.exe"
if (-not (Test-Path $builtExe)) {
    throw "Expected built EXE not found: $builtExe"
}
$cliDistDir = Join-Path $Root "dist/hpc-client-cli"
$builtCliExe = Join-Path $cliDistDir "hpc-client-cli.exe"
if (-not (Test-Path -LiteralPath $builtCliExe -PathType Leaf)) {
    throw "Expected built CLI EXE not found: $builtCliExe"
}

$changelogSrc = Join-Path $Root "src/hpc_gui/docs/CHANGELOG.md"
if (-not (Test-Path $changelogSrc)) {
    throw "Expected changelog source not found: $changelogSrc"
}

function Get-ChangelogSection {
    param(
        [string]$Path,
        [string]$Version
    )

    $lines = Get-Content -Path $Path
    $escapedVersion = [regex]::Escape($Version)
    $start = -1

    for ($i = 0; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match "^##\s+v$escapedVersion\s*$") {
            $start = $i
            break
        }
    }

    if ($start -lt 0) {
        throw "Changelog section not found for v$Version in $Path"
    }

    $end = $lines.Count
    for ($i = $start + 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i] -match '^##\s+') {
            $end = $i
            break
        }
    }

    while ($end -gt $start -and [string]::IsNullOrWhiteSpace($lines[$end - 1])) {
        $end--
    }

    return ($lines[$start..($end - 1)] -join [Environment]::NewLine)
}

$releaseChangelogContent = Get-ChangelogSection -Path $changelogSrc -Version $Version

$releaseBase = Join-Path $Root $ReleaseRoot
$releaseIgnoreProbe = Join-Path $releaseBase '.release-ignore-probe'
git check-ignore -q -- $releaseIgnoreProbe
if ($LASTEXITCODE -ne 0) { throw 'Release output directory must be ignored by Git.' }
$versionDir = Join-Path $releaseBase "v$Version"
if (Test-Path $versionDir) {
    Remove-Item $versionDir -Recurse -Force
}
New-Item -ItemType Directory -Path $versionDir -Force | Out-Null

Copy-Item -Path (Join-Path $distDir "*") -Destination $versionDir -Recurse -Force
Copy-Item -LiteralPath $builtCliExe -Destination (Join-Path $versionDir "hpc-client-cli.exe") -Force
if (Test-Path (Join-Path $Root "templates")) {
    Copy-Item -Path (Join-Path $Root "templates") -Destination $versionDir -Recurse -Force
}

$helpSourceDir = Join-Path $Root "src/hpc_gui/docs"
$helpDestDir = Join-Path $versionDir "help"
New-Item -ItemType Directory -Path $helpDestDir -Force | Out-Null
$requiredHelpFiles = @("HELP_tr.md", "HELP_en.md", "CLI_GUIDE_tr.md", "CLI_GUIDE_en.md")
foreach ($fileName in $requiredHelpFiles) {
    $helpSourcePath = Join-Path $helpSourceDir $fileName
    if (-not (Test-Path -LiteralPath $helpSourcePath -PathType Leaf)) {
        throw "Release packaging: required help file missing from source: $helpSourcePath"
    }
    Copy-Item -Path $helpSourcePath -Destination (Join-Path $helpDestDir $fileName) -Force
}

$licenseFiles = @("LICENSE", "COMMERCIAL_LICENSE.md", "THIRD_PARTY_NOTICES.md", "QT_LGPL_SOURCE_OFFER.md", "THIRD_PARTY_VERSIONS.txt", "SBOM.cdx.json", "QT_LGPL_SOURCES.json")
foreach ($fileName in $licenseFiles) {
    $licenseSourcePath = Join-Path $Root $fileName
    if (-not (Test-Path -LiteralPath $licenseSourcePath -PathType Leaf)) {
        throw "Release packaging: required license file missing from source: $licenseSourcePath"
    }
    Copy-Item -Path $licenseSourcePath -Destination (Join-Path $versionDir $fileName) -Force
}

$thirdPartyLicensesSource = Join-Path $Root "third_party_licenses"
if (-not (Test-Path -LiteralPath $thirdPartyLicensesSource -PathType Container)) {
    throw "Release packaging: third_party_licenses directory missing from source: $thirdPartyLicensesSource"
}
Copy-Item -Path $thirdPartyLicensesSource -Destination (Join-Path $versionDir "third_party_licenses") -Recurse -Force

$exePath = Join-Path $versionDir "hpc-client-gui.exe"
if (-not (Test-Path $exePath)) {
    throw "Expected packaged exe not found: $exePath"
}
$cliExePath = Join-Path $versionDir "hpc-client-cli.exe"

Write-Host "Running release smoke tests against the packaged release..."
& (Join-Path $PSScriptRoot "release_smoke.ps1") -ExePath $exePath
if (-not $?) {
    throw "Release smoke tests failed."
}
& (Join-Path $PSScriptRoot "release_smoke.ps1") -ExePath $cliExePath -CliOnly
if (-not $?) { throw "CLI release smoke tests failed." }

Write-Host "Local transfer gate: Turkish-filename round trip and sftp-smoke/1 artifact placement"
$env:PYTHONPATH = "src"
python scripts/local_transfer_gate.py --version $Version --release-root $ReleaseRoot
if ($LASTEXITCODE -ne 0) {
    throw "Local transfer gate failed."
}


$releaseChangelogPath = Join-Path $versionDir "CHANGELOG.md"
Set-Content -Path $releaseChangelogPath -Value $releaseChangelogContent -Encoding utf8

$releaseZipName = "hpc-client-gui_windows_onedir.zip"
$releaseZipPath = Join-Path $versionDir $releaseZipName
if (Test-Path $releaseZipPath) { Remove-Item $releaseZipPath -Force }

Compress-Archive -Path (Join-Path $versionDir "*") -DestinationPath $releaseZipPath -Force

$releaseShaPath = "$releaseZipPath.sha256"
$hashHex = Get-Sha256Hex $releaseZipPath
"$hashHex  $releaseZipName" | Set-Content -Path $releaseShaPath -Encoding ascii

# v1.1.12 expects the former asset and executable names. Publish one migration
# package so its updater can install this renamed build; subsequent updates use
# the canonical HPC Client GUI asset names above.
$legacyZipName = "hpc-client-gui_windows_onedir.zip"
$legacyZipPath = Join-Path $versionDir $legacyZipName
$legacyStageDir = Join-Path $releaseBase ".legacy-v$Version"
if (Test-Path $legacyStageDir) {
    Remove-Item $legacyStageDir -Recurse -Force
}
New-Item -ItemType Directory -Path $legacyStageDir -Force | Out-Null
Get-ChildItem -Path $versionDir | Where-Object { $_.Name -notlike "*.zip*" } |
    Copy-Item -Destination $legacyStageDir -Recurse -Force
Copy-Item -LiteralPath $exePath -Destination (Join-Path $legacyStageDir "hpc-client-gui.exe") -Force
Compress-Archive -Path (Join-Path $legacyStageDir "*") -DestinationPath $legacyZipPath -Force
$legacyShaPath = "$legacyZipPath.sha256"
$legacyHashHex = Get-Sha256Hex $legacyZipPath
"$legacyHashHex  $legacyZipName" | Set-Content -Path $legacyShaPath -Encoding ascii
Remove-Item $legacyStageDir -Recurse -Force

# onedir releases are distributed as archives; keep executables inside them.
Remove-Item -LiteralPath $exePath, $cliExePath -Force

Write-Host "Release artifacts:"
Write-Host " - $releaseChangelogPath"
Write-Host " - $releaseZipPath"
Write-Host " - $releaseShaPath"
Write-Host " - $legacyZipPath (v1.1.12 migration)"
Write-Host " - $legacyShaPath"
