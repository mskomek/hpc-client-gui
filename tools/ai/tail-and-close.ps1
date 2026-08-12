[CmdletBinding()]
param(
    [Parameter(Mandatory)]
    [string]$LogFile,
    [Parameter(Mandatory)]
    [string]$MatchCommandLine,
    [int]$PollSeconds = 2,
    [int]$AutoCloseDelaySeconds = 5
)

$Host.UI.RawUI.WindowTitle = "DeepSeek takip: $(Split-Path -Leaf $LogFile)"
Write-Host "Takip ediliyor: $LogFile"
Write-Host "Eslesme metni : $MatchCommandLine"
Write-Host "---"

function Find-TargetProcess {
    Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object { $_.ProcessId -ne $PID -and $_.CommandLine -and $_.CommandLine.Contains($MatchCommandLine) } |
        Select-Object -First 1
}

$lastLength = 0
function Show-NewContent {
    if (-not (Test-Path -LiteralPath $LogFile)) { return }
    try {
        $content = [IO.File]::ReadAllText($LogFile)
    } catch { return }
    if ($content.Length -gt $script:lastLength) {
        Write-Host ($content.Substring($script:lastLength)) -NoNewline
        $script:lastLength = $content.Length
    }
}

Write-Host "Surec araniyor..."
$deadline = (Get-Date).AddSeconds(30)
$target = $null
while ((Get-Date) -lt $deadline -and -not $target) {
    $target = Find-TargetProcess
    Show-NewContent
    if (-not $target) { Start-Sleep -Seconds 1 }
}

if (-not $target) {
    Write-Host "Surec 30 saniye icinde bulunamadi; yalnizca log dosyasi izlenecek."
} else {
    Write-Host "Surec bulundu (PID $($target.ProcessId)). Bitince pencere otomatik kapanacak."
}
Write-Host "---"

while ($true) {
    Show-NewContent
    if ($target) {
        $stillAlive = Get-Process -Id $target.ProcessId -ErrorAction SilentlyContinue
        if (-not $stillAlive) { break }
    } elseif (Test-Path -LiteralPath $LogFile) {
        # No process handle: fall back to log-stability heuristic.
        Start-Sleep -Seconds $PollSeconds
        Show-NewContent
        break
    }
    Start-Sleep -Seconds $PollSeconds
}

Show-NewContent
Write-Host "`n--- Tamamlandi. Pencere $AutoCloseDelaySeconds saniye icinde kapanacak. ---"
Start-Sleep -Seconds $AutoCloseDelaySeconds
