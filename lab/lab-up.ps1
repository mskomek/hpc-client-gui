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
foreach ($node in $Config.nodes) {
  $vmPath = Join-Path $StateRoot $node.name; New-Item -ItemType Directory -Force $vmPath | Out-Null
  $disk = Join-Path $vmPath "$($node.name).vhdx"
  if (-not (Test-Path $disk)) { New-VHD -Path $disk -ParentPath $baseVhdx -Differencing | Out-Null }
  $seed = Join-Path $vmPath seed; New-Item -ItemType Directory -Force $seed | Out-Null
  $hosts = ($Config.nodes | ForEach-Object { "      $($_.ip) $($_.name)" }) -join "`n"
  $userData = @('#cloud-config','users:',"  - name: $($Config.ssh.user)",'    sudo: ALL=(ALL) NOPASSWD:ALL','    shell: /bin/bash','    ssh_authorized_keys:',"      - $public",'  - name: hpctest','    sudo: ALL=(ALL) NOPASSWD:ALL','    shell: /bin/bash','    ssh_authorized_keys:',"      - $public",'ssh_pwauth: false','write_files:','  - path: /etc/hosts','    append: true','    content: |',$hosts,'runcmd:','  - systemctl enable --now ssh')
  $userData | Set-Content (Join-Path $seed 'user-data') -Encoding ascii
  @("instance-id: $($node.name)","local-hostname: $($node.name)") | Set-Content (Join-Path $seed 'meta-data') -Encoding ascii
  @('version: 2','ethernets:','  id0:','    match:','      name: "e*"','    set-name: ens160',"    addresses: [$($node.ip)/24]",'    routes:','      - to: default',"        via: $($Config.gateway)",'    nameservers:','      addresses: [1.1.1.1, 8.8.8.8]') | Set-Content (Join-Path $seed 'network-config') -Encoding ascii
  $seedWsl = (wsl.exe wslpath -a ((Resolve-Path $seed).Path -replace '\','/')).Trim(); $iso = Join-Path $vmPath 'seed.iso'; $isoWsl = (wsl.exe wslpath -a ((Resolve-Path $vmPath).Path -replace '\','/')).Trim() + '/seed.iso'
  Invoke-Checked wsl.exe @('bash','-lc',"genisoimage -output '$isoWsl' -volid cidata -joliet -rock '$seedWsl'")
  if (-not (Get-VM -Name $node.name -ErrorAction SilentlyContinue)) { New-VM -Name $node.name -Generation 2 -MemoryStartupBytes ($node.memory_mb * 1MB) -VHDPath $disk -SwitchName $Config.switch | Out-Null; Add-VMDvdDrive -VMName $node.name -Path $iso | Out-Null; Set-VM -Name $node.name -AutomaticStopAction ShutDown }
  if ((Get-VM -Name $node.name).State -ne 'Running') { Start-VM $node.name | Out-Null }
}
foreach ($node in $Config.nodes) { $ready = $false; for ($i=0; $i -lt 60; $i++) { if (Test-NetConnection $node.ip -Port 22 -InformationLevel Quiet) { $ready = $true; break }; Start-Sleep 2 }; if (-not $ready) { throw "SSH did not become ready: $($node.name)" } }
function Send-Script($host,$path,$env='') { $b64 = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes((Get-Content $path -Raw))); Invoke-LabSsh $host "echo '$b64' | base64 -d | sudo $env bash -s" | Out-Null }
$dbPassword = [guid]::NewGuid().ToString('N'); Send-Script (Get-Node login-control01).ip (Join-Path $PSScriptRoot 'provision/controller.sh') "env SLURM_DB_PASSWORD=$dbPassword"
foreach ($node in @($Config.nodes | Where-Object role -eq 'compute')) { Send-Script $node.ip (Join-Path $PSScriptRoot 'provision/compute.sh') }
$munge = Invoke-LabSshCapture (Get-Node login-control01).ip 'sudo base64 -w0 /etc/munge/munge.key'
foreach ($node in @($Config.nodes | Where-Object role -eq 'compute')) { Invoke-LabSsh $node.ip "echo '$($munge.output)' | base64 -d | sudo tee /etc/munge/munge.key >/dev/null; sudo chown munge:munge /etc/munge/munge.key; sudo chmod 400 /etc/munge/munge.key; sudo systemctl restart munge slurmd" | Out-Null }
$controller = Get-Node login-control01
$profile = [ordered]@{ name='LOCAL_REAL'; host=$controller.ip; port=22; username='hpctest'; key_path=(Get-KeyPath); host_key_policy='accept-new'; system=@{slurm=$true}; provider_template=@{name='generic-local-real'; storage=@(@{id='home';path_template='/srv/hpc/home/{user}'},@{id='scratch';path_template='/srv/hpc/scratch/{user}'},@{id='project';path_template='/srv/hpc/project'})} }
Write-Json $profile (Join-Path $StateRoot 'hpc-client-profile.json')
& (Join-Path $PSScriptRoot 'lab-status.ps1')
