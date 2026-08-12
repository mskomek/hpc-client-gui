[CmdletBinding()]
param(
    [string]$Model,
    [string]$FlashModel = $env:DEEPSEEK_FLASH_MODEL,
    [string]$ProModel = $env:DEEPSEEK_PRO_MODEL,
    [ValidateSet('analyze', 'implement', 'review', 'smoke-test', 'dry-run')]
    [string]$Mode = 'analyze'
)

$ErrorActionPreference = 'Stop'

function Get-OpenCodeModels {
    $raw = & opencode models 2>&1
    if ($LASTEXITCODE -ne 0) { throw "opencode models failed: $($raw -join [Environment]::NewLine)" }
    return @($raw | ForEach-Object { "$($_)".Trim() } | Where-Object { $_ -match '/' })
}

function Assert-DeepSeekModel([string]$Candidate, [string[]]$Available, [string]$Source) {
    if ([string]::IsNullOrWhiteSpace($Candidate)) { return $null }
    if ($Candidate -notmatch '(?i)deepseek') { throw "$Source must identify a DeepSeek model; received '$Candidate'." }
    if ($Candidate -notin $Available) {
        throw "$Source '$Candidate' was not returned by 'opencode models'. Available DeepSeek IDs: $($Available -join ', ')"
    }
    return $Candidate
}

$available = Get-OpenCodeModels
$allDeepSeek = @($available | Where-Object { $_ -match '(?i)deepseek' })
$deepSeek = @($allDeepSeek | Where-Object { $_ -match '(?i)^opencode-go/deepseek' })
if ($deepSeek.Count -eq 0) {
    throw "No OpenCode Go DeepSeek model was returned by 'opencode models'. DeepSeek IDs from other providers: $($allDeepSeek -join ', ')"
}

$manual = Assert-DeepSeekModel $Model $deepSeek '-Model'
$flashOverride = Assert-DeepSeekModel $FlashModel $deepSeek 'DEEPSEEK_FLASH_MODEL / -FlashModel'
$proOverride = Assert-DeepSeekModel $ProModel $deepSeek 'DEEPSEEK_PRO_MODEL / -ProModel'
$flash = if ($flashOverride) { $flashOverride } else { @($deepSeek | Where-Object { $_ -match '(?i)/deepseek.*(flash|fast)' } | Select-Object -First 1)[0] }
$pro = if ($proOverride) { $proOverride } else { @($deepSeek | Where-Object { $_ -match '(?i)/deepseek.*(pro|code|reasoner|strong)' } | Select-Object -First 1)[0] }

if ($manual) { $selected = $manual }
else { $selected = $flash }

[pscustomobject]@{
    AvailableDeepSeekModels = $deepSeek
    FlashModel = $flash
    ProModel = $pro
    SelectedModel = $selected
    IsFlashOnly = [bool]($flash -and -not $pro)
}
