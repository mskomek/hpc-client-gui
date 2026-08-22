<#
.SYNOPSIS
    Prune GitHub Actions run history, keeping only the newest runs.

.DESCRIPTION
    Lists workflow runs via the gh CLI newest-first and deletes everything
    beyond the newest N. Dry-run is the default; pass -Apply to delete.
    Published Releases are unaffected: release assets live under Releases,
    not in Actions run history.

.PARAMETER Keep
    How many of the newest runs to keep across all workflows (default 1).

.PARAMETER Workflow
    Optional workflow name filter (e.g. "Release Build") applied before
    keeping/deleting.

.PARAMETER Apply
    Actually delete. Without this switch the script only prints its plan.

.EXAMPLE
    pwsh scripts/prune-action-runs.ps1                 # show plan
    pwsh scripts/prune-action-runs.ps1 -Apply          # keep newest 1
    pwsh scripts/prune-action-runs.ps1 -Keep 5 -Apply  # keep newest 5
#>

[CmdletBinding()]
param(
    [int]$Keep = 1,
    [string]$Workflow = '',
    [switch]$Apply
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

if ($Keep -lt 0) { throw "-Keep must be >= 0" }

$listArgs = @('run', 'list', '--limit', '1000', '--json',
    'databaseId,workflowName,status,createdAt')
if ($Workflow) { $listArgs += @('--workflow', $Workflow) }

$runs = gh @listArgs | ConvertFrom-Json
if (-not $runs) { Write-Host 'No workflow runs found.'; exit 0 }

$newestFirst = $runs |
    Sort-Object -Property @{ Expression = { [datetime]$_.createdAt } } -Descending |
    ForEach-Object {
        $conclusion = $_.PSObject.Properties['conclusion']
        [pscustomobject]@{
            databaseId   = [string]$_.databaseId
            workflowName = $_.workflowName
            result       = $(if ($conclusion) { $conclusion.Value } else { $_.status })
            createdAt    = $_.createdAt
        }
    }

$keepIds = @{}
foreach ($r in ($newestFirst | Select-Object -First $Keep)) { $keepIds[[string]$r.databaseId] = $true }

$victims = @($newestFirst | Where-Object { -not $keepIds.ContainsKey([string]$_.databaseId) })

Write-Host ("Total runs: {0} | keeping: {1} | deleting: {2}" -f $newestFirst.Count, $keepIds.Count, $victims.Count)
foreach ($r in ($newestFirst | Select-Object -First $Keep)) {
    Write-Host ("  KEEP {0}  {1}  {2}  {3}" -f $r.databaseId, $r.workflowName, $r.result, $r.createdAt)
}
if (-not $Apply) {
    Write-Host 'Dry run only. Re-run with -Apply to delete.' -ForegroundColor Yellow
    foreach ($r in $victims) { Write-Host ("  DEL  {0}  {1}  {2}" -f $r.databaseId, $r.workflowName, $r.result) }
    exit 0
}

$deleted = 0; $failed = 0
foreach ($r in $victims) {
    try {
        gh api -X DELETE "repos/{owner}/{repo}/actions/runs/$($r.databaseId)" | Out-Null
        if ($LASTEXITCODE -ne 0) { throw "gh api exit $LASTEXITCODE" }
        $deleted++
        Write-Host ("  DEL  {0}  {1}  {2}" -f $r.databaseId, $r.workflowName, $r.result)
    } catch {
        $failed++
        Write-Warning ("delete failed for run {0}: {1}" -f $r.databaseId, $_.Exception.Message)
    }
    Start-Sleep -Milliseconds 300   # stay friendly to the API rate limit
}
Write-Host ("Deleted {0}, failed {1}." -f $deleted, $failed)
exit ($(if ($failed) { 1 } else { 0 }))
