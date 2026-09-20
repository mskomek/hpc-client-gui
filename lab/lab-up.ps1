. (Join-Path $PSScriptRoot 'lab-common.ps1')
Require-Admin; Ensure-Dirs
& (Join-Path $PSScriptRoot 'lab-prereq.ps1'); if ($LASTEXITCODE) { exit $LASTEXITCODE }
if (-not (Test-Path (Get-KeyPath))) { Invoke-Checked ssh-keygen @('-q','-t','ed25519','-N','','-f',(Get-KeyPath)) }
if (-not (Get-VMSwitch -Name $Config.switch -ErrorAction SilentlyContinue)) { New-VMSwitch -Name $Config.switch -SwitchType Internal | Out-Null }
$adapter = Get-NetAdapter | Where-Object { $_.Name -like "vEthernet ($($Config.switch))" } | Select-Object -First 1
if ($adapter -and -not (Get-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $Config.gateway -ErrorAction SilentlyContinue)) { New-NetIPAddress -InterfaceIndex $adapter.ifIndex -IPAddress $Config.gateway -PrefixLength 24 | Out-Null }
if (-not (Get-NetNat -Name 'hpc-lab-nat' -ErrorAction SilentlyContinue)) { New-NetNat -Name 'hpc-lab-nat' -InternalIPInterfaceAddressPrefix $Config.prefix | Out-Null }
$image = Join-Path $StateRoot $Config.image.file; $baseVhdx = Join-Path $StateRoot 'ubuntu-base.vhdx'
if (-not (Test-Path $image)) { Invoke-WebRequest $Config.image.url -OutFile $image }
if (-not (Test-Path $baseVhdx)) { $source = (wsl.exe wslpath -a ((Resolve-Path $image).Path -replace '\','/')).Trim(); $dest = (wsl.exe wslpath -a ((Resolve-Path $StateRoot).Path -replace '\','/')).Trim() + '/ubuntu-base.vhdx'; Invoke-Checked wsl.exe @('bash','-lc',"qemu-img convert -p -O vhdx '$source' '$dest'") }
$public = Get-PublicKey
$computeCpus = @($Config.nodes | Where-Object role -eq 'compute' | Select-Object -ExpandProperty cpus -Unique)
if ($computeCpus.Count -ne 1 -or $computeCpus[0] -lt 1) { throw 'All compute nodes must define the same positive cpus value.' }
foreach ($node in $Config.nodes) {
  $vmPath = Join-Path $StateRoot $node.name; New-Item -ItemType Directory -Force $vmPath | Out-Null
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
  elseif ($diskInfo.Size -gt $diskBytes) { throw "Existing VM disk exceeds configured disk_gb; use lab-reset/lab-down before reducing it: $($node.name)" }
  $seed = Join-Path $vmPath seed; New-Item -ItemType Directory -Force $seed | Out-Null
  $hosts = ($Config.nodes | ForEach-Object { "      $($_.ip) $($_.name)" }) -join "`n"
  $userData = @('#cloud-config','users:',"  - name: $($Config.ssh.user)",'    sudo: ALL=(ALL) NOPASSWD:ALL','    shell: /bin/bash','    ssh_authorized_keys:',"      - $public",'ssh_pwauth: false','write_files:','  - path: /etc/hosts','    append: true','    content: |',$hosts,'runcmd:','  - systemctl enable --now ssh')
  $userData | Set-Content (Join-Path $seed 'user-data') -Encoding ascii
  @("instance-id: $($node.name)","local-hostname: $($node.name)") | Set-Content (Join-Path $seed 'meta-data') -Encoding ascii
  @('version: 2','ethernets:','  id0:','    match:','      name: "e*"','    set-name: ens160',"    addresses: [$($node.ip)/24]",'    routes:','      - to: default',"        via: $($Config.gateway)",'    nameservers:','      addresses: [1.1.1.1, 8.8.8.8]') | Set-Content (Join-Path $seed 'network-config') -Encoding ascii
  $seedWsl = (wsl.exe wslpath -a ((Resolve-Path $seed).Path -replace '\','/')).Trim(); $iso = Join-Path $vmPath 'seed.iso'; $isoWsl = (wsl.exe wslpath -a ((Resolve-Path $vmPath).Path -replace '\','/')).Trim() + '/seed.iso'
  Invoke-Checked wsl.exe @('bash','-lc',"genisoimage -output '$isoWsl' -volid cidata -joliet -rock '$seedWsl'")
  if (-not (Get-VM -Name $node.name -ErrorAction SilentlyContinue)) { New-VM -Name $node.name -Generation 2 -MemoryStartupBytes ($node.memory_mb * 1MB) -VHDPath $disk -SwitchName $Config.switch | Out-Null; Add-VMDvdDrive -VMName $node.name -Path $iso | Out-Null; Set-VM -Name $node.name -AutomaticStopAction ShutDown }
  $vm = Get-VM -Name $node.name
  $firmware = Get-VMFirmware -VMName $node.name
  $processor = Get-VMProcessor -VMName $node.name
  $hardwareOk = $firmware.SecureBoot -eq 'On' -and $firmware.SecureBootTemplate -eq 'MicrosoftUEFICertificateAuthority' -and $processor.Count -eq $node.cpus
  if ($vm.State -eq 'Running' -and -not $hardwareOk) {
    Stop-VM -Name $node.name
    for ($wait = 0; $wait -lt 30 -and (Get-VM -Name $node.name).State -ne 'Off'; $wait++) { Start-Sleep 1 }
    if ((Get-VM -Name $node.name).State -ne 'Off') { throw "VM did not stop for required hardware reconfiguration: $($node.name)" }
  }
  if ((Get-VM -Name $node.name).State -ne 'Running') {
    Set-VMFirmware -VMName $node.name -EnableSecureBoot On -SecureBootTemplate 'MicrosoftUEFICertificateAuthority'
    Set-VMProcessor -VMName $node.name -Count $node.cpus
    Start-VM $node.name | Out-Null
  }
}
foreach ($node in $Config.nodes) { $ready = $false; for ($i=0; $i -lt 60; $i++) { if (Test-NetConnection $node.ip -Port 22 -InformationLevel Quiet) { $ready = $true; break }; Start-Sleep 2 }; if (-not $ready) { throw "SSH did not become ready: $($node.name)" } }
function Send-Script($host,$path,$env='') { $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content $path -Raw))); Invoke-LabSsh $host "echo '$b64' | base64 -d | sudo $env bash -s" | Out-Null }
$dbPassword = [guid]::NewGuid().ToString('N'); Send-Script (Get-Node login-control01).ip (Join-Path $PSScriptRoot 'provision/controller.sh') "env SLURM_DB_PASSWORD=$dbPassword SLURM_COMPUTE_CPUS=$($computeCpus[0])"
$identity = Invoke-LabSshCapture (Get-Node login-control01).ip 'printf "%s %s %s %s\n" "$(id -u hpctest)" "$(id -g hpctest)" "$(id -u slurm)" "$(id -g slurm)"'
if ($identity.exit_code -ne 0 -or $identity.output.Trim() -notmatch '^\d+\s+\d+\s+\d+\s+\d+$') { throw 'Controller did not provide canonical user/group IDs' }
$identityIds = $identity.output.Trim() -split '\s+'
$computeEnv = "env HPCTEST_UID=$($identityIds[0]) HPCTEST_GID=$($identityIds[1]) SLURM_UID=$($identityIds[2]) SLURM_GID=$($identityIds[3])"
foreach ($node in @($Config.nodes | Where-Object role -eq 'compute')) { Send-Script $node.ip (Join-Path $PSScriptRoot 'provision/compute.sh') $computeEnv }
$slurmConf = Invoke-LabSshCapture (Get-Node login-control01).ip 'sudo base64 -w0 /etc/slurm/slurm.conf'
if ($slurmConf.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($slurmConf.output)) { throw 'Controller did not provide /etc/slurm/slurm.conf' }
$munge = Invoke-LabSshCapture (Get-Node login-control01).ip 'sudo base64 -w0 /etc/munge/munge.key'
if ($munge.exit_code -ne 0 -or [string]::IsNullOrWhiteSpace($munge.output)) { throw 'Controller did not provide /etc/munge/munge.key' }
foreach ($node in @($Config.nodes | Where-Object role -eq 'compute')) { Invoke-LabSsh $node.ip "echo '$($slurmConf.output)' | base64 -d | sudo install -o root -g root -m 0644 /dev/stdin /etc/slurm/slurm.conf; echo '$($munge.output)' | base64 -d | sudo install -o munge -g munge -m 0400 /dev/stdin /etc/munge/munge.key; sudo systemctl enable --now munge slurmd" | Out-Null }
$controller = Get-Node login-control01
$profile = [ordered]@{ name='LOCAL_REAL'; host=$controller.ip; port=22; username='hpctest'; key_path=(Get-KeyPath); host_key_policy='accept-new'; system=@{slurm=$true}; provider_template=@{name='generic-local-real'; storage=@(@{id='home';path_template='/srv/hpc/home/{user}'},@{id='scratch';path_template='/srv/hpc/scratch/{user}'},@{id='project';path_template='/srv/hpc/project'})} }
Write-Json $profile (Join-Path $StateRoot 'hpc-client-profile.json')
& (Join-Path $PSScriptRoot 'lab-status.ps1')
