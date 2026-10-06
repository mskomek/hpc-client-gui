"""Regression checks for W61.1's release-gate and rollback handoff text."""

from __future__ import annotations

import json
import os
from pathlib import Path


def _root() -> Path:
    override = os.environ.get("W61_1_HANDOFF_ROOT")
    return Path(override).resolve() if override else Path(__file__).resolve().parents[1]


def _section(text: str, heading: str, next_heading: str) -> tuple[str, str]:
    start = text.index(heading)
    end = text.index(next_heading, start + len(heading))
    return text[start:end], heading


def test_w611_rel025_records_the_repaired_documented_cli_entrypoint() -> None:
    root = _root()
    report = (root / "docs/wave-reports/v2/opencode/W61.1_WAVE_REPORT.md").read_text(
        encoding="utf-8-sig"
    )
    current, _ = _section(
        report,
        "## U02.1 current clean-launch result",
        "## Current requirement status reconciliation",
    )
    receipt_path = (
        root
        / "artifacts/wave_W61.1/packaged-runtime/U02.1-clean-launch/"
        "W61.1_U02.1_GUEST_LAUNCH_20261006.json"
    )
    receipt = json.loads(receipt_path.read_text(encoding="utf-8-sig"))
    current_historical_heading = "## Historical host-side packaged wx smoke"
    stale_guest_heading = "## section-runtime-smoke-launch (U02.1: REL-025 packaged wx clean launch)"
    assert current_historical_heading in report, "host smoke must be labelled historical"
    assert stale_guest_heading not in report, "host smoke is being presented as a guest launch"
    historical, _ = _section(
        report,
        current_historical_heading,
        "## section-runtime-smoke-gj",
    )

    assert "Copy-Item -ToSession" in current
    repaired_path = (
        root
        / "artifacts/wave_W61.1/packaged-runtime/U02.1-clean-launch/"
        "W61.1_U02.1_CLI_GUI_REPAIR_20261006.json"
    )
    repaired = json.loads(repaired_path.read_text(encoding="utf-8-sig"))

    assert "PARTIAL" in current and "NO-GO" in current
    assert "operative W57 frozen onedir candidate remains" in current
    assert receipt["guest"]["candidate_sha256_verified"] == (
        "B3019DEA16783C8AB859FA36D2B0FEF2FB70DB075633E54EB0F36587295374FD"
    )
    assert receipt["default_gui_launch"]["window_title"] == "HPC Client GUI 1.5.9"
    assert receipt["default_gui_launch"]["process_cleaned_up"] is True
    assert receipt["documented_gui_command"]["result"] == "FAIL"
    assert "No module named PySide6" in receipt["documented_gui_command"]["failure"]
    assert repaired["owner_requirement"] == "HPC-W01-TODO-CLI-SURFACE-001"
    assert repaired["artifact"]["sha256"] != receipt["guest"]["candidate_sha256_verified"]
    assert repaired["gui_command"]["visible_main_window"] is True
    assert repaired["gui_command"]["window_title"] == "HPC Client GUI 1.5.9"
    assert repaired["gui_command"]["closed_gracefully"] is True
    assert repaired["gui_command"]["force_terminated"] is False
    assert "not current guest REL-025 proof" in historical.splitlines()[0]
    assert "Slice verdict: **PASS on the U02.1 slice**" not in historical
    assert "does not satisfy `HPC-W11-REL-025`" in historical


def test_release_rollback_handoff_covers_integrity_migration_and_not_ready_case() -> None:
    guidance = (_root() / "docs/VERIFYING_RELEASES.md").read_text(encoding="utf-8-sig")
    assert "## 6. Release rollback" in guidance, "release rollback procedure is missing"
    rollback = guidance.split("## 6. Release rollback", maxsplit=1)[1]

    assert "disable or withdraw the affected download" in rollback
    assert "published manifest, SHA-256, and provenance" in rollback
    assert "configuration migrations" in rollback
    assert "Rollback is not ready when no previously verified compatible release" in rollback
    assert "A repository-local older candidate" in rollback
