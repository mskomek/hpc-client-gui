from hpc_gui.config.system_profile import (
    ProviderContext,
    format_remote_path,
    resolve_provider_path,
)


def test_provider_context_resolves_all_application_placeholders():
    result = resolve_provider_path(
        "/p/{user_first}/{user}/{project}/{account}",
        ProviderContext(user="alice", project="proj", account="acct"),
    )
    assert result == result.__class__("resolved", "/p/a/alice/proj/acct")


def test_provider_context_fails_closed_for_missing_or_unknown_values():
    missing = resolve_provider_path("/p/{project}", ProviderContext(user="alice"))
    assert missing.state == "missing-context" and missing.missing == ("project",)
    invalid = resolve_provider_path("/p/{secret}", ProviderContext(user="alice"))
    assert invalid.state == "invalid-template" and invalid.path == "/p/{secret}"


def test_legacy_formatter_still_resolves_truba_style_paths():
    assert format_remote_path("/arf/home/{user}", "mkomek") == "/arf/home/mkomek"
