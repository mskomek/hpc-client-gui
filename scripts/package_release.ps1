param(
    [string]$Version = "dev",
    [string]$ReleaseRoot = "dist/releases"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$distDir = Join-Path $Root "dist/hpc-client-gui"
if (-not (Test-Path $distDir)) {
    throw "Expected ONEDIR output not found: $distDir"
}

$changelogSrc = Join-Path $Root "src/truba_gui/docs/CHANGELOG.md"
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

    return ($lines[$start..($end - 1)] -join [Environment]::NewLine)
}

$releaseChangelogContent = Get-ChangelogSection -Path $changelogSrc -Version $Version

$releaseBase = Join-Path $Root $ReleaseRoot
$versionDir = Join-Path $releaseBase "v$Version"
if (Test-Path $versionDir) {
    Remove-Item $versionDir -Recurse -Force
}
New-Item -ItemType Directory -Path $versionDir -Force | Out-Null

Copy-Item -Path (Join-Path $distDir "*") -Destination $versionDir -Recurse -Force
if (Test-Path (Join-Path $Root "templates")) {
    Copy-Item -Path (Join-Path $Root "templates") -Destination $versionDir -Recurse -Force
}

$helpSourceDir = Join-Path $Root "src/truba_gui/docs"
$helpDestDir = Join-Path $versionDir "help"
New-Item -ItemType Directory -Path $helpDestDir -Force | Out-Null
$requiredHelpFiles = @("HELP_tr.md", "HELP_en.md", "CLI_GUIDE_tr.md", "CLI_GUIDE_en.md")
foreach ($fileName in $requiredHelpFiles) {
    $sourcePath = Join-Path $helpSourceDir $fileName
    if (-not (Test-Path -LiteralPath $sourcePath -PathType Leaf)) {
        throw "Release packaging: required help file missing from source: $sourcePath"
    }
    Copy-Item -Path $sourcePath -Destination (Join-Path $helpDestDir $fileName) -Force
}

$exePath = Join-Path $versionDir "hpc-client-gui.exe"
if (-not (Test-Path $exePath)) {
    throw "Expected packaged exe not found: $exePath"
}

$releaseExeName = "hpc-client-gui.exe"

$changelogOut = Join-Path $versionDir "CHANGELOG.md"
Set-Content -Path $changelogOut -Value $releaseChangelogContent -Encoding utf8

$zipName = "hpc-client-gui_windows_onedir.zip"
$zipPath = Join-Path $versionDir $zipName
if (Test-Path $zipPath) { Remove-Item $zipPath -Force }
Compress-Archive -Path (Join-Path $versionDir "*") -DestinationPath $zipPath -Force

$shaPath = "$zipPath.sha256"
$hash = Get-FileHash $zipPath -Algorithm SHA256
"$($hash.Hash)  $zipName" | Set-Content -Path $shaPath -Encoding ascii

Write-Host "Release artifacts:"
Write-Host " - $changelogOut"
Write-Host " - $(Join-Path $versionDir $releaseExeName)"
Write-Host " - $zipPath"
Write-Host " - $shaPath"
Write-Host " - $helpDestDir"
