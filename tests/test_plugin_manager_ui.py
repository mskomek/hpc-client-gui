"""Portable plugin request and translation contracts; native lifecycle lives in wx tests."""
import pytest

from hpc_gui.core.i18n import load_language, t
from hpc_gui.services.plugin_request import PLUGIN_REQUEST_URL, is_allowed_plugin_request_url


@pytest.mark.unit
def test_request_plugin_action_targets_dedicated_issue_form():
    assert PLUGIN_REQUEST_URL == (
        "https://github.com/mskomek/hpc-client-gui-plugins/issues/new"
        "?template=plugin-request.yml"
    )
    assert is_allowed_plugin_request_url(PLUGIN_REQUEST_URL)
    assert not is_allowed_plugin_request_url("https://evil.example.com/x")


@pytest.mark.contract
def test_i18n_keys_resolve_in_both_languages():
    for language in ("en", "tr"):
        load_language(language)
        try:
            for key in (
                "plugins.action", "plugins.tab_discover", "plugins.tab_installed",
                "plugins.tab_updates", "plugins.install", "plugins.installing",
                "plugins.update", "plugins.remove", "plugins.refresh",
                "plugins.status_offline", "plugins.registry_unavailable",
                "plugins.verification_failed", "plugins.incompatible",
                "plugins.publisher", "plugins.version", "plugins.license",
                "plugins.capabilities", "plugins.cluster_commands_warning",
                "plugins.details",
            ):
                value = t(key)
                assert value and value not in (key, f"[{key}]"), f"missing key {key} for {language}"
        finally:
            load_language("en")
