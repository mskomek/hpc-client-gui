param(
    [Parameter(Mandatory)]
    [ValidatePattern('^\d+\.\d+\.\d+$')]
    [string]$Version,
    [string]$ReleaseRoot = "dist/releases"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

function Read-Version([string]$Path) {
    $match = [regex]::Match((Get-Content -Raw -LiteralPath $Path), '(?m)^version\s*=\s*"([^"]+)"\s*$')
    if (-not $match.Success) { throw "Version declaration not found: $Path" }
    return $match.Groups[1].Value
}

$versions = @(
    (Read-Version (Join-Path $Root "pyproject.toml"))
    (Read-Version (Join-Path $Root "src/truba_gui/pyproject.toml"))
)
$init = Get-Content -Raw (Join-Path $Root "src/truba_gui/__init__.py")
$initMatch = [regex]::Match($init, '__version__\s*=\s*''([^'']+)''')
if (-not $initMatch.Success) { throw "__version__ declaration not found." }
$versions += $initMatch.Groups[1].Value

$cli = Get-Content -Raw (Join-Path $Root "src/truba_gui/cli/main.py")
$cliMatch = [regex]::Match($cli, 'CLI_VERSION\s*=\s*"([^"]+)"')
if (-not $cliMatch.Success) { throw "CLI_VERSION declaration not found." }
$versions += $cliMatch.Groups[1].Value

if (@($versions | Select-Object -Unique).Count -ne 1 -or $versions[0] -ne $Version) {
    throw "Release version mismatch: input $Version; discovered $($versions -join ', ')."
}

if ($env:GITHUB_REF -match '^refs/tags/v(.+)$' -and $Matches[1] -ne $Version) {
    throw "Release tag version $($Matches[1]) does not match input $Version."
}

$versionInfoPath = Join-Path $Root "build/windows/version_info.txt"
$versionInfo = Get-Content -Raw -LiteralPath $versionInfoPath
$expectedTuple = "($(($Version -split '\.') -join ', '), 0)"
foreach ($field in @("FileVersion", "ProductVersion")) {
    if (-not (Select-String -InputObject $versionInfo -Pattern "StringStruct\('$field',\s*'$([regex]::Escape($Version))'\)" -Quiet)) {
        throw "build/windows/version_info.txt $field does not match $Version."
    }
}
foreach ($field in @("filevers", "prodvers")) {
    if (-not (Select-String -InputObject $versionInfo -Pattern "$field=$([regex]::Escape($expectedTuple))" -Quiet)) {
        throw "build/windows/version_info.txt $field does not match expected tuple $expectedTuple."
    }
}

$changelog = Join-Path $Root "src/truba_gui/docs/CHANGELOG.md"
if (-not (Select-String -LiteralPath $changelog -Pattern "^##\s+v$([regex]::Escape($Version))\s*$" -Quiet)) {
    throw "Changelog section not found for v$Version."
}

$helpDir = Join-Path $Root "src/truba_gui/docs"
foreach ($name in @("HELP_tr.md", "HELP_en.md", "CLI_GUIDE_tr.md", "CLI_GUIDE_en.md")) {
    if (-not (Test-Path -LiteralPath (Join-Path $helpDir $name) -PathType Leaf)) {
        throw "Required help file missing: $name"
    }
}

$releaseDir = Join-Path (Join-Path $Root $ReleaseRoot) "v$Version"
Write-Host "Release consistency: $Version -> $releaseDir"
