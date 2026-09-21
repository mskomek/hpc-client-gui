. (Join-Path $PSScriptRoot 'lab-common.ps1')
Require-Admin
$controller = Get-ControllerNode
$computeNodes = @(Get-ComputeNodes)


foreach ($node in $Config.nodes) {
  $vm = Get-VM -Name $node.name -ErrorAction SilentlyContinue
  if (-not $vm) { throw "VM does not exist: $($node.name)" }
  if ($vm.State -ne 'Running') { Start-VM -Name $node.name | Out-Null }
}


foreach ($node in $Config.nodes) {
  $ready = $false
  for ($i = 0; $i -lt 30; $i++) {
    if (Test-NetConnection $node.ip -Port $Config.ssh.port -InformationLevel Quiet -WarningAction SilentlyContinue) { $ready = $true; break }
    Start-Sleep 2
  }
  if (-not $ready) {
    Restart-VM -Name $node.name -Force
    for ($i = 0; $i -lt 60; $i++) {
      if (Test-NetConnection $node.ip -Port $Config.ssh.port -InformationLevel Quiet -WarningAction SilentlyContinue) { $ready = $true; break }
      Start-Sleep 2
    }
  }
  if (-not $ready) { throw "SSH did not recover after VM restart: $($node.name)" }
}


$controllerResult = Invoke-LabSshCapture $controller.ip 'sudo systemctl restart munge mariadb nfs-server slurmdbd slurmctld ssh; systemctl is-active --quiet ssh munge mariadb nfs-server slurmdbd slurmctld'
if ($controllerResult.exit_code -ne 0) { throw "Controller service reset failed.`n$($controllerResult.output)`n$($controllerResult.stderr)" }


foreach ($node in $computeNodes) {
  $result = Invoke-LabSshCapture $node.ip 'sudo systemctl restart munge slurmd ssh; systemctl is-active --quiet ssh munge slurmd'
  if ($result.exit_code -ne 0) { throw "Compute service reset failed on $($node.name).`n$($result.output)`n$($result.stderr)" }
}


$computeNameWords = (@($computeNodes | ForEach-Object { $_.name }) -join ' ')
$cleanup = "squeue -h -u hpctest -o '%i' | xargs -r scancel; rm -rf /srv/hpc/home/hpctest/.local-real-job /srv/hpc/scratch/hpctest/sftp-upload.txt /srv/hpc/project/root-only; for n in $computeNameWords; do st=`$(sinfo -h -N -n `$n -o '%t' | head -n1); case `$st in down*|drain*|drng*|fail*|reboot*) sudo scontrol update NodeName=`$n State=RESUME ;; esac; done"
$cleanupResult = Invoke-LabSshCapture $controller.ip $cleanup
if ($cleanupResult.exit_code -ne 0) { throw "Cluster cleanup/resume failed.`n$($cleanupResult.output)`n$($cleanupResult.stderr)" }


Remove-Item (Join-Path $EvidenceRoot 'LOCAL_REAL_TEST.json') -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $EvidenceRoot 'last-fault.json') -Force -ErrorAction SilentlyContinue
& (Join-Path $PSScriptRoot 'lab-status.ps1')
exit $LASTEXITCODE