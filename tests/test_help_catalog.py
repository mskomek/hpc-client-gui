from hpc_gui.core.i18n import load_language
from hpc_gui.services.help_catalog import HELP_CATALOG, is_allowed_external_url


def test_structured_help_sections_search_and_missing_binding():
    load_language("en")
    topics = HELP_CATALOG.topics()
    assert len(topics) == 11
    assert len({topic.id for topic in topics}) == len(topics)
    assert HELP_CATALOG.search("mouse")[0].id == "help.mouse-gestures"
    assert "Unbound" in HELP_CATALOG.render("help.editor", lambda _command_id: None)


def test_external_links_are_https_and_allowlisted():
    assert is_allowed_external_url("https://docs.example.test/help", {"docs.example.test"})
    assert not is_allowed_external_url("http://docs.example.test/help", {"docs.example.test"})
    assert not is_allowed_external_url("https://other.example.test/help", {"docs.example.test"})
