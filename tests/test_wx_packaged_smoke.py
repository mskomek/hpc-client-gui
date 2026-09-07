import json
import subprocess
import sys
from pathlib import Path


def test_packaged_wx_smoke_gate_reports_critical_stages():
    import pytest
    root = Path(__file__).parents[1]
    result = subprocess.run([sys.executable, "scripts/wx_packaged_smoke.py"], cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        # Packaging gate requires a built artifact (build/audit/...); skip when not built
        combined = (result.stdout or "") + (result.stderr or "")
        if "artifact not found" in combined or "missing" in combined.lower():
            pytest.skip(f"wx packaged artifact not built: {combined[:300]}")
    assert result.returncode == 0, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["schema"] == "wx-packaged-smoke/1"
    assert all(value == "PASS" for value in report["stages"].values())
    assert "MFA" in report["manual_required"]
