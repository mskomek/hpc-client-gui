. (Join-Path $PSScriptRoot 'lab-common.ps1')
Require-Admin; Ensure-Dirs
& (Join-Path $PSScriptRoot 'lab-prereq.ps1'); if ($LASTEXITCODE) { exit $LASTEXITCODE }


function Convert-ToWslPath([string]$Path) {
  $full = [IO.Path]::GetFullPath($Path)
  if ($full.Length -lt 3 -or $full[1] -ne ':') { throw "Unsupported Windows path for WSL conversion: $full" }
  $drive = $full.Substring(0,1).ToLowerInvariant()
  $rest = $full.Substring(2).Replace('\','/')
  return "/mnt/$drive$rest"
}


$controller = Get-ControllerNode
$computeNodes = @(Get-ComputeNodes)
$allNames = @($Config.nodes | ForEach-Object { [string]$_.name })
$allIps = @($Config.nodes | ForEach-Object { [string]$_.ip })
if (@($allNames | Select-Object -Unique).Count -ne $allNames.Count) { throw 'config.json contains duplicate node names.' }
if (@($allIps | Select-Object -Unique).Count -ne $allIps.Count) { throw 'config.json contains duplicate node IPs.' }
if ([int]$Config.ssh.port -lt 1 -or [int]$Config.ssh.port -gt 65535) { throw 'config.json ssh.port is invalid.' }
if ([string]$Config.ssh.user -ne 'hpctest') { throw "LOCAL_REAL currently requires ssh.user=hpctest; configured '$($Config.ssh.user)'." }
if ([string]$Config.image.url -notmatch '^https://') { throw 'config.json image.url must use HTTPS.' }
$expectedImageHash = ([string]$Config.image.sha256).Trim().ToLowerInvariant()
if ($expectedImageHash -notmatch '^[0-9a-f]{64}$') { throw 'config.json image.sha256 must be a 64-character SHA-256 hex digest.' }
foreach ($node in $Config.nodes) {
  if ([string]$node.name -notmatch '^[a-z0-9][a-z0-9-]{0,62}$') { throw "Invalid node name: $($node.name)" }
  if ([string]$node.role -notin @('controller','compute')) { throw "Invalid node role for $($node.name): $($node.role)" }
  $parsedIp = $null
  if (-not [Net.IPAddress]::TryParse([string]$node.ip, [ref]$parsedIp) -or $parsedIp.AddressFamily -ne [Net.Sockets.AddressFamily]::InterNetwork) { throw "Invalid IPv4 address for $($node.name): $($node.ip)" }
  if ([int]$node.cpus -lt 1 -or [int]$node.memory_mb -lt 768 -or [int]$node.disk_gb -lt 4) { throw "Invalid hardware sizing for $($node.name)." }
}


if (-not (Test-Path (Get-KeyPath))) {
  $keyPath = Get-KeyPath
  $keygenCommand = 'ssh-keygen -q -t ed25519 -N "" -f "{0}"' -f $keyPath
  & cmd.exe /d /s /c $keygenCommand
  if ($LASTEXITCODE -ne 0) { throw "ssh-keygen failed with exit code $LASTEXITCODE" }
}


if (-not (Get-VMSwitch -Name $Config.switch -ErrorAction SilentlyContinue)) { New-VMSwitch -Name $Config.switch -SwitchType Internal | Out-Null }
$adapter = Get-NetAdapter | Where-Object { $_.Name -like "vEthernet ($($Config.switch))" } | Select-Object -First 1
$prefixLength = [int](($Config.prefix -split '/')[1])
if ($prefixLength -lt 1 -or $prefixLength -gt 32) { throw "Invalid IPv4 prefix: $($Config.prefix)" }
if ($adapter -and -not (Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $Config.gateway -ErrorAction SilentlyContinue)) { New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $Config.gateway -PrefixLength $prefixLength | Out-Null }
$natName = "$($Config.switch)-nat"
$nat = Get-NetNat -Name $natName -ErrorAction SilentlyContinue
if ($nat -and $nat.InternalIPInterfaceAddressPrefix -ne $Config.prefix) { throw "Existing NAT $natName uses $($nat.InternalIPInterfaceAddressPrefix), expected $($Config.prefix). Remove/recreate the lab NAT." }
if (-not $nat) { New-NetNat -Name $natName -InternalIPInterfaceAddressPrefix $Config.prefix | Out-Null }


$image = Join-Path $StateRoot $Config.image.file
$baseVhdx = Join-Path $StateRoot 'ubuntu-base.vhdx'
$partialImage = "$image.partial"
if (Test-Path $partialImage) { Remove-Item $partialImage -Force }
if ((Test-Path $image) -and (Get-Item $image).Length -lt 100MB) { Remove-Item $image -Force }
if (-not (Test-Path $image)) {
  Invoke-WebRequest $Config.image.url -OutFile $partialImage
  if (-not (Test-Path $partialImage) -or (Get-Item $partialImage).Length -lt 100MB) { throw 'Ubuntu cloud image download is incomplete.' }
  Move-Item $partialImage $image -Force
}
$imageHash = (Get-FileHash -Algorithm SHA256 $image).Hash.ToLowerInvariant()
if ($imageHash -ne $expectedImageHash) {
  throw "Ubuntu cloud image SHA-256 mismatch. expected=$expectedImageHash actual=$imageHash. The pinned lab image must be reviewed before use."
}
$baseHashPath = "$baseVhdx.source.sha256"
if ((Test-Path $baseVhdx) -and (Test-Path $baseHashPath)) {
  $recordedHash = (Get-Content $baseHashPath -Raw).Trim().ToLowerInvariant()
  if ($recordedHash -ne $imageHash) {
    $existingNodeDisks = @($Config.nodes | Where-Object { Test-Path (Join-Path (Join-Path $StateRoot $_.name) "$($_.name).vhdx") })
    if ($existingNodeDisks.Count -gt 0) { throw 'Ubuntu source image changed while differencing node disks exist. Recreate the LOCAL_REAL node state before continuing.' }
    Remove-Item $baseVhdx -Force
  }
}
if (-not (Test-Path $baseVhdx)) {
  $source = Convert-ToWslPath ((Resolve-Path $image).Path)
  $tempVhdx = "$baseVhdx.new"
  Remove-Item $tempVhdx -Force -ErrorAction SilentlyContinue
  $dest = Convert-ToWslPath $tempVhdx
  $qemuCommand = "qemu-img convert -p -O vhdx '$source' '$dest'"
  & wsl.exe bash -lc $qemuCommand
  if ($LASTEXITCODE -ne 0) { Remove-Item $tempVhdx -Force -ErrorAction SilentlyContinue; throw "qemu-img failed with exit code $LASTEXITCODE" }
  try { Get-VHD -Path $tempVhdx | Out-Null } catch { Remove-Item $tempVhdx -Force -ErrorAction SilentlyContinue; throw 'Converted base VHDX is invalid.' }
  Move-Item $tempVhdx $baseVhdx -Force
  Set-Content $baseHashPath $imageHash -Encoding ascii
} elseif (-not (Test-Path $baseHashPath)) {
  throw 'Existing base VHDX has no trusted source-image hash. Recreate the LOCAL_REAL base image instead of fabricating provenance.'
}
try { Get-VHD -Path $baseVhdx | Out-Null } catch { throw 'Base VHDX cannot be read by Hyper-V. Remove LOCAL_REAL state and rebuild.' }


$public = Get-PublicKey
$computeCpus = @($computeNodes | Select-Object -ExpandProperty cpus -Unique)
if ($computeCpus.Count -ne 1 -or $computeCpus[0] -lt 1) { throw 'All compute nodes must define the same positive cpus value.' }
$computeMemory = @($computeNodes | Select-Object -ExpandProperty memory_mb -Unique)
if ($computeMemory.Count -ne 1 -or $computeMemory[0] -lt 768) { throw 'All compute nodes must define the same memory_mb value of at least 768 MB.' }
$slurmRealMemory = [int]$computeMemory[0] - 256
$computeNodeList = (@($computeNodes | ForEach-Object { $_.name }) -join ',')


foreach ($node in $Config.nodes) {
  $vmPath = Join-Path $StateRoot $node.name
  New-Item -ItemType Directory -Force $vmPath | Out-Null
  $disk = Join-Path $vmPath "$($node.name).vhdx"
  $diskBytes = [int64]$node.disk_gb * 1GB
  $vm = Get-VM -Name $node.name -ErrorAction SilentlyContinue
  if (-not (Test-Path $disk)) { New-VHD -Path $disk -ParentPath $baseVhdx -Differencing | Out-Null }
  $diskInfo = Get-VHD -Path $disk
  if ($diskInfo.Size -lt $diskBytes -and $vm -and $vm.State -eq 'Running') {
    Stop-VM -Name $node.name
    for ($wait = 0; $wait -lt 30 -and (Get-VM -Name $node.name).State -ne 'Off'; $wait++) { Start-Sleep 1 }
    if ((Get-VM -Name $node.name).State -ne 'Off') { throw "VM did not stop for disk resize: $($node.name)" }
  }
  if ($diskInfo.Size -lt $diskBytes) { Resize-VHD -Path $disk -SizeBytes $diskBytes }
  elseif ($diskInfo.Size -gt $diskBytes) { throw "Existing VM disk exceeds configured disk_gb; recreate the node before reducing it: $($node.name)" }


  $lastOctet = [int](($node.ip -split '\.')[-1])
  $macAddress = ('02:00:00:FA:00:{0:X2}' -f $lastOctet).ToLowerInvariant()
  $hyperVMac = $macAddress.Replace(':','')
  $seed = Join-Path $vmPath 'seed'
  New-Item -ItemType Directory -Force $seed | Out-Null
  $hosts = ($Config.nodes | ForEach-Object { "      $($_.ip) $($_.name)" }) -join "`n"
  $userData = @('#cloud-config','users:',"  - name: $($Config.ssh.user)",'    sudo: ALL=(ALL) NOPASSWD:ALL','    shell: /bin/bash','    ssh_authorized_keys:',"      - $public",'ssh_pwauth: false','write_files:','  - path: /etc/hosts','    append: true','    content: |',$hosts,'runcmd:','  - systemctl enable --now ssh')
  $userData | Set-Content (Join-Path $seed 'user-data') -Encoding ascii
  @("instance-id: $($node.name)","local-hostname: $($node.name)") | Set-Content (Join-Path $seed 'meta-data') -Encoding ascii
  @('version: 2','ethernets:','  id0:','    match:',"      macaddress: $macAddress",'    dhcp4: false','    optional: true',"    addresses: [$($node.ip)/$prefixLength]",'    routes:','      - to: default',"        via: $($Config.gateway)",'    nameservers:','      addresses: [1.1.1.1, 8.8.8.8]') | Set-Content (Join-Path $seed 'network-config') -Encoding ascii


  $seedHashes = @('user-data','meta-data','network-config') | ForEach-Object { (Get-FileHash -Algorithm SHA256 (Join-Path $seed $_)).Hash }
  $seedFingerprint = $seedHashes -join ':'
  $seedHashPath = Join-Path $vmPath 'seed.sha256'
  $iso = Join-Path $vmPath 'seed.iso'
  $existingSeedHash = if (Test-Path $seedHashPath) { (Get-Content $seedHashPath -Raw).Trim() } else { '' }
  if ($vm -and $existingSeedHash -and $existingSeedHash -ne $seedFingerprint) { throw "Cloud-init seed drift detected for $($node.name). Recreate that lab node before applying network/user-data changes." }
  if (-not $vm -and ($existingSeedHash -ne $seedFingerprint -or -not (Test-Path $iso))) {
    Remove-Item $iso -Force -ErrorAction SilentlyContinue
    $seedWsl = Convert-ToWslPath ((Resolve-Path $seed).Path)
    $isoWsl = Convert-ToWslPath $iso
    $isoCommand = "genisoimage -output '$isoWsl' -volid cidata -joliet -rock '$seedWsl'"
    & wsl.exe bash -lc $isoCommand
    if ($LASTEXITCODE -ne 0) { throw "genisoimage failed with exit code $LASTEXITCODE" }
    Set-Content $seedHashPath $seedFingerprint -Encoding ascii
  } elseif ($vm -and -not $existingSeedHash) {
    # Migration for already-created nodes from the first lab revision.
    Set-Content $seedHashPath $seedFingerprint -Encoding ascii
  }


  if (-not $vm) {
    Remove-LabKnownHost $node.ip
    New-VM -Name $node.name -Generation 2 -MemoryStartupBytes ($node.memory_mb * 1MB) -VHDPath $disk -SwitchName $Config.switch | Out-Null
    Set-VMNetworkAdapter -VMName $node.name -StaticMacAddress $hyperVMac
    Add-VMDvdDrive -VMName $node.name -Path $iso | Out-Null
    Set-VM -Name $node.name -AutomaticStopAction ShutDown
  }
  $vm = Get-VM -Name $node.name
  $firmware = Get-VMFirmware -VMName $node.name
  $processor = Get-VMProcessor -VMName $node.name
  $memory = Get-VMMemory -VMName $node.name
  $networkAdapter = Get-VMNetworkAdapter -VMName $node.name | Select-Object -First 1
  $networkOk = $networkAdapter.MacAddress -eq $hyperVMac -and $networkAdapter.SwitchName -eq [string]$Config.switch
  $memoryOk = (-not $memory.DynamicMemoryEnabled) -and $memory.Startup -eq ([int64]$node.memory_mb * 1MB)
  $hardwareOk = $firmware.SecureBoot -eq 'On' -and $firmware.SecureBootTemplate -eq 'MicrosoftUEFICertificateAuthority' -and $processor.Count -eq $node.cpus -and $memoryOk -and $networkOk
  if ($vm.State -eq 'Running' -and -not $hardwareOk) {
    Stop-VM -Name $node.name
    for ($wait = 0; $wait -lt 30 -and (Get-VM -Name $node.name).State -ne 'Off'; $wait++) { Start-Sleep 1 }
    if ((Get-VM -Name $node.name).State -ne 'Off') { throw "VM did not stop for required hardware reconfiguration: $($node.name)" }
  }
  if ((Get-VM -Name $node.name).State -ne 'Running') {
    Set-VMFirmware -VMName $node.name -EnableSecureBoot On -SecureBootTemplate 'MicrosoftUEFICertificateAuthority'
    Set-VMProcessor -VMName $node.name -Count $node.cpus
    Set-VMMemory -VMName $node.name -DynamicMemoryEnabled $false -StartupBytes ([int64]$node.memory_mb * 1MB)
    Connect-VMNetworkAdapter -VMName $node.name -SwitchName $Config.switch
    Set-VMNetworkAdapter -VMName $node.name -StaticMacAddress $hyperVMac
    Start-VM $node.name | Out-Null
  }
}


foreach ($node in $Config.nodes) {
  $ready = $false
  for ($i=0; $i -lt 60; $i++) {
    if (Test-NetConnection $node.ip -Port $Config.ssh.port -InformationLevel Quiet) {
      $probe = Invoke-LabSshCapture $node.ip 'cloud-init status --wait >/dev/null 2>&1'
      if ($probe.exit_code -eq 0) { $ready = $true; break }
    }
    Start-Sleep 2
  }
  if (-not $ready) { throw "SSH/cloud-init did not become ready: $($node.name)" }
}


function Send-Script($targetHost,$path,$env='') {
  $scriptText = (Get-Content $path -Raw).Replace("`r`n","`n").Replace("`r","`n")
  $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($scriptText))
  $remoteCommand = "echo '$b64' | base64 -d | sudo $env bash -s"
  $result = Invoke-LabSshCapture $targetHost $remoteCommand
  if ($result.exit_code -ne 0) {
    $name = Split-Path -Leaf $path
    throw "Remote provisioning failed on $targetHost for $name (exit $($result.exit_code)).`nSTDOUT:`n$($result.output)`nSTDERR:`n$($result.stderr)"
  }
}


