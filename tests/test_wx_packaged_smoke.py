import json
import subprocess
import sys
from pathlib import Path

import pytest


pytestmark = pytest.mark.packaging


@pytest.mark.reporting
def test_missing_artifact_report_fails_critical_stages(tmp_path):
    root = Path(__file__).parents[1]
    artifact = tmp_path / "missing-wx-artifact.exe"
    output = tmp_path / "smoke-evidence.json"
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
    assert report == json.loads(output.read_text(encoding="utf-8"))
    assert report["result"] == "FAIL"
    assert {"process_started", "wx_runtime_started", "main_frame_created", "clean_shutdown"} <= report["checks"].keys()
    assert set(report["checks"].values()) == {"FAIL"}
    assert "artifact not found" in report["details"]["artifact"]
    assert "MFA" in report["manual_required"]
