from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest import mock

import pytest

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


def _spec_text() -> str:
    return (rm.REPO_ROOT / "build" / "macos" / "hpc-client-gui.spec").read_text(encoding="utf-8")


def test_macos_spec_excludes_devtools_like_windows_and_linux():
    text = _spec_text()
    assert "qtwebengine_devtools_resources" in text
    for other in (
        rm.REPO_ROOT / "build/windows/hpc-client-gui.spec",
        rm.REPO_ROOT / "build/linux/hpc-client-gui-linux.spec",
    ):
        assert "qtwebengine_devtools_resources" in other.read_text(encoding="utf-8")
    # The safe keep-list stays intact: WebEngine runtime, ICU data, and
    # software rendering fallbacks must never be excluded.
    for forbidden in ("qtwebenginecore", "icudtl", "softwarerenderer", "_renderer"):
        assert forbidden not in text.split("EXCLUDED_NAME_PATTERNS", 1)[1].lower()


def test_dmg_budget_defaults_to_600_mib():
    assert rm.DEFAULT_DMG_BUDGET_MIB == 600
    assert rm.dmg_budget_mib({}) == 600


def test_dmg_budget_override_is_validated(tmp_path):
    with pytest.raises(rm.PackagingError, match="integer"):
        rm.dmg_budget_mib({rm.DMG_BUDGET_ENV: "big"})
    with pytest.raises(rm.PackagingError, match="positive"):
        rm.dmg_budget_mib({rm.DMG_BUDGET_ENV: "0"})
    assert rm.dmg_budget_mib({rm.DMG_BUDGET_ENV: "750"}) == 750


def test_dmg_over_budget_is_rejected(tmp_path):
    dmg = tmp_path / "hpc-client-gui_macos_arm64.dmg"
    dmg.write_bytes(b"x" * (601 * 1024 * 1024))
    with pytest.raises(rm.PackagingError, match="package-size budget"):
        rm.check_dmg_budget(dmg, 600)


def test_dmg_within_budget_reports_size(tmp_path):
    dmg = tmp_path / "hpc-client-gui_macos_arm64.dmg"
    dmg.write_bytes(b"x" * (2 * 1024 * 1024))
    line = rm.check_dmg_budget(dmg, 600)
    assert "2.00 MiB" in line and "budget: 600 MiB" in line


def test_bundle_report_lists_largest_files(tmp_path):
    app = tmp_path / "HPC Client GUI.app" / "Contents" / "MacOS"
    app.mkdir(parents=True)
    (app / "big.bin").write_bytes(b"a" * 5000)
    (app / "small.bin").write_bytes(b"b")
    from report_bundle_sizes import collect_report, format_report

    report = collect_report(app.parent.parent)
    text = format_report(report)
    assert "big.bin" in text and "small.bin" in text
    assert text.index("big.bin") < text.index("small.bin")


def test_macos_staging_preserves_framework_symlinks():
    release_script = (rm.REPO_ROOT / "scripts" / "release_macos.py").read_text(encoding="utf-8")
    signing_script = (rm.REPO_ROOT / "scripts" / "sign_macos_release.py").read_text(encoding="utf-8")
    assert "shutil.copytree(app, plan.staging / app.name, symlinks=True)" in release_script
    assert "shutil.copytree(app, stage / app.name, symlinks=True)" in signing_script


def test_release_lock_keeps_macos_x86_64_cryptography_support():
    lock = (rm.REPO_ROOT / "requirements-release.lock").read_text(encoding="utf-8")
    assert 'cryptography==50.0.0; sys_platform != "darwin" or platform_machine != "x86_64"' in lock
    assert 'cryptography==48.0.1; sys_platform == "darwin" and platform_machine == "x86_64"' in lock
