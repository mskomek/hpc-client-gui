param([Parameter(Mandatory)][ValidateSet('ssh-loss','slurm-loss','drain','down','reconnect')][string]$Action,[string]$Node='compute01',[ValidateRange(10,300)][int]$RecoveryDelaySeconds=30)
. (Join-Path $PSScriptRoot 'lab-common.ps1')
$target = Get-Node $Node; if (-not $target) { throw "Unknown node: $Node" }; $controller = Get-Node login-control01
switch ($Action) {
  'ssh-loss' {
    $unit = "local-real-ssh-recovery-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
    Invoke-LabSsh $controller.ip "sudo systemd-run --unit=$unit --on-active=${RecoveryDelaySeconds}s /bin/systemctl start ssh; sudo systemctl stop ssh" | Out-Null
    $Node = $controller.name
  }
  'slurm-loss' {
    if ($target.role -ne 'compute') { throw 'slurm-loss requires a compute node.' }
    Invoke-LabSsh $target.ip 'sudo systemctl stop slurmd' | Out-Null
  }
  'drain' {
    if ($target.role -ne 'compute') { throw 'drain requires a compute node.' }
    Invoke-LabSsh $controller.ip "sudo scontrol update NodeName=$Node State=DRAIN Reason=LOCAL_REAL_FAULT" | Out-Null
  }
  'down' { Require-Admin; Stop-VM -Name $Node -Force -TurnOff }
  'reconnect' {
    if ($target.role -eq 'controller') {
      Invoke-LabSsh $target.ip 'sudo systemctl start ssh munge slurmdbd slurmctld' | Out-Null
    } else {
      Invoke-LabSsh $target.ip 'sudo systemctl start ssh munge slurmd' | Out-Null
      Invoke-LabSsh $controller.ip "sudo scontrol update NodeName=$Node State=RESUME" | Out-Null
    }
  }
}
Write-Json ([pscustomobject]@{action=$Action;node=$Node;generated_at=(Get-Date).ToUniversalTime().ToString('o')}) (Join-Path $EvidenceRoot 'last-fault.json')
