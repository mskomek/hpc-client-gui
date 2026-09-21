. (Join-Path $PSScriptRoot 'lab-common.ps1')
Ensure-Dirs
$controller = Get-ControllerNode
$computeNodes = @(Get-ComputeNodes)


$items = foreach ($node in $Config.nodes) {
  $services = if ($node.role -eq 'controller') { @('ssh','munge','slurmctld','slurmdbd','mariadb','nfs-server') } else { @('ssh','munge','slurmd') }
  $transport = Invoke-LabSshCapture $node.ip 'hostname'
  $serviceCommand = 'systemctl is-active ' + ($services -join ' ')
  $serviceProbe = if ($transport.exit_code -eq 0) { Invoke-LabSshCapture $node.ip $serviceCommand } else { [pscustomobject]@{exit_code=255;output='';stderr='SSH transport unavailable'} }
  [pscustomobject]@{
    name=$node.name
    ip=$node.ip
    role=$node.role
    transport_ok=($transport.exit_code -eq 0 -and $transport.output.Trim() -eq [string]$node.name)
    services_ok=($serviceProbe.exit_code -eq 0)
    services=$services
    service_states=$serviceProbe.output
    stderr=(@($transport.stderr,$serviceProbe.stderr) | Where-Object { $_ } | Select-Object -Unique) -join "`n"
  }
}


$slurmProbe = Invoke-LabSshCapture $controller.ip 'sinfo -h -N -o "%N|%t"'
$stateMap = @{}
foreach ($line in @($slurmProbe.output -split "`r?`n")) {
  if ($line -match '^([^|]+)\|(.+)$') { $stateMap[$matches[1].Trim()] = $matches[2].Trim() }
}
$slurmOk = ($slurmProbe.exit_code -eq 0)
foreach ($node in $computeNodes) {
  $name = [string]$node.name
  if (-not $stateMap.ContainsKey($name) -or $stateMap[$name] -notin @('idle','mix','alloc')) { $slurmOk = $false }
}


$versionCommand = 'set -eu; . /etc/os-release; printf "os=%s\n" "$PRETTY_NAME"; sinfo --version; dpkg-query -W -f="\${Package}=\${Version}\n" openssh-server munge slurm-wlm slurmctld slurmdbd mariadb-server nfs-kernel-server'
$versionProbe = Invoke-LabSshCapture $controller.ip $versionCommand
$imagePath = Join-Path $StateRoot $Config.image.file
$imageSha = if (Test-Path $imagePath) { (Get-FileHash -Algorithm SHA256 $imagePath).Hash.ToLowerInvariant() } else { '' }
$expectedImageSha = ([string]$Config.image.sha256).Trim().ToLowerInvariant()
$imagePinOk = ($expectedImageSha -match '^[0-9a-f]{64}$' -and $imageSha -eq $expectedImageSha)
$baseSourceHashPath = (Join-Path $StateRoot 'ubuntu-base.vhdx.source.sha256')
$baseSourceSha = if (Test-Path $baseSourceHashPath) { (Get-Content $baseSourceHashPath -Raw).Trim().ToLowerInvariant() } else { '' }


$profilePath = Join-Path $StateRoot 'hpc-client-profile.json'
$profileOk = $false
$profileSha = ''
$profileError = ''
if (Test-Path $profilePath) {
  try {
    $profileData = Get-Content $profilePath -Raw | ConvertFrom-Json
    $profileOk = (
      [string]$profileData.name -eq 'LOCAL_REAL' -and
      [string]$profileData.host -eq [string]$controller.ip -and
      [int]$profileData.port -eq [int]$Config.ssh.port -and
      [string]$profileData.username -eq [string]$Config.ssh.user -and
      [string]$profileData.key_path -eq [string](Get-KeyPath) -and
      [string]$profileData.host_key_policy -eq 'accept-new' -and
      (Test-Path ([string]$profileData.key_path)) -and
      [int]$profileData.provider_template.schema_version -eq 2 -and
      [string]$profileData.provider_template.profile_id -eq 'local-real' -and
      [string]$profileData.provider_template.scheduler -eq 'slurm' -and
      @($profileData.provider_template.storage).Count -eq 3
    )
    $profileSha = (Get-FileHash -Algorithm SHA256 $profilePath).Hash.ToLowerInvariant()
  } catch {
    $profileError = $_.Exception.Message
  }
} else {
  $profileError = 'profile file missing'
}
$identityOk = ($versionProbe.exit_code -eq 0 -and $imagePinOk -and $baseSourceSha -eq $imageSha -and $profileOk)


$statusOk = (@($items | Where-Object {-not $_.transport_ok -or -not $_.services_ok}).Count -eq 0) -and $slurmOk -and $identityOk
$status = [pscustomobject]@{
  status=if ($statusOk) {'PASS'} else {'FAIL'}
  topology=$items
  slurm=[pscustomobject]@{ ok=$slurmOk; output=$slurmProbe.output; stderr=$slurmProbe.stderr }
  environment_identity=[pscustomobject]@{
    kind='LOCAL_REAL_HYPERV'
    switch=[string]$Config.switch
    prefix=[string]$Config.prefix
    gateway=[string]$Config.gateway
    image_url=[string]$Config.image.url
    image_file=[string]$Config.image.file
    expected_image_sha256=$expectedImageSha
    image_sha256=$imageSha
    image_pin_ok=$imagePinOk
    base_vhdx_source_sha256=$baseSourceSha
    remote_versions=$versionProbe.output
    remote_versions_stderr=$versionProbe.stderr
    profile_path=$profilePath
    profile_sha256=$profileSha
    profile_valid=$profileOk
    profile_error=$profileError
    nodes=@($Config.nodes | ForEach-Object { [pscustomobject]@{name=$_.name;ip=$_.ip;role=$_.role;cpus=$_.cpus;memory_mb=$_.memory_mb;disk_gb=$_.disk_gb} })
  }
  generated_at=(Get-Date).ToUniversalTime().ToString('o')
}
Write-Json $status (Join-Path $EvidenceRoot 'health.json')
$status | ConvertTo-Json -Depth 10
if (-not $statusOk) { exit 3 }
exit 0