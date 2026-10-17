"""PowerShell command construction for verified self updates."""

from pathlib import Path

from hpc_gui.services.app_updater import RELEASE_EXE_NAME


def _powershell_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"

def build_update_script(
    *,
    zip_path: Path,
    install_dir: Path,
    current_exe: Path,
    new_version: str,
    process_id: int,
) -> str:
    new_exe = install_dir / RELEASE_EXE_NAME
    staging_dir = zip_path.parent / "staging"
    backup_internal = zip_path.parent / "_internal.backup"
    backup_exe = zip_path.parent / "hpc-client-gui.exe.backup"
    install_log = zip_path.parent / "update-install.log"
    return f"""$ErrorActionPreference = "Stop"
$oldPid = {process_id}
$zipPath = {_powershell_literal(str(zip_path))}
$installDir = {_powershell_literal(str(install_dir))}
$stagingDir = {_powershell_literal(str(staging_dir))}
$backupInternal = {_powershell_literal(str(backup_internal))}
$backupExe = {_powershell_literal(str(backup_exe))}
$installLog = {_powershell_literal(str(install_log))}
$currentExe = {_powershell_literal(str(current_exe))}
$newExe = {_powershell_literal(str(new_exe))}

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.IO.Compression
Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.Windows.Forms.Application]::EnableVisualStyles()
$form = New-Object System.Windows.Forms.Form
$form.Text = "Application Update"
$form.FormBorderStyle = [System.Windows.Forms.FormBorderStyle]::None
$form.StartPosition = [System.Windows.Forms.FormStartPosition]::CenterScreen
$form.TopMost = $true
$form.BackColor = [System.Drawing.ColorTranslator]::FromHtml("#f7f8fa")
$form.ClientSize = New-Object System.Drawing.Size(480,250)
$title = New-Object System.Windows.Forms.Label
$title.Text = "APPLICATION UPDATE"
$title.Font = New-Object System.Drawing.Font("Segoe UI",23,[System.Drawing.FontStyle]::Bold)
$title.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#1f2937")
$title.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$title.SetBounds(20,25,440,48)
$subtitle = New-Object System.Windows.Forms.Label
$subtitle.Text = "Updating..."
$subtitle.Font = New-Object System.Drawing.Font("Segoe UI",10)
$subtitle.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#5b6472")
$subtitle.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$subtitle.SetBounds(20,77,440,25)
$statusLabel = New-Object System.Windows.Forms.Label
$statusLabel.Font = New-Object System.Drawing.Font("Segoe UI",10)
$statusLabel.ForeColor = [System.Drawing.ColorTranslator]::FromHtml("#6b7280")
$statusLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$statusLabel.SetBounds(20,125,440,28)
$progressBar = New-Object System.Windows.Forms.ProgressBar
$progressBar.Minimum = 0
$progressBar.Maximum = 100
$progressBar.Style = [System.Windows.Forms.ProgressBarStyle]::Continuous
$progressBar.SetBounds(35,165,410,18)
$percentLabel = New-Object System.Windows.Forms.Label
$percentLabel.Font = New-Object System.Drawing.Font("Segoe UI",10)
$percentLabel.TextAlign = [System.Drawing.ContentAlignment]::MiddleCenter
$percentLabel.SetBounds(20,190,440,25)
$form.Controls.AddRange(@($title,$subtitle,$statusLabel,$progressBar,$percentLabel))
$script:lastProgress = 0
function Set-UpdateProgress([int]$Value, [string]$Status) {{
    $Value = [Math]::Max($script:lastProgress, [Math]::Min(100, $Value))
    $script:lastProgress = $Value
    $statusLabel.Text = $Status
    $progressBar.Value = $Value
    $percentLabel.Text = "$Value%"
    [System.Windows.Forms.Application]::DoEvents()
}}
$form.Show()
Set-UpdateProgress 0 "Preparing update..."

function Write-UpdateLog([string]$Message) {{
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -LiteralPath $installLog -Value "$timestamp $Message" -Encoding utf8
}}

Write-UpdateLog "Updater started"
Write-UpdateLog "Waiting for PID $oldPid"
Set-UpdateProgress 2 "Waiting for application to close..."
Wait-Process -Id $oldPid -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 500

try {{
    if (Test-Path -LiteralPath $stagingDir) {{
        Remove-Item -LiteralPath $stagingDir -Recurse -Force
    }}
    New-Item -ItemType Directory -Path $stagingDir -Force | Out-Null
    Write-UpdateLog "Extraction started"
    $archive = [System.IO.Compression.ZipFile]::OpenRead($zipPath)
    $extractTotal = [Math]::Max(1, ($archive.Entries | Measure-Object -Property Length -Sum).Sum)
    $extractDone = 0L
    $stagingRoot = [System.IO.Path]::GetFullPath($stagingDir + [System.IO.Path]::DirectorySeparatorChar)
    foreach ($entry in $archive.Entries) {{
        $target = [System.IO.Path]::GetFullPath((Join-Path $stagingDir $entry.FullName))
        if (-not $target.StartsWith($stagingRoot, [System.StringComparison]::OrdinalIgnoreCase)) {{
            throw "Unsafe archive path"
        }}
        if ([string]::IsNullOrEmpty($entry.Name)) {{
            New-Item -ItemType Directory -Path $target -Force | Out-Null
            continue
        }}
        New-Item -ItemType Directory -Path ([System.IO.Path]::GetDirectoryName($target)) -Force | Out-Null
        $input = $entry.Open()
        $output = [System.IO.File]::Create($target)
        try {{
            $buffer = New-Object byte[] (1024 * 1024)
            while (($read = $input.Read($buffer, 0, $buffer.Length)) -gt 0) {{
                $output.Write($buffer, 0, $read)
                $extractDone += $read
                $value = 5 + [int](30 * $extractDone / $extractTotal)
                Set-UpdateProgress $value ("Extracting: " + $entry.FullName)
            }}
        }} finally {{ $output.Dispose(); $input.Dispose() }}
    }}
    $archive.Dispose()
    Write-UpdateLog "Extraction completed"

    $internalDir = Join-Path $installDir "_internal"
    Set-UpdateProgress 36 "Backing up current version..."
    if (Test-Path -LiteralPath $backupInternal) {{
        Remove-Item -LiteralPath $backupInternal -Recurse -Force
    }}
    if (Test-Path -LiteralPath $internalDir) {{
        Move-Item -LiteralPath $internalDir -Destination $backupInternal
    }}
    if (Test-Path -LiteralPath $backupExe) {{
        Remove-Item -LiteralPath $backupExe -Force
    }}
    if (Test-Path -LiteralPath $currentExe) {{
        Copy-Item -LiteralPath $currentExe -Destination $backupExe -Force
    }}
    Write-UpdateLog "Backup completed"

    Write-UpdateLog "Copy started"
    $files = @(Get-ChildItem -LiteralPath $stagingDir -Recurse -File)
    $copyTotal = [Math]::Max(1, ($files | Measure-Object -Property Length -Sum).Sum)
    $copyDone = 0L
    foreach ($file in $files) {{
        $relative = $file.FullName.Substring($stagingRoot.Length)
        $target = Join-Path $installDir $relative
        New-Item -ItemType Directory -Path ([System.IO.Path]::GetDirectoryName($target)) -Force | Out-Null
        $input = [System.IO.File]::OpenRead($file.FullName)
        $output = [System.IO.File]::Create($target)
        try {{
            $buffer = New-Object byte[] (1024 * 1024)
            while (($read = $input.Read($buffer, 0, $buffer.Length)) -gt 0) {{
                $output.Write($buffer, 0, $read)
                $copyDone += $read
                $value = 45 + [int](50 * $copyDone / $copyTotal)
                Set-UpdateProgress $value ("Copying: " + $relative)
            }}
        }} finally {{ $output.Dispose(); $input.Dispose() }}
    }}
    Write-UpdateLog "Copy completed"
    Set-UpdateProgress 96 "Verifying installation..."
    if (-not (Test-Path -LiteralPath $newExe)) {{
        throw "Updated executable not found: $newExe"
    }}

    Set-UpdateProgress 98 "Starting application..."
    Write-UpdateLog "Launch attempted"
    $newProcess = Start-Process -FilePath $newExe -WorkingDirectory $installDir -PassThru
    Start-Sleep -Seconds 5
    $newProcess.Refresh()
    if ($newProcess.HasExited -and $newProcess.ExitCode -ne 0) {{
        throw "Updated application exited with code $($newProcess.ExitCode)"
    }}
    Write-UpdateLog "New process healthy"

    Set-UpdateProgress 99 "Cleaning up..."
    if (($currentExe -ne $newExe) -and (Test-Path -LiteralPath $currentExe)) {{
        Remove-Item -LiteralPath $currentExe -Force
    }}
    if (Test-Path -LiteralPath $backupInternal) {{
        Remove-Item -LiteralPath $backupInternal -Recurse -Force
    }}
    if (Test-Path -LiteralPath $backupExe) {{
        Remove-Item -LiteralPath $backupExe -Force
    }}
    Set-UpdateProgress 100 "Update complete."
    Write-UpdateLog "Update to v{new_version} completed"
    Start-Sleep -Milliseconds 500
    $form.Close()
}} catch {{
    Write-UpdateLog "Update failed: $($_.Exception.Message)"
    $statusLabel.ForeColor = [System.Drawing.Color]::DarkRed
    $statusLabel.Text = "Update failed. Restoring previous version..."
    [System.Windows.Forms.Application]::DoEvents()
    Write-UpdateLog "Rollback started"
    $internalDir = Join-Path $installDir "_internal"
    if (Test-Path -LiteralPath $internalDir) {{
        Remove-Item -LiteralPath $internalDir -Recurse -Force
    }}
    if (Test-Path -LiteralPath $backupInternal) {{
        Move-Item -LiteralPath $backupInternal -Destination $internalDir
    }}
    if (($newExe -ne $currentExe) -and (Test-Path -LiteralPath $newExe)) {{
        Remove-Item -LiteralPath $newExe -Force
    }}
    if (Test-Path -LiteralPath $backupExe) {{
        Copy-Item -LiteralPath $backupExe -Destination $currentExe -Force
        Remove-Item -LiteralPath $backupExe -Force
    }}
    if (Test-Path -LiteralPath $currentExe) {{
        Start-Process -FilePath $currentExe -WorkingDirectory $installDir
    }}
    Write-UpdateLog "Rollback completed; previous application restarted"
    [System.Windows.Forms.MessageBox]::Show(
        "The update failed and the previous version was restored. See update-install.log for details.",
        "Application Update",
        [System.Windows.Forms.MessageBoxButtons]::OK,
        [System.Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
    $form.Close()
    exit 1
}}
"""
