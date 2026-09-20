$ErrorActionPreference = 'Stop'
$LabRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$StateRoot = Join-Path $LabRoot 'state'
$EvidenceRoot = Join-Path $LabRoot 'evidence'
$Config = Get-Content (Join-Path $LabRoot 'config.json') -Raw | ConvertFrom-Json

function Require-Admin {
  $id = [Security.Principal.WindowsIdentity]::GetCurrent()
  if (-not ([Security.Principal.WindowsPrincipal]$id).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) { throw 'Run PowerShell as Administrator.' }
}
function Ensure-Dirs { New-Item -ItemType Directory -Force $StateRoot,$EvidenceRoot | Out-Null }
function Invoke-Checked([string]$File,[string[]]$Args) { & $File @Args; if ($LASTEXITCODE -ne 0) { throw "$File failed with exit code $LASTEXITCODE" } }
function Get-Node([string]$Name) { @($Config.nodes) | Where-Object name -eq $Name | Select-Object -First 1 }
function Get-KeyPath { Join-Path $StateRoot 'id_ed25519' }
function Get-PublicKey { (Get-Content ((Get-KeyPath).ToString() + '.pub') -Raw).Trim() }
function Invoke-LabSshCapture([string]$Host,[string]$Command,[switch]$Pty) {
  $args = @('-o','StrictHostKeyChecking=no','-o','UserKnownHostsFile=NUL','-i',(Get-KeyPath),"$($Config.ssh.user)@$Host",$Command)
  if ($Pty) { $args = @('-tt') + $args }
  $out = & ssh @args 2>&1
  [pscustomobject]@{ exit_code = $LASTEXITCODE; output = ($out -join "`n") }
}
function Invoke-LabSsh([string]$Host,[string]$Command,[switch]$Pty) { $r = Invoke-LabSshCapture $Host $Command $Pty; $r.output; return $r.exit_code }
function Write-Json($Value,[string]$Path) { $Value | ConvertTo-Json -Depth 10 | Set-Content -Encoding utf8 $Path }
