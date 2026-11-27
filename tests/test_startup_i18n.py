"""Startup text is available before any saved preferences are loaded."""
from __future__ import annotations

import pytest

from hpc_gui.core import i18n


@pytest.mark.unit
@pytest.mark.parametrize("language", ["en", "tr"])
def test_wx_startup_labels_resolve_in_both_languages(language):
    previous = i18n.current_language()
    try:
        i18n.load_language(language)
        for key in ("splash.starting", "splash.checking_updates", "splash.loading_preferences",
                    "splash.checking_helpers", "updates.skip_updates"):
            value = i18n.t(key)
            assert value and value != f"[{key}]", (language, key)
    finally:
        i18n.load_language(previous)
