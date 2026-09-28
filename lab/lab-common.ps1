$ErrorActionPreference = 'Stop'
$LabRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StateRoot = Join-Path ([Environment]::GetFolderPath('LocalApplicationData')) 'hpc-client-gui-lab'
$EvidenceRoot = Join-Path $LabRoot 'evidence'
$Config = Get-Content (Join-Path $LabRoot 'config.json') -Raw | ConvertFrom-Json


function Require-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run PowerShell as Administrator.' }
}
function Ensure-Dirs { New-Item -ItemType Directory -Force $StateRoot,$EvidenceRoot | Out-Null }
function Get-KnownHostsPath { Join-Path $StateRoot 'known_hosts' }
function Get-LabSshCommonOptions {
  return @('-o','BatchMode=yes','-o','StrictHostKeyChecking=accept-new','-o',('UserKnownHostsFile=' + (Get-KnownHostsPath)),'-o','IdentitiesOnly=yes','-o','LogLevel=ERROR','-o','ConnectTimeout=5','-o','ConnectionAttempts=1','-o','ServerAliveInterval=5','-o','ServerAliveCountMax=3')
}
function Remove-LabKnownHost([string]$TargetHost) {
  $knownHosts = Get-KnownHostsPath
  if (-not (Test-Path $knownHosts)) { return }
  $port = [int]$Config.ssh.port
  $targets = @($TargetHost)
  if ($port -ne 22) { $targets += "[$TargetHost]:$port" }
  foreach ($target in $targets | Select-Object -Unique) {
    & ssh-keygen -q -f $knownHosts -R $target 2>$null | Out-Null
  }
}
function Invoke-Checked {
  param(
    [Parameter(Mandatory=$true, Position=0)][string]$File,
    [Parameter(Position=1, ValueFromRemainingArguments=$true)][string[]]$ArgumentList
  )
  & $File @ArgumentList
  $code = $LASTEXITCODE
  if ($code -ne 0) { throw "$File failed with exit code $code" }
}
function Get-Node([string]$Name) { @($Config.nodes) | Where-Object name -eq $Name | Select-Object -First 1 }
function Get-ControllerNode {
  $nodes = @($Config.nodes | Where-Object role -eq 'controller')
  if ($nodes.Count -ne 1) { throw "config.json must define exactly one controller node; found $($nodes.Count)." }
  return $nodes[0]
}
function Get-ComputeNodes {
  $nodes = @($Config.nodes | Where-Object role -eq 'compute')
  if ($nodes.Count -lt 1) { throw 'config.json must define at least one compute node.' }
  return $nodes
}
function Get-KeyPath { Join-Path $StateRoot 'id_ed25519' }
function Get-PublicKey {
  $keyPath = Get-KeyPath
  $pubPath = "$keyPath.pub"
  if (-not (Test-Path $keyPath)) { throw "Lab SSH private key is missing: $keyPath" }
  if (-not (Test-Path $pubPath)) {
    $derived = & ssh-keygen -y -f $keyPath 2>$null
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace(($derived | Out-String))) {
      throw "Unable to derive the lab SSH public key from $keyPath"
    }
    (($derived | Out-String).Trim()) | Set-Content -Encoding ascii $pubPath
  }
  $public = (Get-Content $pubPath -Raw).Trim()
  if ($public -notmatch '^ssh-(ed25519|rsa|ecdsa-[^ ]+)\s+\S+') { throw "Lab SSH public key is malformed: $pubPath" }
  return $public
}
function Get-LabCommandTimeoutSeconds {
  # Every remote lab command is bounded. Slurm holds an allocation PENDING
  # forever when a required node is DOWN, so an unbounded ssh child would hang
  # the maintained harness instead of failing it.
  $configured = $Config.timeouts.command_seconds
  if ($null -ne $configured -and [int]$configured -gt 0) { return [int]$configured }
  return 180
}
function Get-LabAllocationTimeoutSeconds {
  $configured = $Config.timeouts.allocation_seconds
  if ($null -ne $configured -and [int]$configured -gt 0) { return [int]$configured }
  return 300
}
function ConvertTo-LabProcessArguments([string[]]$ArgumentList) {
  # Windows CommandLineToArgvW quoting. The lab passes arguments that contain
  # spaces (the base64 remote command), so the argument vector is re-quoted
  # deterministically instead of relying on PowerShell 5.1 array joining.
  $parts = @()
  foreach ($argument in @($ArgumentList)) {
    $value = [string]$argument
    if ($value -eq '') { $parts += '""'; continue }
    if ($value -notmatch '[\s"]') { $parts += $value; continue }
    $escaped = $value -replace '(\\*)"', '$1$1\"'
    $escaped = $escaped -replace '(\\+)$', '$1$1'
    $parts += '"' + $escaped + '"'
  }
  return ($parts -join ' ')
}
function Invoke-LabBoundedCommand {
  param(
    [Parameter(Mandatory=$true)][string]$FilePath,
    [Parameter()][AllowEmptyCollection()][AllowEmptyString()][string[]]$ArgumentList,
    [Parameter(Mandatory=$true)][string]$StdoutPath,
    [Parameter(Mandatory=$true)][string]$StderrPath,
    [int]$TimeoutSeconds = 180
  )
  # Runs a child process under a hard wall-clock bound and kills the process
  # tree on expiry, so a healthy-looking but non-completing child can never hang
  # the harness. A timeout is reported truthfully as a failure (exit 124), never
  # as a pass and never as an empty success.
  if ($null -eq $ArgumentList) { $ArgumentList = @() }
  if ($TimeoutSeconds -le 0) { $TimeoutSeconds = 180 }
  $startInfo = New-Object System.Diagnostics.ProcessStartInfo
  $startInfo.FileName = $FilePath
  $startInfo.Arguments = ConvertTo-LabProcessArguments $ArgumentList
  $startInfo.UseShellExecute = $false
  $startInfo.CreateNoWindow = $true
  $startInfo.RedirectStandardOutput = $true
  $startInfo.RedirectStandardError = $true
  $process = New-Object System.Diagnostics.Process
  $process.StartInfo = $startInfo
  $started = Get-Date
  $timedOut = $false
  $code = 255
  $stdout = ''
  $stderr = ''
  $null = $process.Start()
  $stdoutTask = $process.StandardOutput.ReadToEndAsync()
  $stderrTask = $process.StandardError.ReadToEndAsync()
  try {
    if (-not $process.WaitForExit(($TimeoutSeconds * 1000))) {
      $timedOut = $true
      # Kill(entireProcessTree) exists on .NET Core (PowerShell 7); Windows
      # PowerShell 5.1 falls back to killing the direct child.
      try { $process.Kill($true) } catch { try { $process.Kill() } catch { } }
      $null = $process.WaitForExit(5000)
    }
    try { if ($stdoutTask.Wait(5000)) { $stdout = [string]$stdoutTask.Result } } catch { }
    try { if ($stderrTask.Wait(5000)) { $stderr = [string]$stderrTask.Result } } catch { }
    $code = if ($timedOut) { 124 } else { $process.ExitCode }
  } finally {
    try { if (-not $process.HasExited) { $process.Kill() } } catch { }
    $process.Dispose()
  }
  if ($timedOut) {
    $message = "lab command exceeded the {0}s wall-clock bound and was terminated (target timeout was not honoured)" -f $TimeoutSeconds
    $stderr = (@($stderr) + $message) -join [Environment]::NewLine
  }
  [IO.File]::WriteAllText($StdoutPath, $stdout)
  [IO.File]::WriteAllText($StderrPath, $stderr)
  [pscustomobject]@{
    exit_code       = $code
    output          = ([string]$stdout).TrimEnd()
    stderr          = ([string]$stderr).TrimEnd()
    timed_out       = $timedOut
    timeout_seconds = $TimeoutSeconds
    duration_seconds = [math]::Round(((Get-Date) - $started).TotalSeconds, 2)
  }
}
function Invoke-LabSshCapture([string]$TargetHost,[string]$Command,[switch]$Pty,[int]$TimeoutSeconds = 0) {
  # PowerShell 5.1 + Windows OpenSSH may rewrite nested quoting in a raw remote
  # command argument. Encode the exact command bytes and decode them remotely.
  if ($TimeoutSeconds -le 0) { $TimeoutSeconds = Get-LabCommandTimeoutSeconds }
  $commandBytes = [Text.Encoding]::UTF8.GetBytes($Command)
  $commandBase64 = [Convert]::ToBase64String($commandBytes)
  # timeout guards the remote side too, so a killed client cannot orphan a Slurm
  # allocation that stays PENDING on the controller.
  $remoteCommand = "printf %s $commandBase64 | base64 -d | timeout -k 5 $TimeoutSeconds bash -s"
  $args = @(Get-LabSshCommonOptions) + @('-p',[string]$Config.ssh.port,'-i',(Get-KeyPath),"$($Config.ssh.user)@$TargetHost",$remoteCommand)
  if ($Pty) { $args = @('-tt') + $args }
  $stdoutPath = [IO.Path]::GetTempFileName()
  $stderrPath = [IO.Path]::GetTempFileName()
  try {
    $r = Invoke-LabBoundedCommand -FilePath 'ssh' -ArgumentList $args -StdoutPath $stdoutPath -StderrPath $stderrPath -TimeoutSeconds $TimeoutSeconds
  } finally {
    Remove-Item $stdoutPath,$stderrPath -Force -ErrorAction SilentlyContinue
  }
  $stdout = [string]$r.output
  $stderr = [string]$r.stderr
  [pscustomobject]@{
    exit_code        = $r.exit_code
    output           = ([string]$stdout).TrimEnd()
    stderr           = ([string]$stderr).TrimEnd()
    timed_out        = $r.timed_out
    timeout_seconds  = $r.timeout_seconds
    duration_seconds = $r.duration_seconds
  }
}
function Invoke-LabSsh([string]$TargetHost,[string]$Command,[switch]$Pty) { $r = Invoke-LabSshCapture $TargetHost $Command $Pty; $r.output; return $r.exit_code }
function Write-Json($Value,[string]$Path) { $Value | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 $Path }