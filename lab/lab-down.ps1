. (Join-Path $PSScriptRoot 'lab-common.ps1')
Require-Admin
foreach ($node in $Config.nodes) {
  $vm = Get-VM -Name $node.name -ErrorAction SilentlyContinue
  if (-not $vm -or $vm.State -eq 'Off') { continue }
  Stop-VM -Name $node.name -Force -ErrorAction SilentlyContinue
  for ($i=0; $i -lt 30; $i++) {
    if ((Get-VM -Name $node.name).State -eq 'Off') { break }
    Start-Sleep 1
  }
  if ((Get-VM -Name $node.name).State -ne 'Off') {
    Write-Warning "Graceful shutdown timed out for $($node.name); forcing power off."
    Stop-VM -Name $node.name -Force -TurnOff
  }
}