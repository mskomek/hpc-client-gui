$ErrorActionPreference='Stop'
$task='HPC_GUI_R14_WEBVIEW_MODULE_20261118'
$work=Join-Path $env:LOCALAPPDATA 'Temp\hpc-client-gui-r14-webview-module-20261118'
$root=Join-Path $env:LOCALAPPDATA 'Temp\hpc-client-gui-r14-debug-20261118\repo'
$py=Join-Path $env:LOCALAPPDATA 'Programs\Python\Python314\python.exe'
New-Item -ItemType Directory -Force $work|Out-Null
$env:PYTHONPATH=($root+'\src'+[IO.Path]::PathSeparator+$root+'\tests'+[IO.Path]::PathSeparator+$env:PYTHONPATH)
$out=Join-Path $work 'pytest.stdout';$err=Join-Path $work 'pytest.stderr';$start=[DateTime]::UtcNow
$p=Start-Process -FilePath $py -ArgumentList @('-X','faulthandler','-m','pytest','-p','no:cacheprovider','-vv','--tb=long','--junitxml',(Join-Path $work 'junit.xml'),'tests/test_wx_terminal_webview_bridge.py') -WorkingDirectory $root -PassThru -Wait -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err
[ordered]@{pid=$p.Id;session=(Get-Process -Id $PID).SessionId;exit=$p.ExitCode;startUtc=$start.ToString('o');endUtc=[DateTime]::UtcNow.ToString('o');stdout=$out;stderr=$err;junit=(Join-Path $work 'junit.xml')}|ConvertTo-Json -Depth 4|Set-Content (Join-Path $work 'result.json') -Encoding utf8
