. (Join-Path $PSScriptRoot 'lab-common.ps1')
Require-Admin
foreach ($node in $Config.nodes) { if (Get-VM -Name $node.name -ErrorAction SilentlyContinue) { Stop-VM -Name $node.name -Force -TurnOff -ErrorAction SilentlyContinue } }