$controllerEnv = "env SLURM_COMPUTE_CPUS=$($computeCpus[0]) SLURM_COMPUTE_REAL_MEMORY=$slurmRealMemory SLURM_COMPUTE_NODES=$computeNodeList SLURM_CONTROLLER_HOST=$($controller.name) SLURM_CLUSTER_NAME=local-real LAB_NFS_CIDR=$($Config.prefix)"
Send-Script $controller.ip (Join-Path $PSScriptRoot 'provision/controller.sh') $controllerEnv


$identity = Invoke-LabSshCapture $controller.ip 'id -u hpctest; id -g hpctest; id -u slurm; id -g slurm'
if ($identity.exit_code -ne 0 -or $identity.output.Trim() -notmatch '^\d+\s+\d+\s+\d+\s+\d+$') { throw "Controller did not provide canonical user/group IDs. exit=$($identity.exit_code) output='$($identity.output)' stderr='$($identity.stderr)'" }
$identityIds = $identity.output.Trim() -split '\s+'
$computeEnv = "env HPCTEST_UID=$($identityIds[0]) HPCTEST_GID=$($identityIds[1]) SLURM_UID=$($identityIds[2]) SLURM_GID=$($identityIds[3]) LAB_CONTROLLER_HOST=$($controller.name)"
foreach ($node in $computeNodes) { Send-Script $node.ip (Join-Path $PSScriptRoot 'provision/compute.sh') $computeEnv }


