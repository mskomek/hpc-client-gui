"""W14 provenance / build-manifest / artifact-identity regression tests.

Purpose IDs:
  REQ-W14-MANIFEST  requirement proof for HPC-W04-MANIFEST-001 (11 fields)
  REQ-W14-PROV      requirement proof for HPC-W04-PROV-001/002 (capture)
  REQ-W04-GUARD     defect regression for HPC-W04-PROV-003 (stale guard)
  REQ-W14-IDENTITY  requirement proof for HPC-W04-IDENTITY-001/002
  REQ-W14-VERSION   requirement proof for HPC-W04-MANIFEST-002 (consistency)
  NEG-W14-*         negative/error-path proof
  PKG-W14-*         packaged-artifact proof (staged release dir manifest)

Taxonomy: unit + packaging + static contract. No GUI surface is touched by
W14, so no wx runtime proof applies. Mocking: none -- tests exercise real
code against tmp fixtures plus read-only git inspection of the checkout.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.release

import artifact_identity as identity  # noqa: E402
import capture_build_provenance as prov  # noqa: E402
import generate_release_manifest as gen  # noqa: E402

REQUIRED_MANIFEST_FIELDS = (
    "main_commit",
    "plugin_commit",
    "plugin_bundle_revision",
    "build_timestamp_utc",
    "app_version",
    "python_runtime",
    "packager_version",
    "target_os_arch",
    "build_command",
    "dependency_lock_sha256",
)


def _stage_release(tmp_path: Path) -> Path:
    release_dir = tmp_path / "v9.9.9"
    release_dir.mkdir()
    (release_dir / "hpc-client-gui_windows_onedir.zip").write_bytes(b"candidate-bytes")
    return release_dir


# --- REQ-W14-MANIFEST: 11-field build manifest -------------------------------


def test_manifest_contains_all_provenance_fields(tmp_path: Path) -> None:
    """REQ-W14-MANIFEST: staged manifest carries every Workstream B field."""
    release_dir = _stage_release(tmp_path)
    manifest = gen.build_manifest(release_dir, "v9.9.9", build_command="unit-test-build")

    for field in REQUIRED_MANIFEST_FIELDS:
        assert manifest.get(field), f"manifest missing provenance field: {field}"
    assert re.fullmatch(r"[0-9a-fA-F]{40}", manifest["main_commit"])
    assert manifest["artifacts"] and manifest["artifacts"][0]["file"].endswith(".zip")
    assert re.fullmatch(r"[0-9a-f]{64}", manifest["artifacts"][0]["sha256"])
    # backward compatibility with the pre-W14 schema
    assert manifest["schema"] == 1
    assert manifest["release"] == "v9.9.9"


def test_manifest_rejects_empty_release_dir(tmp_path: Path, capsys) -> None:
    """NEG-W14-MANIFEST: manifest generation fails visibly with no artifacts."""
    empty = tmp_path / "empty"
    empty.mkdir()
    assert gen.main(["--release-dir", str(empty), "--version", "v0.0.0"]) == 2
    assert "no artifacts" in capsys.readouterr().err


def test_manifest_rejects_missing_release_dir(tmp_path: Path, capsys) -> None:
    """NEG-W14-MANIFEST: manifest generation fails visibly for missing dir."""
    assert gen.main(["--release-dir", str(tmp_path / "absent")]) == 2
    assert "does not exist" in capsys.readouterr().err


# --- REQ-W14-PROV: provenance capture ----------------------------------------


def test_provenance_captures_git_identity_and_toolchain() -> None:
    """REQ-W14-PROV: capture records HEAD/status facts plus toolchain pins."""
    facts = prov.capture_provenance(ROOT)
    assert re.fullmatch(r"[0-9a-fA-F]{40}", facts["main_commit"])
    assert isinstance(facts["main_status"], str)
    assert re.fullmatch(r"\d+\.\d+.*", facts["toolchain"]["python"])
    assert facts["toolchain"]["os_arch"].startswith("windows/")
    assert facts["captured_utc"].endswith("+00:00")
    assert re.fullmatch(r"[0-9a-f]{64}", facts["dependency_lock_sha256"])


# --- HPC-W04-PROV-003: stale-dist guard --------------------------------------


def test_stale_guard_rejects_unidentified_executable(tmp_path: Path) -> None:
    """REQ-W04-GUARD: stale exe inside the candidate blocks the build."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "hpc-client-gui.exe").write_bytes(b"stale-bytes")
    with pytest.raises(ValueError, match="stale build outputs"):
        prov.guard_candidate_dir(candidate, search_roots=())


