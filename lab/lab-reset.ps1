. (Join-Path $PSScriptRoot 'lab-common.ps1')
$null = Require-Admin
$controller = Get-Node login-control01
foreach ($node in $Config.nodes) {
  $vm = Get-VM -Name $node.name -ErrorAction SilentlyContinue
  if (-not $vm) { throw "VM does not exist: $($node.name)" }
  if ($vm.State -ne 'Running') { Start-VM -Name $node.name | Out-Null }
}
foreach ($node in $Config.nodes) {
  $ready = $false
  for ($i = 0; $i -lt 60; $i++) { if (Test-NetConnection $node.ip -Port 22 -InformationLevel Quiet) { $ready = $true; break }; Start-Sleep 2 }
  if (-not $ready) { throw "SSH did not recover: $($node.name)" }
}
$controllerServices = 'sudo systemctl start ssh munge mariadb nfs-server slurmdbd slurmctld'
Invoke-LabSsh $controller.ip $controllerServices | Out-Null
foreach ($node in @($Config.nodes | Where-Object role -eq 'compute')) { Invoke-LabSsh $node.ip 'sudo systemctl start ssh munge slurmd' | Out-Null }
Invoke-LabSsh $controller.ip "squeue -h -o '%i' | xargs -r scancel; sudo rm -f /srv/hpc/project/local-real-proof; sudo scontrol update NodeName=compute01,compute02 State=RESUME" | Out-Null
Remove-Item (Join-Path $EvidenceRoot 'LOCAL_REAL_TEST.json') -Force -ErrorAction SilentlyContinue
& (Join-Path $PSScriptRoot 'lab-status.ps1')