$slurmConf = Invoke-LabSshCapture $controller.ip 'sudo base64 -w0 /etc/slurm/slurm.conf'
if ($slurmConf.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($slurmConf.output)) { throw 'Controller did not provide /etc/slurm/slurm.conf' }
$munge = Invoke-LabSshCapture $controller.ip 'sudo base64 -w0 /etc/munge/munge.key'
if ($munge.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($munge.output)) { throw 'Controller did not provide /etc/munge/munge.key' }
foreach ($node in $computeNodes) {
  $remoteSetup = "echo '$($slurmConf.output)' | base64 -d | sudo install -o root -g root -m 0644 /dev/stdin /etc/slurm/slurm.conf; echo '$($munge.output)' | base64 -d | sudo install -o munge -g munge -m 0400 /dev/stdin /etc/munge/munge.key; sudo systemctl enable munge slurmd >/dev/null; sudo systemctl restart munge; munge -n | unmunge >/dev/null; sudo systemctl restart slurmd; systemctl is-active --quiet munge slurmd"
  $setupResult = Invoke-LabSshCapture $node.ip $remoteSetup
  if ($setupResult.exit_code -ne 0) { throw "Compute service/config activation failed on $($node.name).`nSTDOUT:`n$($setupResult.output)`nSTDERR:`n$($setupResult.stderr)" }
}


