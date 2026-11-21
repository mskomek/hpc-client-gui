"""Explicit trusted-X11 profile choices reach the wx SSH session model."""

from __future__ import annotations

from types import SimpleNamespace

import pytest


pytestmark = [pytest.mark.gui, pytest.mark.wx]


def test_trusted_profile_choice_reaches_paramiko_connection_info():
    from hpc_gui.wx_connection_model import ssh_info_from_profile

    model = SimpleNamespace(answer_keyboard_interactive=lambda _request: [])
    info = ssh_info_from_profile(
        {
            "host": "localhost",
            "username": "tester",
            "x11_forwarding": True,
            "x11_trusted": True,
        },
        model,
    )
    assert info.x11_forwarding is True
    assert info.x11_trusted is True
