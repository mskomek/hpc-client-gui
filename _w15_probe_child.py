"""Temporary W15-resume diagnostic: launch the fresh-user child manually and poll
its visible window titles to locate a hang. Not part of the test suite."""
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
OUT = ROOT / "build" / "audit" / "w15-resume-child-probe.json"
RUNTIME = ROOT / "build" / "audit" / "w15-resume-child-probe.run1.runtime.json"

fresh_parent = Path(tempfile.mkdtemp(prefix="hpc-fresh-probe-"))
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
    env["HPC_GUI_PACKAGED_SMOKE_APP_NAME"] = "hpc-probe-manual"
    env["WEBVIEW2_USER_DATA_FOLDER"] = str((fresh_parent / "wv").resolve())
    env.pop("PYTHONPATH", None)
    (fresh_parent / "wv").mkdir(exist_ok=True)
    RUNTIME.unlink(missing_ok=True)
    p = subprocess.Popen([str(EXE), "--wx-smoke"], cwd=str(workdir), env=env)
    print(f"child pid={p.pid}", flush=True)
    for i in range(24):
        time.sleep(5)
        rc = p.poll()
        try:
            ps = subprocess.run(
                ["powershell", "-NoProfile", "-Command",
                 f"(Get-Process -Id {p.pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty MainWindowTitle)"],
                capture_output=True, text=True, timeout=15)
            title = (ps.stdout or "").strip()
        except Exception as e:
            title = f"<poll error {e}>"
        rt = "no" if not RUNTIME.is_file() else "YES"
        print(f"t={(i + 1) * 5:3d}s rc={rc} runtime={rt} title={title!r}", flush=True)
        if rc is not None:
            break
    if p.poll() is None:
        print("child still alive -> killing", flush=True)
        p.kill()
    try:
        print("RUNTIME:", RUNTIME.read_text(encoding="utf-8")[:2000] if RUNTIME.is_file() else "<absent>")
    except Exception as e:
        print("runtime read error", e)
    print("config root:", [x.name for x in fresh_root.iterdir()] if fresh_root.is_dir() else "<absent>")
finally:
    try:
        server.__exit__(None, None, None)
    except Exception:
        pass
    print("fresh_parent_kept:", fresh_parent)
