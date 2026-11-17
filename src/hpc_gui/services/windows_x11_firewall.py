"""Windows Firewall proof for an app-owned, authenticated VcXsrv listener."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

from hpc_gui.core.xauthority import read_mit_cookie


def firewall_isolation_proven(executable: Path) -> bool:
    """Require active firewall isolation for this exact VcXsrv binary."""
    powershell = shutil.which("powershell.exe") or shutil.which("powershell")
    if not powershell:
        return False
    script = r'''
$ErrorActionPreference = 'Stop'
try {
  $svc = Get-Service -Name MpsSvc
  if ($svc.Status -ne 'Running') { exit 2 }
  $profiles = @(Get-NetFirewallProfile -PolicyStore ActiveStore)
  if (@($profiles | Where-Object { !$_.Enabled -or $_.DefaultInboundAction -ne 'Block' }).Count) { exit 3 }
  $active = @(Get-NetConnectionProfile | ForEach-Object {
    if ($_.NetworkCategory -eq 'DomainAuthenticated') { 'Domain' }
    else { [string]$_.NetworkCategory }
  } | Select-Object -Unique)
  if (!$active.Count) { exit 4 }
  $rules = @(Get-NetFirewallRule -PolicyStore ActiveStore -Direction Inbound -Enabled True -Action Block)
  foreach ($protocol in @('TCP','UDP')) {
    foreach ($profileName in $active) {
      $matched = $false
      foreach ($rule in $rules) {
        $app = Get-NetFirewallApplicationFilter -AssociatedNetFirewallRule $rule -ErrorAction SilentlyContinue
        if ([string]::IsNullOrWhiteSpace($app.Program) -or $app.Program -ine $env:HPC_X11_EXE) { continue }
        $port = Get-NetFirewallPortFilter -AssociatedNetFirewallRule $rule
        if (($port.Protocol -notcontains $protocol) -and ($port.Protocol -notcontains 'Any')) { continue }
        if (($port.LocalPort -notcontains 'Any') -or ($port.RemotePort -notcontains 'Any')) { continue }
        $address = Get-NetFirewallAddressFilter -AssociatedNetFirewallRule $rule
        if ($address.RemoteAddress -notcontains 'Any') { continue }
        $security = Get-NetFirewallSecurityFilter -AssociatedNetFirewallRule $rule
        if ($security.OverrideBlockRules -eq $true) { continue }
        $scope = @($rule.Profile | ForEach-Object { [string]$_ })
        if (($scope -contains 'Any') -or ($scope -contains $profileName)) { $matched = $true; break }
      }
      if (!$matched) { exit 5 }
    }
  }
  'PASS'
  exit 0
} catch { exit 6 }
'''
    env = os.environ.copy()
    env["HPC_X11_EXE"] = str(executable)
    try:
        result = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=8, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except Exception:
        return False
    return result.returncode == 0 and result.stdout.strip() == "PASS"


def app_firewall_listener(
    display: int,
    *,
    pid_file: Path,
    auth_marker: Path,
    executable_path: Path | None,
) -> bool:
    """Accept wildcard binds only for this task's cookie-authenticated server."""
    try:
        pid = int(pid_file.read_text(encoding="utf-8").strip())
        auth_path = Path(auth_marker.read_text(encoding="utf-8").strip())
        if not auth_path.is_file() or read_mit_cookie(auth_path, display) is None:
            return False
        result = subprocess.run(
            ["netstat", "-ano", "-p", "tcp"], capture_output=True,
            text=True, timeout=3,
        )
        addresses, pids = [], set()
        port = str(6000 + int(display))
        for line in (result.stdout or "").splitlines():
            columns = line.split()
            if len(columns) < 5 or columns[0].upper() != "TCP" or columns[-2].upper() != "LISTENING":
                continue
            endpoint = columns[1].rsplit(":", 1)
            if len(endpoint) == 2 and endpoint[1] == port:
                addresses.append(endpoint[0].strip("[]"))
                pids.add(int(columns[-1]))
        if not addresses or pids != {pid}:
            return False
        if any(address not in {"127.0.0.1", "::1", "0.0.0.0", "::"} for address in addresses):
            return False
        if not any(address in {"0.0.0.0", "::"} for address in addresses):
            return False
        powershell = shutil.which("powershell.exe") or shutil.which("powershell")
        if not powershell or executable_path is None:
            return False
        script = "$p=Get-CimInstance Win32_Process -Filter ('ProcessId=' + $env:HPC_X11_PID); if($p){$p | Select-Object ExecutablePath,CommandLine | ConvertTo-Json -Compress}"
        env = os.environ.copy()
        env["HPC_X11_PID"] = str(pid)
        proc = subprocess.run(
            [powershell, "-NoProfile", "-NonInteractive", "-Command", script],
            capture_output=True, text=True, timeout=5, env=env,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        identity = json.loads(proc.stdout) if proc.returncode == 0 and proc.stdout.strip() else None
        if not isinstance(identity, dict):
            return False
        executable = Path(identity.get("ExecutablePath") or "")
        command_line = str(identity.get("CommandLine") or "")
        auth_option = re.compile(
            r"(?i)(?:^|\s)-auth(?:\s+|=)\"?" + re.escape(str(auth_path)) + r"\"?(?:\s|$)"
        )
        if not executable.samefile(executable_path) or not auth_option.search(command_line):
            return False
        if "-listen tcp" not in command_line.lower() or re.search(r"(?i)(?:^|\s)-ac(?:\s|$)", command_line):
            return False
        return firewall_isolation_proven(executable)
    except Exception:
        return False
