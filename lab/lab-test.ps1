. (Join-Path $PSScriptRoot 'lab-common.ps1')
Ensure-Dirs
$controller = Get-Node login-control01; $results = [ordered]@{}
$results.ssh = Invoke-LabSshCapture $controller.ip 'id -un; hostname; printf "pty=%s\n" "$([ -t 0 ] && echo yes || echo no)"' -Pty
$keyProbes = @($Config.nodes | ForEach-Object { Invoke-LabSshCapture $_.ip 'test "$(id -un)" = hpctest && test "$HOME" = /srv/hpc/home/hpctest && test "$(stat -c %u:%g:%a "$HOME/.ssh")" = "$(id -u hpctest):$(id -g hpctest):700" && test "$(stat -c %u:%g:%a "$HOME/.ssh/authorized_keys")" = "$(id -u hpctest):$(id -g hpctest):600"' })
$results.ssh_key_login = $keyProbes
$results.ssh_key_login_ok = (@($keyProbes | Where-Object exit_code -ne 0).Count -eq 0)
$pathProbes = @($Config.nodes | ForEach-Object { Invoke-LabSshCapture $_.ip 'test -d /srv/hpc/home && test -d /srv/hpc/scratch && test -d /srv/hpc/project && printf "home=/srv/hpc/home scratch=/srv/hpc/scratch project=/srv/hpc/project\n"' })
$results.canonical_paths = $pathProbes
$results.canonical_paths_same = (@($pathProbes | ForEach-Object { $_.output.Trim() } | Select-Object -Unique).Count -eq 1)
$results.canonical_paths_ok = (@($pathProbes | Where-Object exit_code -ne 0).Count -eq 0) -and $results.canonical_paths_same
$identityProbes = @($Config.nodes | ForEach-Object { Invoke-LabSshCapture $_.ip 'printf "%s|%s:%s|%s:%s\n" "$HOME" "$(id -u hpctest)" "$(id -g hpctest)" "$(id -u slurm)" "$(id -g slurm)"' })
$results.identity = $identityProbes
$results.identity_same = (@($identityProbes | ForEach-Object { $_.output.Trim() } | Select-Object -Unique).Count -eq 1)
$results.identity_ok = (@($identityProbes | Where-Object exit_code -ne 0).Count -eq 0) -and $results.identity_same
$sftpPath = Join-Path $StateRoot 'hostname.copy'; $sftpBatchPath = $sftpPath -replace '\','/'; $sftpOutput = ("get /etc/hostname $sftpBatchPath`n" | & sftp -q -b - -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i (Get-KeyPath) "$($Config.ssh.user)@$($controller.ip)" 2>&1); $results.sftp_exit=$LASTEXITCODE; $results.sftp_file_exists=Test-Path $sftpPath; $results.sftp_content_match=$false; if ($results.sftp_file_exists) { $remoteHostname = Invoke-LabSshCapture $controller.ip 'cat /etc/hostname'; $results.sftp_content_match=((Get-Content $sftpPath -Raw).Trim() -eq $remoteHostname.output.Trim()) }; $results.sftp_output=($sftpOutput -join "`n")
$results.munge = Invoke-LabSshCapture $controller.ip 'munge -n | unmunge'
$results.srun = Invoke-LabSshCapture $controller.ip 'srun -N2 -n2 hostname | sort -u'
$results.sinfo = Invoke-LabSshCapture $controller.ip 'sinfo -h -o "%N %T"'
$results.squeue = Invoke-LabSshCapture $controller.ip 'squeue -h -o "%i %T %j"'
$results.scontrol = Invoke-LabSshCapture $controller.ip 'scontrol show nodes compute[01-02]'
$results.sbatch = Invoke-LabSshCapture $controller.ip 'printf "#!/bin/sh\necho LOCAL_REAL_SBATCH\nsleep 2\n" | sbatch --parsable --wait'
$job = ($results.sbatch.output -split '\s+')[0]; $results.sacct = Invoke-LabSshCapture $controller.ip "sacct -n -P -j $job --format=JobIDRaw,State,ExitCode"
$results.shared_home_job = Invoke-LabSshCapture $controller.ip 'cd /srv/hpc/home/hpctest && rm -rf .local-real-job && mkdir .local-real-job && srun --nodes=2 --ntasks=2 --ntasks-per-node=1 --chdir=/srv/hpc/home/hpctest/.local-real-job /bin/sh -c ''printf "%s %s\n" "$(hostname)" "$PWD" >> /srv/hpc/home/hpctest/.local-real-job/result'' && test "$(wc -l < .local-real-job/result)" -eq 2 && test "$(grep -c "^compute01 /srv/hpc/home/hpctest/.local-real-job$" .local-real-job/result)" -eq 1 && test "$(grep -c "^compute02 /srv/hpc/home/hpctest/.local-real-job$" .local-real-job/result)" -eq 1'
$results.shared_fs = Invoke-LabSshCapture $controller.ip 'touch /srv/hpc/project/local-real-proof && test -f /srv/hpc/project/local-real-proof'
$pass = ($results.GetEnumerator() | ForEach-Object { if ($_.Value -is [bool]) {$_.Value} elseif ($_.Value -is [int]) {$_.Value -eq 0} elseif ($_.Value.PSObject.Properties['exit_code']) {$_.Value.exit_code -eq 0} else {$true} }) -notcontains $false
$report = [pscustomobject]@{ status=if ($pass) {'LOCAL_REAL_READY'} else {'FAIL'}; tests=$results; generated_at=(Get-Date).ToUniversalTime().ToString('o'); note='Laboratory evidence only; not W22 PASS.' }
Write-Json $report (Join-Path $EvidenceRoot 'LOCAL_REAL_TEST.json'); $report | ConvertTo-Json -Depth 12
if (-not $pass) { exit 3 }
