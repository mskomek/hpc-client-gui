param([Parameter(Mandatory=$true)][ValidateSet('nested-loop','yield')][string]$Variant)
$ErrorActionPreference='Stop'
$taskName="HPC_GUI_R14CONT_$($Variant.ToUpper().Replace('-','_'))_20261118"
$work=Join-Path $env:LOCALAPPDATA 'Temp\hpc-client-gui-r14-native-crash-20261118'
$dump=Join-Path $work 'wer-dumps'
$runner=Join-Path $work 'run-variant.ps1'
$reg='HKCU:\Software\Microsoft\Windows\Windows Error Reporting\LocalDumps\python.exe'
New-Item -ItemType Directory -Path $dump -Force | Out-Null
New-Item -Path $reg -Force | Out-Null
New-ItemProperty -Path $reg -Name DumpFolder -Value $dump -PropertyType ExpandString -Force | Out-Null
New-ItemProperty -Path $reg -Name DumpType -Value 1 -PropertyType DWord -Force | Out-Null
New-ItemProperty -Path $reg -Name DumpCount -Value 10 -PropertyType DWord -Force | Out-Null
$old=Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if($old){if($old.State.ToString() -ne 'Ready'){throw "owned task unexpectedly active: $($old.State)"};Unregister-ScheduledTask -TaskName $taskName -Confirm:$false}
$action=New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$runner`" -Variant $Variant -Runs 5"
$principal=New-ScheduledTaskPrincipal -UserId 'home' -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Action $action -Principal $principal -Description 'R14 owned native crash diagnostic variant; five isolated test processes' | Out-Null
$started=[DateTime]::UtcNow
Start-ScheduledTask -TaskName $taskName
$deadline=[DateTime]::UtcNow.AddMinutes(5)
do{
  Start-Sleep -Seconds 1
  $info=Get-ScheduledTaskInfo -TaskName $taskName
  $task=Get-ScheduledTask -TaskName $taskName
  $state=$task.State.ToString()
}while(([DateTime]::UtcNow -lt $deadline) -and ($state -ne 'Ready' -or $info.LastRunTime.ToUniversalTime() -lt $started.AddSeconds(-2)))
[pscustomobject]@{Task=$taskName;State=$state;LastRunUtc=$info.LastRunTime.ToUniversalTime().ToString('o');LastTaskResult=$info.LastTaskResult;DumpCount=(Get-ChildItem $dump -File -ErrorAction SilentlyContinue|Measure-Object).Count;Results=@(Get-ChildItem $work -Filter "$Variant-*.result.json" -File|Select-Object -ExpandProperty Name)}|ConvertTo-Json -Depth 4

