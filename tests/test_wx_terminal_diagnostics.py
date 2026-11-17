"""Privacy contract for opt-in terminal acceptance diagnostics."""

from __future__ import annotations

import json

from hpc_gui.wx_terminal_diagnostics import record_terminal_event


def test_terminal_diagnostics_are_disabled_without_opt_in(monkeypatch, tmp_path):
    target = tmp_path / "terminal.jsonl"
    monkeypatch.delenv("HPC_GUI_TERMINAL_DIAGNOSTICS_FILE", raising=False)

    record_terminal_event("terminal-ready", ready=True)

    assert not target.exists()


def test_terminal_diagnostics_keep_only_safe_metadata(monkeypatch, tmp_path):
    target = tmp_path / "nested" / "terminal.jsonl"
    monkeypatch.setenv("HPC_GUI_TERMINAL_DIAGNOSTICS_FILE", str(target))

    record_terminal_event(
        "terminal-input-result",
        callback=True,
        accepted=False,
        channel_active=False,
        marker_visible=True,
        is_parity=True,
        password="must not be logged",
        input_data="must not be logged",
    )

    record = json.loads(target.read_text(encoding="utf-8"))
    assert record["event"] == "terminal-input-result"
    assert record["metadata"] == {
        "callback": True,
        "accepted": False,
        "channel_active": False,
        "marker_visible": True,
        "is_parity": True,
    }
    assert "must not be logged" not in target.read_text(encoding="utf-8")
