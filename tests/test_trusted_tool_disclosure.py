from __future__ import annotations

from hpc_gui.core.i18n import load_language, t
from hpc_gui.wx_plugins import WxPluginManagerModel
import pytest


@pytest.mark.contract
@pytest.mark.semantic
def test_trusted_tool_disclosure_is_localized_and_accurate():
    load_language("en")
    assert "not OS-sandboxed" in t("plugins.trusted_tool_disclosure")
    assert "not OS-sandboxed" in t("plugins.trusted_tool_disclosure_short")
    load_language("tr")
    assert "sandbox" in t("plugins.trusted_tool_disclosure").lower()
    load_language("en")


@pytest.mark.contract
@pytest.mark.semantic
def test_trusted_tool_details_are_disclosed(tmp_path):
    load_language("en")
    model = WxPluginManagerModel(root=tmp_path, app_version="2.0.0")
    model.build_cards_from_registry({"plugins": [{
        "id": "org.hpcclient.ansyslint", "name": "ANSYS Linter", "version": "0.1.0",
        "publisher": "HPC Client GUI", "requires_app": ">=1.5.0",
        "capabilities": ["linter-tool"], "description": "Offline linter",
    }]}, "cache")
    assert t("plugins.trusted_tool_disclosure") in model.details_for(model.cards[0])
