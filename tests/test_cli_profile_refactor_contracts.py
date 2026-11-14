"""Headless invariants while retaining the existing develop CLI modularization.

The stale branch uses a different split, so code is not copied wholesale.
"""

from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from hpc_gui.cli import _profile_commands as commands
from hpc_gui.cli.errors import ExitCode


pytestmark = pytest.mark.unit


def _args(action: str, **values):
    defaults = dict(
        profile_command=action, name="cluster", format="json",
        quiet=False, yes=False, host=None, port=None, username=None,
        key_path=None, host_key_policy=None,
    )
    defaults.update(values)
    return SimpleNamespace(**defaults)


def test_list_never_exposes_stored_passwords(monkeypatch, capsys):
    monkeypatch.setattr(commands, "load_profiles", lambda: [
        {"name": "cluster", "password": "SECRET_NEVER_PRINT", "password_enc": "PRIVATE"},
    ])
    assert commands._run_profile(_args("list")) == ExitCode.SUCCESS
    assert json.loads(capsys.readouterr().out) == ["cluster"]


def test_show_excludes_password_and_plugin_metadata(monkeypatch, capsys):
    monkeypatch.setattr(commands, "resolve_profile", lambda _name: {
        "name": "cluster", "host": "login.example", "id": "stable-id",
        "password_enc": "SECRET_NEVER_PRINT", "plugin_meta": {"token": "PRIVATE"},
    })
    assert commands._run_profile(_args("show")) == ExitCode.SUCCESS
    displayed = json.loads(capsys.readouterr().out)
    assert displayed == {"name": "cluster", "host": "login.example"}


def test_update_preserves_stable_id_and_unknown_fields(monkeypatch, capsys):
    original = {
        "name": "cluster", "id": "stable-id", "host": "old.example",
        "password_enc": "ENC", "plugin_meta": {"future_key": True},
    }
    saved = []
    monkeypatch.setattr(commands, "resolve_profile", lambda _name: original.copy())
    monkeypatch.setattr(commands, "upsert_profile", saved.append)
    assert commands._run_profile(_args("update", host="new.example")) == ExitCode.SUCCESS
    assert saved[0]["host"] == "new.example"
    assert saved[0]["id"] == "stable-id"
    assert saved[0]["password_enc"] == "ENC"
    assert saved[0]["plugin_meta"] == {"future_key": True}
    displayed = json.loads(capsys.readouterr().out)
    assert displayed["host"] == "new.example"
    assert "password_enc" not in displayed


def test_delete_requires_explicit_confirmation(monkeypatch, capsys):
    deleted = []
    monkeypatch.setattr(commands, "delete_profile", deleted.append)
    monkeypatch.setattr(commands, "resolve_profile", lambda _name: {"name": "cluster"})
    assert commands._run_profile(_args("delete")) == ExitCode.USAGE
    assert deleted == []
    assert "without --yes" in (capsys.readouterr().out + capsys.readouterr().err)
