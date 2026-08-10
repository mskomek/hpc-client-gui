param()

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

if (-not (git rev-parse --verify HEAD^ 2>$null)) {
    throw "Release CI gate requires a parent commit."
}

git diff --quiet HEAD^ HEAD -- .github/workflows
if ($LASTEXITCODE -ne 0) {
    throw "Release commit changes .github/workflows. Commit CI changes separately before version/changelog."
}

Write-Host "Release CI workflow gate: PASS"