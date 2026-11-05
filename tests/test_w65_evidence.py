"""W65 G48: evidence manifest + 500-line gate self-check."""
from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
OWNED = ["src/hpc_gui/openfoam_core", "src/hpc_gui/plugins/openfoam_studio",
         "src/hpc_gui/plugins/openfoam_lint", "tests/test_w65_core_roundtrip.py",
         "tests/test_w65_catalog.py", "tests/test_w65_mesh.py", "tests/test_w65_physics.py",
         "tests/test_w65_workflow.py", "tests/test_w65_lint.py", "tests/test_w65_sftp_slurm.py",
         "tests/test_w65_evidence.py", "tests/test_w65_r9_host.py"]


def _physical_lines(path: Path) -> int:
    return sum(1 for _ in path.open(encoding="utf-8", errors="replace"))


def test_owned_files_within_500_lines():
    offenders = []
    for rel in OWNED:
        target = REPO / rel
        if target.is_dir():
            for child in sorted(target.glob("*.py")):
                if _physical_lines(child) > 500:
                    offenders.append(str(child))
        elif target.is_file():
            if _physical_lines(target) > 500:
                offenders.append(str(target))
    assert offenders == []


def test_manifest_and_bindings_exist_and_bind_commit():
    manifest = REPO / "artifacts/wave_W65/WAVE_W65_EVIDENCE_MANIFEST.json"
    bindings = REPO / "artifacts/wave_W65/W65_SOURCE_BINDINGS.json"
    assert manifest.is_file() and bindings.is_file()
    data = json.loads(manifest.read_text(encoding="utf-8"))
    assert data["wave"] == "W65" and data["git"]["push"] == "NO"
    bdata = json.loads(bindings.read_text(encoding="utf-8"))
    assert bdata["head"] == data["git"]["head"]
