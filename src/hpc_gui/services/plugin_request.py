"""Framework-neutral plugin-request destination (W44).

The dedicated plugin-request issue form URL is a shared constant consumed
by both the Qt plugin-manager dialog and the wx shell dispatch. It lives
here — outside ``hpc_gui.ui.*`` and without any Qt import — so the wx
runtime can obtain it without importing Qt UI modules (ARCH-QT-WX-002).
"""

from __future__ import annotations

# Dedicated plugin-request issue form in the official plugin registry repo.
# This is the only destination the "Request a plugin" action may open; it is
# a fixed constant and is never built from registry-controlled fields.
PLUGIN_REQUEST_URL = (
    "https://github.com/mskomek/hpc-client-gui-plugins/issues/new"
    "?template=plugin-request.yml"
)


def is_allowed_plugin_request_url(url: str) -> bool:
    """Return True only for the exact fixed plugin-request destination."""
    return url == PLUGIN_REQUEST_URL
