from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import release_macos as rm


def test_plan_is_stable_and_arch_specific():
    plan = rm.make_plan(rm.resolve_version(), "arm64")
    data = plan.to_dict()
    assert data["artifact"].endswith("_arm64.dmg")
    assert data["output"].endswith("hpc-client-gui_macos_arm64.dmg")
    assert data["commands"][0][-1].endswith("hpc-client-gui.spec")


def test_execute_refuses_non_macos_before_mutation(monkeypatch):
    plan = rm.make_plan(rm.resolve_version(), "arm64")
    monkeypatch.setattr(rm.sys, "platform", "win32")
    with mock.patch.object(rm, "_run") as run:
        try:
            rm.execute(plan)
        except rm.PackagingError as exc:
            assert "Darwin" in str(exc)
        else:
            raise AssertionError("execute unexpectedly succeeded")
    run.assert_not_called()


def test_main_json_dry_run(capsys):
    assert rm.main(["--version", rm.resolve_version(), "--arch", "x86_64", "--json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact"].endswith("_x86_64.dmg")


def test_smoke_script_is_darwin_gated():
    import macos_release_smoke

    with mock.patch.object(macos_release_smoke.os.sys, "platform", "win32"):
        assert macos_release_smoke.main(["--app", "."]) == 1
