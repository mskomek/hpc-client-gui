. (Join-Path $PSScriptRoot 'lab-common.ps1')
Ensure-Dirs
$controller = Get-ControllerNode
$computeNodes = @(Get-ComputeNodes)
$results = [ordered]@{}
$results.sftp_exit = 255
$results.sftp_put_exit = 255


# PTY evidence is intentionally a direct OpenSSH probe instead of going
# through Invoke-LabSshCapture. That helper transports arbitrary scripts by
# piping decoded bytes into bash -s, which changes the shell's fd topology and
# is therefore the wrong place to prove terminal allocation. "tty" is the
# direct POSIX assertion: it succeeds only when the remote process owns a TTY
# and prints the actual /dev/pts/* device.
$ptyStdoutPath = [IO.Path]::GetTempFileName()
$ptyStderrPath = [IO.Path]::GetTempFileName()
$ptyCode = 255
$ptyStdout = ''
$ptyStderr = ''
try {
  $previousEap = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $ptyArgs = @('-tt') + @(Get-LabSshCommonOptions) + @(
      '-p',[string]$Config.ssh.port,
      '-i',(Get-KeyPath),
      "$($Config.ssh.user)@$($controller.ip)",
      'tty && id -un && hostname'
    )
    & ssh @ptyArgs 1> $ptyStdoutPath 2> $ptyStderrPath
    $ptyCode = $LASTEXITCODE
  } finally {
    $ErrorActionPreference = $previousEap
  }
  if (Test-Path $ptyStdoutPath) {
    $raw = Get-Content $ptyStdoutPath -Raw -ErrorAction SilentlyContinue
    if ($null -ne $raw) { $ptyStdout = [string]$raw }
  }
  if (Test-Path $ptyStderrPath) {
    $raw = Get-Content $ptyStderrPath -Raw -ErrorAction SilentlyContinue
    if ($null -ne $raw) { $ptyStderr = [string]$raw }
  }
} finally {
  Remove-Item $ptyStdoutPath,$ptyStderrPath -Force -ErrorAction SilentlyContinue
}
$results.ssh = [pscustomobject]@{
  exit_code = $ptyCode
  output = ([string]$ptyStdout).TrimEnd()
  stderr = ([string]$ptyStderr).TrimEnd()
}
$sshLines = @($results.ssh.output -split "`r?`n" | ForEach-Object { $_.Trim() } | Where-Object { $_ })
$ptyDevice = @($sshLines | Where-Object { $_ -match '^/dev/(pts/\d+|tty\S*)$' } | Select-Object -First 1)
$results.ssh_pty_device = if ($ptyDevice.Count) { [string]$ptyDevice[0] } else { '' }
$results.ssh_pty_ok = (
  $results.ssh.exit_code -eq 0 -and
  -not [string]::IsNullOrWhiteSpace($results.ssh_pty_device) -and
  $sshLines -contains 'hpctest' -and
  $sshLines -contains ([string]$controller.name)
)


$knownHosts = Get-KnownHostsPath
$hostKeyEntries = [ordered]@{}
foreach ($node in $Config.nodes) {
  $lookup = if ([int]$Config.ssh.port -eq 22) { [string]$node.ip } else { "[$($node.ip)]:$($Config.ssh.port)" }
  $output = & ssh-keygen -F $lookup -f $knownHosts 2>$null
  $hostKeyEntries[[string]$node.name] = ($LASTEXITCODE -eq 0 -and -not [string]::IsNullOrWhiteSpace(($output | Out-String)))
}
$results.host_keys = $hostKeyEntries
$results.host_keys_pinned_ok = (@($hostKeyEntries.GetEnumerator() | Where-Object { -not [bool]$_.Value }).Count -eq 0)


$keyProbes = @($Config.nodes | ForEach-Object {
  Invoke-LabSshCapture $_.ip 'test "$(id -un)" = hpctest && test "$HOME" = /home/hpctest && mountpoint -q "$HOME" && test "$HOME/.ssh/authorized_keys" -ef /srv/hpc/home/hpctest/.ssh/authorized_keys && test "$(stat -c %u:%g:%a "$HOME/.ssh")" = "$(id -u hpctest):$(id -g hpctest):700" && test "$(stat -c %u:%g:%a "$HOME/.ssh/authorized_keys")" = "$(id -u hpctest):$(id -g hpctest):600"'
})
$results.ssh_key_login = $keyProbes
$results.ssh_key_login_ok = (@($keyProbes | Where-Object exit_code -ne 0).Count -eq 0)


