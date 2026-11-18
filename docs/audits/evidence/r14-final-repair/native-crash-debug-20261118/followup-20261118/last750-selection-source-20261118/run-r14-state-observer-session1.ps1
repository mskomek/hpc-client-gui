$ErrorActionPreference='Stop'
$root='C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo'
$py=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
$runner='C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\run-r14-state-observer.py'
Set-Location $root
$started=[DateTime]::UtcNow
$p=Start-Process -FilePath $py -ArgumentList ('"'+$runner+'"') -PassThru -Wait -WindowStyle Hidden
[ordered]@{group='r14_state_observer';wrapper_session_id=(Get-Process -Id $PID).SessionId;python_exit=$p.ExitCode;started_utc=$started.ToString('o');ended_utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json -Compress|Set-Content -LiteralPath (Join-Path $root '.tmp\debug-r14\r14-state-observer-task.result.json') -Encoding utf8
if($p.ExitCode -ne 0){exit $p.ExitCode}