$slurmReady = $false
for ($i=0; $i -lt 60; $i++) {
  $readyProbe = Invoke-LabSshCapture $controller.ip 'sinfo -h -N -o "%N|%t"'
  if ($readyProbe.exit_code -eq 0) {
    $stateMap = @{}
    foreach ($line in @($readyProbe.output -split "`r?`n")) {
      if ($line -match '^([^|]+)\|(.+)$') { $stateMap[$matches[1].Trim()] = $matches[2].Trim() }
    }
    $allReady = $true
    foreach ($node in $computeNodes) {
      if (-not $stateMap.ContainsKey([string]$node.name) -or $stateMap[[string]$node.name] -ne 'idle') { $allReady = $false; break }
    }
    if ($allReady) { $slurmReady = $true; break }
  }
  Start-Sleep 2
}
if (-not $slurmReady) {
  $diag = Invoke-LabSshCapture $controller.ip 'sinfo -N -l; scontrol show nodes'
  throw "Slurm compute nodes did not become IDLE.`n$($diag.output)`n$($diag.stderr)"
}


$providerTemplate = [ordered]@{
  schema_version = 2
  profile_id = 'local-real'
  name = 'LOCAL_REAL'
  scheduler = 'slurm'
  description = 'Disposable local Hyper-V HPC integration lab'
  site = @{ public_name='LOCAL_REAL'; region='local'; access_note='Disposable maintainer-owned integration lab' }
  access = @{
    hosts=@(@{host=[string]$controller.ip;port=[int]$Config.ssh.port;role='login-controller'})
    auth_methods=@('ssh-key')
    access_note='Generated lab SSH key'
    documentation_url=$null
  }
  requirements = @{ project=@{required=$false;label='Project';help=''}; account=@{required=$false;label='Account';help=''} }
  scheduler_hints = @{ queue_notes='debug partition'; account_notes='local account'; partitions=@('debug') }
  software = @{ module_paths=@(); setup_notes='' }
  storage = @(
    @{id='home';label='Home';enabled=$true;kind='home';path_template='/srv/hpc/home/{user}';access_context='shared'},
    @{id='scratch';label='Scratch';enabled=$true;kind='scratch';path_template='/srv/hpc/scratch/{user}';access_context='shared'},
    @{id='project';label='Project';enabled=$true;kind='project';path_template='/srv/hpc/project/{user}';access_context='shared'}
  )
  quota_sources = @()
}
$profile = [ordered]@{
  name='LOCAL_REAL'
  host=$controller.ip
  port=$Config.ssh.port
  username='hpctest'
  project=''
  account=''
  password=''
  save_password=$false
  key_path=(Get-KeyPath)
  host_key_policy='accept-new'
  x11_forwarding=$false
  cli_allowed=$false
  transfer_parallelism=1
  keepalive_interval_seconds=30
  provider_template=$providerTemplate
  system=@{provider_template=$providerTemplate}
  jump_host=@{enabled=$false}
}
Write-Json $profile (Join-Path $StateRoot 'hpc-client-profile.json')
& (Join-Path $PSScriptRoot 'lab-status.ps1')
$statusExit = $LASTEXITCODE
if ($statusExit -ne 0) { throw "LOCAL_REAL health check failed with exit code $statusExit" }