$pathProbes = @($Config.nodes | ForEach-Object {
  Invoke-LabSshCapture $_.ip 'test -d /srv/hpc/home && test -d /srv/hpc/scratch && test -d /srv/hpc/project && printf "home=/srv/hpc/home scratch=/srv/hpc/scratch project=/srv/hpc/project\n"'
})
$results.canonical_paths = $pathProbes
$results.canonical_paths_same = (@($pathProbes | ForEach-Object { $_.output.Trim() } | Select-Object -Unique).Count -eq 1)
$results.canonical_paths_ok = (@($pathProbes | Where-Object exit_code -ne 0).Count -eq 0) -and $results.canonical_paths_same


$identityProbes = @($Config.nodes | ForEach-Object {
  Invoke-LabSshCapture $_.ip 'printf "%s\n" "$HOME"; id -u hpctest; id -g hpctest; id -u slurm; id -g slurm'
})
$results.identity = $identityProbes
$results.identity_same = (@($identityProbes | ForEach-Object { $_.output.Trim() } | Select-Object -Unique).Count -eq 1)
$results.identity_ok = (@($identityProbes | Where-Object exit_code -ne 0).Count -eq 0) -and $results.identity_same


$storageProbes = @($Config.nodes | ForEach-Object {
  Invoke-LabSshCapture $_.ip 'set -eu; for path in /srv/hpc/home/hpctest /srv/hpc/scratch/hpctest /srv/hpc/project/hpctest; do test -d "$path"; file="$path/.local-real-storage-roundtrip"; printf LOCAL_REAL_STORAGE > "$file"; test "$(cat "$file")" = LOCAL_REAL_STORAGE; rm -f "$file"; test ! -e "$file"; done; printf "home=/srv/hpc/home/hpctest scratch=/srv/hpc/scratch/hpctest project=/srv/hpc/project/hpctest\n"'
})
$results.storage = $storageProbes
$results.storage_same = (@($storageProbes | ForEach-Object { $_.output.Trim() } | Select-Object -Unique).Count -eq 1)
$results.storage_ok = (@($storageProbes | Where-Object exit_code -ne 0).Count -eq 0) -and $results.storage_same


$sftpPath = Join-Path $StateRoot 'hostname.copy'
Remove-Item $sftpPath -Force -ErrorAction SilentlyContinue
$sftpBatch = [IO.Path]::GetTempFileName()
$sftpStdout = [IO.Path]::GetTempFileName()
$sftpStderr = [IO.Path]::GetTempFileName()
try {
  $sftpBatchPath = $sftpPath.Replace('\','/')
  ('get /etc/hostname "{0}"' -f $sftpBatchPath) | Set-Content $sftpBatch -Encoding ascii
  $previousEap = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $sftpOptions = @(Get-LabSshCommonOptions)
    & sftp @sftpOptions -q -b $sftpBatch -P $Config.ssh.port -i (Get-KeyPath) "$($Config.ssh.user)@$($controller.ip)" 1> $sftpStdout 2> $sftpStderr
    $results.sftp_exit = $LASTEXITCODE
  } finally { $ErrorActionPreference = $previousEap }
  $results.sftp_output = if (Test-Path $sftpStdout) { [string](Get-Content $sftpStdout -Raw -ErrorAction SilentlyContinue) } else { '' }
  $results.sftp_stderr = if (Test-Path $sftpStderr) { [string](Get-Content $sftpStderr -Raw -ErrorAction SilentlyContinue) } else { '' }
} finally {
  Remove-Item $sftpBatch,$sftpStdout,$sftpStderr -Force -ErrorAction SilentlyContinue
}
$results.sftp_file_exists = Test-Path $sftpPath
$results.sftp_content_match = $false
if ($results.sftp_file_exists) {
  $remoteHostname = Invoke-LabSshCapture $controller.ip 'cat /etc/hostname'
  $results.sftp_content_match = ($remoteHostname.exit_code -eq 0 -and (Get-Content $sftpPath -Raw).Trim() -eq $remoteHostname.output.Trim())
}


