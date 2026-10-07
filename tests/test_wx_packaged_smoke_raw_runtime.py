"""Raw runtime failures remain authoritative in packaged smoke acceptance."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def test_raw_critical_runtime_failures_override_server_observations(tmp_path, monkeypatch):
    root = Path(__file__).parents[1]
    scripts = str(root / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import wx_packaged_smoke as runner

    payload = {
        "schema": "wx-packaged-runtime/1",
        "result": "PASS",
        "checks": {
            name: "PASS" for name in runner.REQUIRED_CHECKS
            if name != "process_started"
        },
    }
    payload["checks"].update(pty_resize="FAIL", clean_shutdown="FAIL")
    artifact = tmp_path / "stub.py"
    artifact.write_text(
        "import json, os\nfrom pathlib import Path\n"
        "Path(os.environ['HPC_GUI_PACKAGED_SMOKE_OUTPUT']).write_text("
        "json.dumps(json.loads(os.environ['HPC_STUB_PAYLOAD'])))\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("HPC_STUB_PAYLOAD", json.dumps(payload))

    class FakeRoot:
        name = str(tmp_path)

        def cleanup(self):
            pass

    class FakeServer:
        port = 2222
        pty_sizes = [(96, 31)]
        resize_sizes = [(123, 45)]

        def __exit__(self, *_args):
            pass

    monkeypatch.setattr(
        runner, "_start_loopback_ssh",
        lambda _output: (FakeRoot(), FakeServer(), "user", "password"),
    )
    evidence = runner.run_packaged_smoke(artifact, "windows", tmp_path / "result.json")

    assert evidence["result"] == "FAIL"
    assert evidence["checks"]["pty_resize"] == "FAIL"
    assert evidence["checks"]["clean_shutdown"] == "FAIL"
    assert evidence["details"]["raw_runtime_failed_checks"] == [
        "pty_resize", "clean_shutdown"
    ]
