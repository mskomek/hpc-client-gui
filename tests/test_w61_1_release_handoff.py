"""Regression checks for W61.1's release-gate and rollback handoff text."""

from __future__ import annotations

import os
from pathlib import Path


def _root() -> Path:
    override = os.environ.get("W61_1_HANDOFF_ROOT")
    return Path(override).resolve() if override else Path(__file__).resolve().parents[1]


def _section(text: str, heading: str, next_heading: str) -> tuple[str, str]:
    start = text.index(heading)
    end = text.index(next_heading, start + len(heading))
    return text[start:end], heading


def test_w611_rel025_history_cannot_be_misrepresented_as_guest_pass() -> None:
    report = (_root() / "docs/wave-reports/v2/opencode/W61.1_WAVE_REPORT.md").read_text(
        encoding="utf-8-sig"
    )
    current, _ = _section(
        report,
        "## U02.1 current clean-launch result",
        "## Current requirement status reconciliation",
    )
    current_historical_heading = "## Historical host-side packaged wx smoke"
    stale_guest_heading = "## section-runtime-smoke-launch (U02.1: REL-025 packaged wx clean launch)"
    assert current_historical_heading in report, "host smoke must be labelled historical"
    assert stale_guest_heading not in report, "host smoke is being presented as a guest launch"
    historical, _ = _section(
        report,
        current_historical_heading,
        "## section-runtime-smoke-gj",
    )

    assert "0x80070005" in current
    assert "No guest archive or candidate was created, extracted, or launched" in current
    assert "BLOCKED_ENV" in current
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
