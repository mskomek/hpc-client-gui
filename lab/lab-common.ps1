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
function Invoke-LabSshCapture([string]$TargetHost,[string]$Command,[switch]$Pty) {
  # PowerShell 5.1 + Windows OpenSSH may rewrite nested quoting in a raw remote
  # command argument. Encode the exact command bytes and decode them remotely.
  $commandBytes = [Text.Encoding]::UTF8.GetBytes($Command)
  $commandBase64 = [Convert]::ToBase64String($commandBytes)
  $remoteCommand = "printf %s $commandBase64 | base64 -d | bash -s"
  $args = @(Get-LabSshCommonOptions) + @('-p',[string]$Config.ssh.port,'-i',(Get-KeyPath),"$($Config.ssh.user)@$TargetHost",$remoteCommand)
  if ($Pty) { $args = @('-tt') + $args }
  $stdoutPath = [IO.Path]::GetTempFileName()
  $stderrPath = [IO.Path]::GetTempFileName()
  $previousErrorActionPreference = $ErrorActionPreference
  $code = 255
  $stdout = ''
  $stderr = ''
  try {
    $ErrorActionPreference = 'Continue'
    & ssh @args 1> $stdoutPath 2> $stderrPath
    $code = $LASTEXITCODE
    $stdoutRaw = if (Test-Path $stdoutPath) { Get-Content $stdoutPath -Raw -ErrorAction SilentlyContinue } else { $null }
    $stderrRaw = if (Test-Path $stderrPath) { Get-Content $stderrPath -Raw -ErrorAction SilentlyContinue } else { $null }
    if ($null -ne $stdoutRaw) { $stdout = [string]$stdoutRaw }
    if ($null -ne $stderrRaw) { $stderr = [string]$stderrRaw }
  } finally {
    $ErrorActionPreference = $previousErrorActionPreference
    Remove-Item $stdoutPath,$stderrPath -Force -ErrorAction SilentlyContinue
  }
  [pscustomobject]@{ exit_code = $code; output = ([string]$stdout).TrimEnd(); stderr = ([string]$stderr).TrimEnd() }
}
function Invoke-LabSsh([string]$TargetHost,[string]$Command,[switch]$Pty) { $r = Invoke-LabSshCapture $TargetHost $Command $Pty; $r.output; return $r.exit_code }
function Write-Json($Value,[string]$Path) { $Value | ConvertTo-Json -Depth 12 | Set-Content -Encoding utf8 $Path }