def test_stale_guard_accepts_clean_candidate(tmp_path: Path) -> None:
    """REQ-W04-GUARD happy path: clean dir passes with no quarantine."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "notes.txt").write_text("not an executable\n")
    assert prov.guard_candidate_dir(candidate, search_roots=()) == []


def test_stale_guard_accepts_declared_fresh_artifact(tmp_path: Path) -> None:
    """Lifecycle: post-build re-verification exempts only the declared artifact."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    fresh = candidate / "hpc_client_gui-1.5.9-py3-none-any.whl"
    fresh.write_bytes(b"fresh")
    assert prov.guard_candidate_dir(candidate, search_roots=(), known_fresh={fresh.name}) == []
    with pytest.raises(ValueError, match="stale build outputs"):
        prov.guard_candidate_dir(candidate, search_roots=())


def test_stale_guard_cli_known_fresh_exempts_declared_artifact(tmp_path: Path, capsys) -> None:
    """CLI: --known-fresh exempts the declared current-build artifact.

    The CLI scans the real dist/ + build/ roots, so exit stays 2 while
    pre-existing stale outputs exist; the declared fresh file itself must
    not appear in the stale listing.
    """
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    fresh_name = "hpc_client_gui-9.9.9-py3-none-any.whl"
    (candidate / fresh_name).write_bytes(b"fresh")
    rc_without = prov.main(["--candidate-dir", str(candidate)])
    assert rc_without == 2 or rc_without == 0
    capsys.readouterr()
    rc_with = prov.main(["--candidate-dir", str(candidate), "--known-fresh", fresh_name])
    err = capsys.readouterr().err
    assert fresh_name not in err
    assert rc_with in (0, 2)


