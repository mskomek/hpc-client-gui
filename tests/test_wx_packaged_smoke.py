import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = [
    pytest.mark.reporting,
    pytest.mark.packaging,
    pytest.mark.windows,
]


@pytest.mark.subprocess
def test_packaged_wx_smoke_gate_fails_closed_without_artifact(tmp_path):
    root = Path(__file__).parents[1]
    artifact = tmp_path / "missing.exe"
    output = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/wx_packaged_smoke.py",
            "--artifact",
            str(artifact),
            "--platform",
            "windows",
            "--output",
            str(output),
        ],
        cwd=root,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1, result.stderr or result.stdout
    report = json.loads(result.stdout)
    assert report["schema"] == "wx-packaged-smoke/1"
    assert report["result"] == "FAIL"
    assert report["checks"]["process_started"] == "FAIL"
    assert "artifact not found" in report["details"]["artifact"]
    assert json.loads(output.read_text(encoding="utf-8")) == report
    assert "MFA" in report["manual_required"]
