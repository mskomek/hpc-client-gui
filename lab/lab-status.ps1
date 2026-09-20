. (Join-Path $PSScriptRoot 'lab-common.ps1')
Ensure-Dirs
$items = foreach ($node in $Config.nodes) {
  $probe = Invoke-LabSshCapture $node.ip "hostname; systemctl is-active ssh munge $(if ($node.role -eq 'controller') {'slurmctld slurmdbd mariadb nfs-server'} else {'slurmd'})"
  [pscustomobject]@{ name=$node.name; ip=$node.ip; role=$node.role; ssh=($probe.exit_code -eq 0); probe=$probe.output }
}
$status = [pscustomobject]@{ status=if (@($items | Where-Object {-not $_.ssh}).Count -eq 0) {'PASS'} else {'FAIL'}; topology=$items; generated_at=(Get-Date).ToUniversalTime().ToString('o') }
Write-Json $status (Join-Path $EvidenceRoot 'health.json'); $status | ConvertTo-Json -Depth 8
