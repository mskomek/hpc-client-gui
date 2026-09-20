param([Parameter(Mandatory)][ValidateSet('ssh-loss','slurm-loss','drain','down','reconnect')][string]$Action,[string]$Node='compute01')
. (Join-Path $PSScriptRoot 'lab-common.ps1')
$target = Get-Node $Node; if (-not $target) { throw "Unknown node: $Node" }; $controller = Get-Node login-control01
switch ($Action) {
  'ssh-loss' { Invoke-LabSsh $target.ip 'sudo systemctl stop ssh' | Out-Null }
  'slurm-loss' { Invoke-LabSsh $target.ip 'sudo systemctl stop slurmd' | Out-Null }
  'drain' { Invoke-LabSsh $controller.ip "sudo scontrol update NodeName=$Node State=DRAIN Reason=LOCAL_REAL_FAULT" | Out-Null }
  'down' { Require-Admin; Stop-VM -Name $Node -Force -TurnOff }
  'reconnect' { Invoke-LabSsh $target.ip 'sudo systemctl start ssh munge slurmd' | Out-Null; Invoke-LabSsh $controller.ip "sudo scontrol update NodeName=$Node State=RESUME" | Out-Null }
}
Write-Json ([pscustomobject]@{action=$Action;node=$Node;generated_at=(Get-Date).ToUniversalTime().ToString('o')}) (Join-Path $EvidenceRoot 'last-fault.json')