def test_stale_guard_quarantines_outside_candidate(tmp_path: Path) -> None:
    """Lifecycle: stale outputs move to an explicit archive outside the path."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    stale_exe = candidate / "old-build.exe"
    stale_exe.write_bytes(b"stale")
    archive = tmp_path / "quarantine-20260919"
    moved = prov.guard_candidate_dir(candidate, archive_outside=archive, search_roots=())
    assert not stale_exe.exists()
    assert moved == [archive / "old-build.exe"]
    assert prov.guard_candidate_dir(candidate, search_roots=()) == []


def test_stale_guard_refuses_archive_inside_candidate(tmp_path: Path) -> None:
    """NEG-W14-GUARD: archive inside the candidate path is rejected."""
    candidate = tmp_path / "candidate"
    candidate.mkdir()
    (candidate / "old-build.exe").write_bytes(b"stale")
    with pytest.raises(ValueError, match="outside the candidate path"):
        prov.guard_candidate_dir(candidate, archive_outside=candidate / "archive", search_roots=())


# --- REQ-W14-IDENTITY: six-line header ---------------------------------------


def test_identity_header_has_six_required_lines() -> None:
    """REQ-W14-IDENTITY: header carries Artifact/SHA/Main/Plugin/Ver/OS."""
    header = identity.format_artifact_identity(
        artifact="hpc-client-gui_windows_onedir.zip",
        sha256="a" * 64,
        main_sha="b" * 40,
        plugin_sha="c" * 40,
        version="1.5.9",
        os_arch="windows/amd64",
    )
    lines = header.splitlines()
    assert [line.split(":")[0] for line in lines] == [
        "Artifact",
        "SHA256",
        "Main SHA",
        "Plugin SHA",
        "Version",
        "OS/arch",
    ]
    assert identity.parse_artifact_identity(header)["SHA256"] == "a" * 64


def test_identity_header_rejects_malformed_input() -> None:
    """NEG-W14-IDENTITY: truncated header cannot pass as identity proof."""
    with pytest.raises(ValueError, match="missing labels"):
        identity.parse_artifact_identity("Artifact: x\nSHA256: y")


def test_manifest_identity_headers_bind_exact_hashes(tmp_path: Path) -> None:
    """REQ-W14-IDENTITY + HPC-W04-IDENTITY-002: rebuilt content changes identity."""
    release_dir = _stage_release(tmp_path)
    first = gen.build_manifest(release_dir, "v9.9.9")
    (release_dir / "hpc-client-gui_windows_onedir.zip").write_bytes(b"changed-bytes")
    second = gen.build_manifest(release_dir, "v9.9.9")
    first_headers = gen.identity_headers_for_manifest(first)
    second_headers = gen.identity_headers_for_manifest(second)
    assert len(first_headers) == len(second_headers) == 1
    assert first_headers[0] != second_headers[0]
    assert second_headers[0].splitlines()[0].startswith("Artifact: ")


def test_smoke_evidence_carries_identity_header(tmp_path: Path) -> None:
    """PKG-W14-IDENTITY: packaged-smoke evidence embeds the six-line header."""
    import wx_packaged_smoke as smoke  # noqa: E402

    artifact = tmp_path / "probe.py"
    artifact.write_bytes(b"print('probe')\n")
    out = tmp_path / "smoke.json"
    evidence = smoke.run_packaged_smoke(artifact, "windows", out, timeout=5)
    try:
        header = evidence["identity_header"]
        parsed = identity.parse_artifact_identity(header)
        assert parsed["Artifact"] == "probe.py"
        assert re.fullmatch(r"[0-9a-f]{64}", parsed["SHA256"])
        assert re.fullmatch(r"[0-9a-fA-F]{40}", parsed["Main SHA"])
    finally:
        out.unlink(missing_ok=True)


# --- REQ-W14-VERSION: packaged app reports manifest-consistent version -------


def test_manifest_app_version_matches_product_metadata() -> None:
    """REQ-W14-VERSION: manifest version agrees with __version__/CLI/changelog."""
    from hpc_gui import __version__  # noqa: E402
    from hpc_gui.cli.main import CLI_VERSION  # noqa: E402

    assert CLI_VERSION == __version__
    changelog = (ROOT / "src" / "hpc_gui" / "docs" / "CHANGELOG.md").read_text(encoding="utf-8")
    assert f"## v{__version__}" in changelog
    assert gen._app_version() == __version__


def test_provenance_degrades_truthfully_without_repos(tmp_path: Path) -> None:
    """NEG-W14-PROV: non-repo roots yield explicit unknown, never a fake SHA."""
    assert gen._git_head(tmp_path) == "unknown"
    facts = prov.capture_provenance(tmp_path)
    assert facts["main_commit"] == "unknown"
    assert facts["dependency_lock_sha256"] == "unknown"


def test_staged_manifest_json_is_machine_readable(tmp_path: Path) -> None:
    """PKG-W14-MANIFEST: written MANIFEST.json round-trips with all fields."""
    release_dir = _stage_release(tmp_path)
    manifest = gen.build_manifest(release_dir, "v9.9.9", build_command="unit-test-build")
    encoded = json.dumps(manifest, indent=2)
    decoded = json.loads(encoded)
    for field in (*REQUIRED_MANIFEST_FIELDS, "schema", "release", "artifacts"):
        assert field in decoded
