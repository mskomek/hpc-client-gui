"""SSH credential-flow regression tests (SSH-1 .. SSH-12).

The original regression: Save & Connect cleared the typed password before the
connection attempt when "remember password" was off, so Paramiko received no
credential and raised "No authentication methods available". These tests
assert the actual credential crossing each boundary and the absence of
persisted/leaked secrets, not just that a callback returned True.
"""

from __future__ import annotations

pytest_plugins = ('support.test_ssh_credential_flow_shared',)
from support.test_ssh_credential_flow_shared import (
    ConnectionDialog,
    LoginWidget,
    _ConnectionAuthStrategy,
    _KeyboardInteractiveSource,
    _PasswordSource,
    _run_worker,
    normalize_auth_methods,
    pytest,
)

@pytest.mark.unit
def test_ssh_9_keyboard_interactive_metadata_reaches_conn_info(monkeypatch):
    settings = {
        "provider_template": {"access": {"auth_methods": ["keyboard-interactive"]}}
    }
    conn = _run_worker(monkeypatch, {"system_settings": settings})
    assert conn.keyboard_interactive_handler is not None
    assert normalize_auth_methods(settings) == ("keyboard-interactive",)

@pytest.mark.unit
def test_ssh_10_password_plus_keyboard_interactive_available(monkeypatch):
    settings = {
        "provider_template": {
            "access": {"auth_methods": ["password", "keyboard-interactive"]}
        }
    }
    conn = _run_worker(monkeypatch, {"password": "pw", "system_settings": settings})
    assert conn.password == "pw"
    assert conn.keyboard_interactive_handler is not None
    sources = list(_ConnectionAuthStrategy(conn).get_sources())
    kinds = [type(source) for source in sources]
    assert _PasswordSource in kinds
    assert _KeyboardInteractiveSource in kinds

@pytest.mark.unit
def test_ssh_11_unknown_auth_methods_are_ignored_and_not_executable(monkeypatch):
    settings = {
        "provider_template": {
            "access": {"auth_methods": ["password", "telnet", "exec", "publickey;rm -rf /"]}
        }
    }
    assert normalize_auth_methods(settings) == ("password",)
    conn = _run_worker(monkeypatch, {"system_settings": settings})
    assert conn.keyboard_interactive_handler is None

    legacy = {"access": {"auth_methods": ["keyboard-interactive", "bogus"]}}
    assert normalize_auth_methods(legacy) == ("keyboard-interactive",)

@pytest.mark.gui
@pytest.mark.qt
def test_ssh_9b_plugin_access_metadata_survives_dialog_to_login_chain(qt_app):
    """Provider access metadata must survive the full Path:
    plugin template -> ConnectionDialog provider_template -> profile -> login
    system settings -> keyboard-interactive handler.
    """
    from hpc_gui.plugins.templates import PluginSystemTemplate

    template = PluginSystemTemplate(
        settings={"name": "TRUBA"},
        provenance={"kind": "plugin", "plugin_id": "org.hpcclient.truba"},
        structured={
            "schema_version": 3,
            "access": {"auth_methods": ["password", "keyboard-interactive"]},
        },
    )
    dialog = ConnectionDialog()
    try:
        dialog._apply_system_template(
            dict(template.settings), dict(template.provenance), dict(template.structured)
        )
        collected = dialog._collect_profile()
    finally:
        dialog.deleteLater()
    assert collected is not None
    assert collected["provider_template"]["access"]["auth_methods"] == [
        "password",
        "keyboard-interactive",
    ]

    login = LoginWidget()
    try:
        login._load_profile_into_fields(collected)
        assert normalize_auth_methods(login._profile_system_settings) == (
            "password",
            "keyboard-interactive",
        )
    finally:
        login.deleteLater()
