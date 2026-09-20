"""Temporary W15-resume diagnostic: launch frozen fresh-user child, poll for the
bootloader crash dialog, dump its text, then kill. Not part of the suite."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts"))
import wx_packaged_smoke as smoke

EXE = ROOT / "dist" / "hpc-client-gui" / "hpc-client-gui.exe"
OUT = ROOT / "build" / "audit" / "w15-resume-dlg2-probe.json"
RUNTIME = ROOT / "build" / "audit" / "w15-resume-dlg2-probe.run1.runtime.json"

fresh_parent = Path(tempfile.mkdtemp(prefix="hpc-dlg2-probe-"))
fresh_root = fresh_parent / "config"
workdir = fresh_parent / "work"
workdir.mkdir(parents=True, exist_ok=True)

loopback_root, server, user, password = smoke._start_loopback_ssh(OUT)
print(f"fixture port={server.port} user={user}", flush=True)
try:
    env = smoke.fresh_user_env(os.environ, fresh_root=fresh_root, run_index=1)
    env["HPC_GUI_PACKAGED_SMOKE_OUTPUT"] = str(RUNTIME.resolve())
    env["HPC_GUI_PACKAGED_SMOKE_SSH_HOST"] = "127.0.0.1"
    env["HPC_GUI_PACKAGED_SMOKE_SSH_PORT"] = str(server.port)
    env["HPC_GUI_PACKAGED_SMOKE_SSH_USER"] = user
    env["HPC_GUI_PACKAGED_SMOKE_SSH_PASSWORD"] = password
    env["HPC_GUI_PACKAGED_SMOKE_SSH_KNOWN_HOSTS"] = str(Path(loopback_root.name) / "known_hosts")
    env["HPC_GUI_PACKAGED_SMOKE_APP_NAME"] = "hpc-dlg2-probe"
    env["WEBVIEW2_USER_DATA_FOLDER"] = str((fresh_parent / "wv").resolve())
    env.pop("PYTHONPATH", None)
    (fresh_parent / "wv").mkdir(exist_ok=True)
    RUNTIME.unlink(missing_ok=True)
    p = subprocess.Popen([str(EXE), "--wx-smoke"], cwd=str(workdir), env=env)
    print(f"child pid={p.pid}", flush=True)
    dumped = False
    for i in range(30):
        time.sleep(2)
        if p.poll() is not None:
            print(f"child exited rc={p.returncode} at t={(i+1)*2}s", flush=True)
            break
        wins = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(ROOT / "_w15_list_wins.ps1")],
            capture_output=True, timeout=30)
        wintext = wins.stdout.decode("utf-8", "replace") if wins.stdout else ""
        mine = [l for l in wintext.splitlines() if f"PID={p.pid}" in l]
        if mine:
            print(f"t={(i+1)*2}s " + " | ".join(mine), flush=True)
            if any("Unhandled exception" in l for l in mine) and not dumped:
                dump = subprocess.run(
                    ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                     "-File", str(ROOT / "_w15_dump_dlg.ps1")],
                    capture_output=True, timeout=60)
                print("=== DIALOG DUMP ===", flush=True)
                print(dump.stdout.decode("utf-8", "replace")[-6000:], flush=True)
                dumped = True
                break
    if p.poll() is None:
        p.kill()
        print("child killed", flush=True)
    print("RUNTIME:", RUNTIME.read_text(encoding="utf-8")[:1500] if RUNTIME.is_file() else "<absent>")
    print("config root:", [x.name for x in fresh_root.iterdir()] if fresh_root.is_dir() else "<absent>")
finally:
    try:
        server.__exit__(None, None, None)
    except Exception:
        pass
    print("fresh_parent_kept:", fresh_parent)
