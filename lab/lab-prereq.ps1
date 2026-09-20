. (Join-Path $PSScriptRoot 'lab-common.ps1')
Ensure-Dirs
$checks = [ordered]@{}
$checks.hyperv = [bool](Get-Command New-VM -ErrorAction SilentlyContinue)
$checks.ssh = [bool](Get-Command ssh -ErrorAction SilentlyContinue)
$checks.sftp = [bool](Get-Command sftp -ErrorAction SilentlyContinue)
$checks.ssh_keygen = [bool](Get-Command ssh-keygen -ErrorAction SilentlyContinue)
$checks.wsl = [bool](Get-Command wsl.exe -ErrorAction SilentlyContinue)
$checks.genisoimage = $false
$checks.qemu_img = $false
if ($checks.wsl) { wsl.exe bash -lc 'command -v genisoimage >/dev/null 2>&1'; $checks.genisoimage = $LASTEXITCODE -eq 0; wsl.exe bash -lc 'command -v qemu-img >/dev/null 2>&1'; $checks.qemu_img = $LASTEXITCODE -eq 0 }
$checks.admin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
$checks.ok = @($checks.GetEnumerator() | Where-Object { $_.Key -ne 'ok' -and -not $_.Value }).Count -eq 0
$report = [pscustomobject]@{ status = if ($checks.ok) {'PASS'} else {'FAIL'}; checks = $checks; generated_at = (Get-Date).ToUniversalTime().ToString('o') }
Write-Json $report (Join-Path $EvidenceRoot 'prereq.json'); $report | ConvertTo-Json -Depth 5
if (-not $checks.ok) { exit 2 }
