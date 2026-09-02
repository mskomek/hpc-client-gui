from hpc_gui.core.i18n import load_language
from hpc_gui.services.help_search import HelpSearchIndex


def test_cross_type_search_and_context_disambiguation():
    load_language("en")
    index = HelpSearchIndex()
    ctrl_z = index.search("ctrl z")
    assert {result.context for result in ctrl_z} >= {"editor", "remote_files", "terminal"}
    assert index.search("middle click", context="files")[0].id == "pointer.middle-click-folder"
    assert any(result.id == "editor.execute" for result in index.search("submit", context="editor"))


def test_no_results_and_localized_titles():
    index = HelpSearchIndex()
    assert index.search("does-not-exist") == ()
    load_language("tr")
    assert index.search("bağlantı")
