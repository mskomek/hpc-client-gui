param([int]$Runs=5)
$ErrorActionPreference='Stop'
$task='HPC_GUI_R14_CLOSEPROBE_20261118'
$work=Join-Path $env:LOCALAPPDATA 'Temp\hpc-client-gui-r14-closeprobe-20261118'
$runner=Join-Path $work 'closeprobe_runner.py'
$root='%USERPROFILE%\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo'
$py=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
New-Item -ItemType Directory -Path $work -Force | Out-Null
$results=@()
for($i=1;$i -le $Runs;$i++){
 $out=Join-Path $work "run-$i.stdout";$err=Join-Path $work "run-$i.stderr";$start=[DateTime]::UtcNow
 $p=Start-Process -FilePath $py -ArgumentList @('-X','faulthandler',$runner) -WorkingDirectory $root -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
 $r=[ordered]@{run=$i;pid=$p.Id;session=(Get-Process -Id $PID).SessionId;exit=$p.ExitCode;startUtc=$start.ToString('o');endUtc=[DateTime]::UtcNow.ToString('o');stdout=$out;stderr=$err}
 $r|ConvertTo-Json -Compress|Set-Content -LiteralPath (Join-Path $work "run-$i.result.json") -Encoding utf8
 $results+=,$r
}
$results|ConvertTo-Json -Depth 5