$sftpUploadPath = Join-Path $StateRoot 'sftp-upload.txt'
$sftpUploadContent = 'LOCAL_REAL_SFTP_UPLOAD_şğüıçö'
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[IO.File]::WriteAllText($sftpUploadPath, $sftpUploadContent, $utf8NoBom)
$sftpUploadHash = (Get-FileHash -Algorithm SHA256 $sftpUploadPath).Hash.ToLowerInvariant()
$sftpPutBatch = [IO.Path]::GetTempFileName()
$sftpPutOut = [IO.Path]::GetTempFileName()
$sftpPutErr = [IO.Path]::GetTempFileName()
try {
  $putLocal = $sftpUploadPath.Replace('\','/')
  @('put "{0}" /srv/hpc/scratch/hpctest/sftp-upload.txt' -f $putLocal,'bye') | Set-Content $sftpPutBatch -Encoding ascii
  $previousEap = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'Continue'
    $sftpOptions = @(Get-LabSshCommonOptions)
    & sftp @sftpOptions -q -b $sftpPutBatch -P $Config.ssh.port -i (Get-KeyPath) "$($Config.ssh.user)@$($controller.ip)" 1> $sftpPutOut 2> $sftpPutErr
    $results.sftp_put_exit = $LASTEXITCODE
  } finally { $ErrorActionPreference = $previousEap }
  $remoteUpload = Invoke-LabSshCapture $controller.ip 'sha256sum /srv/hpc/scratch/hpctest/sftp-upload.txt | awk ''{print $1}''; rm -f /srv/hpc/scratch/hpctest/sftp-upload.txt'
  $results.sftp_put_content_match = ($results.sftp_put_exit -eq 0 -and $remoteUpload.exit_code -eq 0 -and $remoteUpload.output.Trim().ToLowerInvariant() -eq $sftpUploadHash)
} finally {
  Remove-Item $sftpPutBatch,$sftpPutOut,$sftpPutErr,$sftpUploadPath -Force -ErrorAction SilentlyContinue
}


$results.munge = Invoke-LabSshCapture $controller.ip 'munge -n | unmunge >/dev/null'
$taskCount = $computeNodes.Count
$results.srun = Invoke-LabSshCapture $controller.ip ("srun --nodes={0} --ntasks={0} --ntasks-per-node=1 hostname | sort -u" -f $taskCount)
$expectedComputeNames = @($computeNodes | ForEach-Object { [string]$_.name } | Sort-Object)
$actualSrunNames = @($results.srun.output -split "`r?`n" | Where-Object { $_ } | Sort-Object)
$results.srun_nodes_ok = ($results.srun.exit_code -eq 0 -and (($actualSrunNames -join '|') -eq ($expectedComputeNames -join '|')))


$results.sinfo = Invoke-LabSshCapture $controller.ip 'sinfo -h -N -o "%N|%t"'
$stateMap = @{}
foreach ($line in @($results.sinfo.output -split "`r?`n")) { if ($line -match '^([^|]+)\|(.+)$') { $stateMap[$matches[1].Trim()] = $matches[2].Trim() } }
$results.sinfo_nodes_ok = $results.sinfo.exit_code -eq 0
foreach ($name in $expectedComputeNames) { if (-not $stateMap.ContainsKey($name) -or $stateMap[$name] -notin @('idle','mix','alloc')) { $results.sinfo_nodes_ok = $false } }


$results.squeue = Invoke-LabSshCapture $controller.ip 'squeue -h -o "%i %T %j"'
$nodeList = (@($computeNodes | ForEach-Object { $_.name }) -join ',')
$results.scontrol = Invoke-LabSshCapture $controller.ip ("scontrol show node {0}" -f $nodeList)


$results.sbatch = Invoke-LabSshCapture $controller.ip 'printf "#!/bin/sh\necho LOCAL_REAL_SBATCH\nsleep 2\n" | sbatch --parsable --wait'
$job = if ($results.sbatch.exit_code -eq 0) { (($results.sbatch.output -split '\s+')[0]).Trim() } else { '' }
if ($job) { $results.sacct = Invoke-LabSshCapture $controller.ip "sacct -n -P -j $job --format=JobIDRaw,State,ExitCode" }
else { $results.sacct = [pscustomobject]@{ exit_code=1; output=''; stderr='sbatch did not return a job id' } }
$results.sacct_completed_ok = ($results.sacct.exit_code -eq 0 -and $results.sacct.output -match 'COMPLETED')


$results.shared_home_job = Invoke-LabSshCapture $controller.ip (('cd /srv/hpc/home/hpctest && rm -rf .local-real-job && mkdir .local-real-job && srun --nodes={0} --ntasks={0} --ntasks-per-node=1 --chdir=/srv/hpc/home/hpctest/.local-real-job /bin/sh -c ''printf "%s %s\n" "$(hostname)" "$PWD"'' | sort > /srv/hpc/home/hpctest/.local-real-job/result && cat /srv/hpc/home/hpctest/.local-real-job/result' -f $taskCount))
$expectedJobLines = @($expectedComputeNames | ForEach-Object { "$_ /srv/hpc/home/hpctest/.local-real-job" })
$actualJobLines = @($results.shared_home_job.output -split "`r?`n" | Where-Object { $_ } | Sort-Object)
$results.shared_home_job_ok = ($results.shared_home_job.exit_code -eq 0 -and (($actualJobLines -join '|') -eq (($expectedJobLines | Sort-Object) -join '|')))


