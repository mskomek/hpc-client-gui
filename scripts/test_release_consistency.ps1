$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
& (Join-Path $PSScriptRoot "check_release_consistency.ps1") -Version "1.1.21"

Write-Output "release consistency tests passed"
