import json
import subprocess
import sys
from pathlib import Path


def test_packaged_wx_smoke_gate_reports_critical_stages():
    root = Path(__file__).parents[1]
    result = subprocess.run([sys.executable, "scripts/wx_packaged_smoke.py"], cwd=root, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["schema"] == "wx-packaged-smoke/1"
    assert all(value == "PASS" for value in report["stages"].values())
    assert "MFA" in report["manual_required"]
