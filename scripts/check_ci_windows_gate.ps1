$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$ci = Get-Content (Join-Path $root ".github/workflows/ci.yml") -Raw
foreach ($required in @('windows-latest', 'python-version: "3.11"', 'Windows boundary tests', 'tests/test_safe_download.py')) { if ($ci -notmatch [regex]::Escape($required)) { throw "Missing Windows CI gate: $required" } }
if ($ci -match 'softprops/action-gh-release|release.ps1') { throw "CI must not publish releases" }
Write-Host "Windows CI workflow gate: PASS"