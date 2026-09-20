. (Join-Path $PSScriptRoot 'lab-common.ps1')
Ensure-Dirs
$controller = Get-Node login-control01; $results = [ordered]@{}
$results.ssh = Invoke-LabSshCapture $controller.ip 'id -un; hostname; printf "pty=%s\n" "$([ -t 0 ] && echo yes || echo no)"' -Pty
$results.sftp = & sftp -q -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL -i (Get-KeyPath) "$($Config.ssh.user)@$($controller.ip):/etc/hostname" (Join-Path $StateRoot hostname.copy) 2>&1; $results.sftp_exit=$LASTEXITCODE
$results.munge = Invoke-LabSshCapture $controller.ip 'munge -n | unmunge | grep -q STATUS:0'
$results.srun = Invoke-LabSshCapture $controller.ip 'srun -N2 -n2 hostname | sort -u'
$results.sinfo = Invoke-LabSshCapture $controller.ip 'sinfo -h -o "%N %T"'
$results.squeue = Invoke-LabSshCapture $controller.ip 'squeue -h -o "%i %T %j"'
$results.scontrol = Invoke-LabSshCapture $controller.ip 'scontrol show nodes compute01 compute02'
$results.sbatch = Invoke-LabSshCapture $controller.ip 'printf "#!/bin/sh\necho LOCAL_REAL_SBATCH\nsleep 2\n" | sbatch --parsable --wait'
$job = ($results.sbatch.output -split '\s+')[0]; $results.sacct = Invoke-LabSshCapture $controller.ip "sacct -n -P -j $job --format=JobIDRaw,State,ExitCode"
$results.shared_fs = Invoke-LabSshCapture $controller.ip 'touch /srv/hpc/project/local-real-proof && test -f /srv/hpc/project/local-real-proof'
$pass = ($results.GetEnumerator() | ForEach-Object { if ($_.Value -is [int]) {$_.Value -eq 0} elseif ($_.Value.PSObject.Properties['exit_code']) {$_.Value.exit_code -eq 0} else {$true} }) -notcontains $false
$report = [pscustomobject]@{ status=if ($pass) {'LOCAL_REAL_READY'} else {'FAIL'}; tests=$results; generated_at=(Get-Date).ToUniversalTime().ToString('o'); note='Laboratory evidence only; not W22 PASS.' }
Write-Json $report (Join-Path $EvidenceRoot 'LOCAL_REAL_TEST.json'); $report | ConvertTo-Json -Depth 12
if (-not $pass) { exit 3 }
