. (Join-Path $PSScriptRoot 'lab-common.ps1')
$controller = Get-Node login-control01
Invoke-LabSsh $controller.ip "squeue -h -o '%i' | xargs -r scancel; sudo rm -f /srv/hpc/project/local-real-proof; sudo scontrol update NodeName=compute01,compute02 State=RESUME" | Out-Null
Remove-Item (Join-Path $EvidenceRoot 'LOCAL_REAL_TEST.json') -Force -ErrorAction SilentlyContinue
& (Join-Path $PSScriptRoot 'lab-status.ps1')