$permissionDeniedProbe = Invoke-LabSshCapture $controller.ip 'sudo sh -c "printf LOCAL_REAL_ROOT_ONLY > /srv/hpc/project/root-only && chmod 600 /srv/hpc/project/root-only"; cat /srv/hpc/project/root-only'
$results.permission_denied = [pscustomobject]@{ observed_exit_code=$permissionDeniedProbe.exit_code; output=$permissionDeniedProbe.output; stderr=$permissionDeniedProbe.stderr }
$results.permission_denied_ok = ($permissionDeniedProbe.exit_code -ne 0)
Invoke-LabSshCapture $controller.ip 'sudo rm -f /srv/hpc/project/root-only' | Out-Null


$results.cancel_submit = Invoke-LabSshCapture $controller.ip 'sbatch --parsable --wrap="sleep 120"'
$cancelJob = if ($results.cancel_submit.exit_code -eq 0) { (($results.cancel_submit.output -split '\s+')[0]).Trim() } else { '' }
$results.scancel_ok = $false
if ($cancelJob) {
  $cancelResult = Invoke-LabSshCapture $controller.ip "scancel $cancelJob"
  $results.scancel = $cancelResult
  for ($i=0; $i -lt 20; $i++) {
    $cancelState = Invoke-LabSshCapture $controller.ip "sacct -n -X -j $cancelJob --format=State -P"
    if ($cancelState.exit_code -eq 0 -and $cancelState.output -match 'CANCELLED') { $results.scancel_ok = $true; break }
    Start-Sleep 1
  }
} else {
  $results.scancel = [pscustomobject]@{ exit_code=1; output=''; stderr='cancel test job was not submitted' }
}


$requiredChecks = [ordered]@{
  ssh_pty = [bool]$results.ssh_pty_ok
  host_keys_pinned_all_nodes = [bool]$results.host_keys_pinned_ok
  ssh_key_login_all_nodes = [bool]$results.ssh_key_login_ok
  canonical_paths = [bool]$results.canonical_paths_ok
  identity_consistency = [bool]$results.identity_ok
  storage_roundtrip = [bool]$results.storage_ok
  sftp_download_exit = ([int]$results.sftp_exit -eq 0)
  sftp_download_file = [bool]$results.sftp_file_exists
  sftp_download_content = [bool]$results.sftp_content_match
  sftp_upload_exit = ([int]$results.sftp_put_exit -eq 0)
  sftp_upload_content = [bool]$results.sftp_put_content_match
  munge_roundtrip = ($results.munge.exit_code -eq 0)
  srun_two_nodes = [bool]$results.srun_nodes_ok
  sinfo_nodes = [bool]$results.sinfo_nodes_ok
  squeue_command = ($results.squeue.exit_code -eq 0)
  scontrol_command = ($results.scontrol.exit_code -eq 0)
  sbatch_command = ($results.sbatch.exit_code -eq 0 -and -not [string]::IsNullOrWhiteSpace($job))
  sacct_completed = [bool]$results.sacct_completed_ok
  shared_home_compute_job = [bool]$results.shared_home_job_ok
  permission_denied_negative = [bool]$results.permission_denied_ok
  cancel_submit = ($results.cancel_submit.exit_code -eq 0 -and -not [string]::IsNullOrWhiteSpace($cancelJob))
  scancel_command = ($results.scancel.exit_code -eq 0)
  scancel_state = [bool]$results.scancel_ok
}
$failedChecks = @($requiredChecks.GetEnumerator() | Where-Object { -not [bool]$_.Value } | ForEach-Object { [string]$_.Key })
$pass = ($failedChecks.Count -eq 0)
$results.verdict = [pscustomobject]@{ required=$requiredChecks; failed=$failedChecks; required_count=$requiredChecks.Count; failed_count=$failedChecks.Count }


$report = [pscustomobject]@{ status=if ($pass) {'LOCAL_REAL_READY'} else {'FAIL'}; tests=$results; generated_at=(Get-Date).ToUniversalTime().ToString('o'); note='Laboratory evidence only; not W22 PASS.' }
Write-Json $report (Join-Path $EvidenceRoot 'LOCAL_REAL_TEST.json')
$report | ConvertTo-Json -Depth 14
if (-not $pass) { exit 3 }
exit 0