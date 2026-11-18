param([Parameter(Mandatory=$true)][ValidateSet('nested-loop','yield')][string]$Variant,[int]$Runs=5)
$ErrorActionPreference='Stop'
$root='C:\Users\home\AppData\Local\Temp\hpc-client-gui-r14-debug-20261118\repo'
$work=Join-Path $env:LOCALAPPDATA 'Temp\hpc-client-gui-r14-native-crash-20261118'
$sessionId=(Get-Process -Id $PID).SessionId
$py=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
New-Item -ItemType Directory -Path $work -Force | Out-Null
for($i=1;$i -le $Runs;$i++){
  $out=Join-Path $work "$Variant-$i.stdout"
  $err=Join-Path $work "$Variant-$i.stderr"
  $start=[DateTime]::UtcNow
  $p=Start-Process -FilePath $py -ArgumentList @('-X','faulthandler',(Join-Path $work 'variant_runner.py'),$Variant) -WorkingDirectory $root -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
  $r=[ordered]@{variant=$Variant;run=$i;pid=$p.Id;session=$sessionId;exit=$p.ExitCode;startUtc=$start.ToString('o');endUtc=[DateTime]::UtcNow.ToString('o');stdout=$out;stderr=$err}
  $r|ConvertTo-Json -Compress|Set-Content -LiteralPath (Join-Path $work "$Variant-$i.result.json") -Encoding utf8
}
