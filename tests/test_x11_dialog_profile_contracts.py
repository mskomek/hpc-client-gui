"""Offline contract: explicit X11 trust survives wx profile edit/save."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from hpc_gui.wx_connection_dialog_profile import ConnectionDialogProfileMixin


pytestmark = [pytest.mark.unit, pytest.mark.regression]


class _Control:
    def __init__(self):
        self.value = ""
        self.selection = 0

    def SetValue(self, value):
        self.value = value

    def GetValue(self):
        return self.value

    def SetSelection(self, value):
        self.selection = value

    def GetSelection(self):
        return self.selection


class _Dialog(ConnectionDialogProfileMixin):
    def __init__(self):
        self.controls = {}
        self._initial_profile = {}
        self._provider_template = None
        self._system_template_source = None
        self._template_action_taken = False
        self._wx = SimpleNamespace()
        self._legacy_storage_snapshot = {}

    def __getattr__(self, name):
        control = self.controls.get(name)
        if control is None:
            control = self.controls[name] = _Control()
        return control

    def _update_storage_summary(self):
        pass

    def _load_quota_widgets(self):
        pass

    def _system_form_values(self):
        return {}


@pytest.mark.parametrize("trusted", [False, True])
def test_trusted_choice_survives_profile_round_trip(trusted):
    initial = {
        "name": "Cluster",
        "host": "cluster.example",
        "port": 22,
        "x11_forwarding": True,
        "x11_trusted": trusted,
    }
    dialog = _Dialog()
    dialog._initial_profile = dict(initial)
    dialog._load_profile(initial)
    assert dialog.cb_x11_trusted.GetValue() is trusted

    saved = dialog._collect_profile()
    assert saved is not None
    assert saved["x11_forwarding"] is True
    assert saved["x11_trusted"] is trusted


def test_new_profile_defaults_to_restricted_x11():
    dialog = _Dialog()
    dialog._load_profile({"host": "cluster.example", "port": 22})
    assert dialog.cb_x11_trusted.GetValue() is False
    dialog.cb_x11.SetValue(True)

    profile = dialog._collect_profile()
    assert profile is not None
    assert profile["x11_forwarding"] is True
    assert profile["x11_trusted"] is False
