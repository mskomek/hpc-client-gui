from __future__ import annotations

from hpc_gui.services.provider_profile_diff import apply_provider_to_connection, build_provider_profile_diff


def _profile(**changes):
    value = {
        "profile_id": "example",
        "access": {"auth_methods": ["key"]},
        "scheduler_hints": {"partitions": ["short"]},
        "requirements": {"project": {"required": True}},
        "storage": [{"id": "home", "kind": "home", "path_template": "/home/{user}"}],
        "quota_sources": [{"id": "q", "backend_id": "reviewed", "enabled": True}],
        "metadata": {"documentation_url": "https://example.test/docs", "last_verified": "2026-09-01"},
    }
    value.update(changes)
    return value


def test_no_change_and_semantic_changes():
    same = build_provider_profile_diff(_profile(), _profile(), from_version="1", to_version="1")
    assert not same.changed
    changed = build_provider_profile_diff(
        _profile(),
        _profile(
            access={"auth_methods": ["ssh-certificate"]},
            scheduler_hints={"partitions": ["long"]},
            storage=[{"id": "scratch", "kind": "scratch", "path_template": "/scratch/{project}"}],
        ),
    )
    assert {change.section for change in changed.changes} == {"auth", "partitions", "storage"}
    assert "key" not in " ".join(changed.summary()) or "ssh-certificate" in " ".join(changed.summary())


def test_snapshot_is_unchanged_until_explicit_apply():
    old = {"name": "saved", "provider_template": {"version": "1"}}
    new = {"version": "2", "secret_token": "must-not-be-copied"}
    assert apply_provider_to_connection(old, new) == old
    applied = apply_provider_to_connection(old, new, confirmed=True)
    assert applied["provider_template"] == new
