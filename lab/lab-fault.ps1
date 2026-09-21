param(
  [Parameter(Mandatory)][ValidateSet('ssh-loss','slurm-loss','drain','down','reconnect')][string]$Action,
  [string]$Node='',
  [ValidateRange(10,300)][int]$RecoveryDelaySeconds=30
)
. (Join-Path $PSScriptRoot 'lab-common.ps1')
$controller = Get-ControllerNode
if (-not $Node) {
  if ($Action -eq 'ssh-loss') {
    $Node = $controller.name
  } elseif ($Action -eq 'reconnect') {
    $lastFaultPath = Join-Path $EvidenceRoot 'last-fault.json'
    if (Test-Path $lastFaultPath) {
      try { $Node = [string]((Get-Content $lastFaultPath -Raw | ConvertFrom-Json).node) } catch { $Node = '' }
    }
    if (-not $Node) { $Node = $controller.name }
  } else {
    $Node = (Get-ComputeNodes | Select-Object -First 1).name
  }
}
$target = Get-Node $Node
if (-not $target) { throw "Unknown node: $Node" }


switch ($Action) {
  'ssh-loss' {
    $unit = "local-real-ssh-recovery-$([DateTimeOffset]::UtcNow.ToUnixTimeSeconds())"
    # Schedule recovery before killing the listener/session. OpenSSH process
    # titles vary by build: cover both "sshd:" and "sshd-session:" forms.
    # The SSH client invocation must disconnect non-zero; otherwise only the
    # listener was stopped and this is not truthful transport-loss evidence.
    $command = "sudo systemd-run --quiet --unit=$unit --on-active=${RecoveryDelaySeconds}s /bin/systemctl start ssh; sudo systemctl stop ssh; sudo pkill -KILL -f '^(sshd|sshd-session): hpctest' || true"
    $result = Invoke-LabSshCapture $target.ip $command
    $listenerDown = $false
    for ($i=0; $i -lt 10; $i++) {
      if (-not (Test-NetConnection $target.ip -Port $Config.ssh.port -InformationLevel Quiet -WarningAction SilentlyContinue)) { $listenerDown = $true; break }
      Start-Sleep -Milliseconds 500
    }
    $sessionDropped = $result.exit_code -ne 0
    if (-not $listenerDown -or -not $sessionDropped) {
      throw "SSH loss injection was incomplete on $($target.name): listenerDown=$listenerDown sessionDropped=$sessionDropped exit=$($result.exit_code)"
    }
    $Node = $target.name
  }
  'slurm-loss' {
    if ($target.role -ne 'compute') { throw 'slurm-loss requires a compute node.' }
    $result = Invoke-LabSshCapture $target.ip 'sudo systemctl stop slurmd'
    if ($result.exit_code -ne 0) { throw "Failed to stop slurmd on $Node: $($result.stderr)" }
  }
  'drain' {
    if ($target.role -ne 'compute') { throw 'drain requires a compute node.' }
    $result = Invoke-LabSshCapture $controller.ip "sudo scontrol update NodeName=$Node State=DRAIN Reason=LOCAL_REAL_FAULT"
    if ($result.exit_code -ne 0) { throw "Failed to drain $Node: $($result.stderr)" }
  }
  'down' {
    Require-Admin
    Stop-VM -Name $Node -Force -TurnOff
  }
  'reconnect' {
    if (-not (Test-NetConnection $target.ip -Port $Config.ssh.port -InformationLevel Quiet -WarningAction SilentlyContinue)) {
      Require-Admin
      $vm = Get-VM -Name $target.name -ErrorAction SilentlyContinue
      if (-not $vm) { throw "VM does not exist: $($target.name)" }
      if ($vm.State -eq 'Off') { Start-VM -Name $target.name | Out-Null }
      else { Restart-VM -Name $target.name -Force }
      $ready = $false
      for ($i=0; $i -lt 60; $i++) {
        if (Test-NetConnection $target.ip -Port $Config.ssh.port -InformationLevel Quiet -WarningAction SilentlyContinue) { $ready=$true; break }
        Start-Sleep 2
      }
      if (-not $ready) { throw "Target did not recover SSH after VM restart/start: $($target.name)" }
    }
    if ($target.role -eq 'controller') {
      $result = Invoke-LabSshCapture $target.ip 'sudo systemctl restart munge slurmdbd slurmctld ssh; systemctl is-active --quiet ssh munge slurmdbd slurmctld'
    } else {
      $result = Invoke-LabSshCapture $target.ip 'sudo systemctl restart munge slurmd ssh; systemctl is-active --quiet ssh munge slurmd'
      if ($result.exit_code -eq 0) { $result = Invoke-LabSshCapture $controller.ip "sudo scontrol update NodeName=$Node State=RESUME" }
    }
    if ($result.exit_code -ne 0) { throw "Reconnect failed for $Node.`n$($result.output)`n$($result.stderr)" }
  }
}
$faultStatus = if ($Action -eq 'reconnect') {'RECOVERED'} else {'INJECTED'}
Write-Json ([pscustomobject]@{action=$Action;node=$Node;status=$faultStatus;generated_at=(Get-Date).ToUniversalTime().ToString('o')}) (Join-Path $EvidenceRoot 'last-fault.json')