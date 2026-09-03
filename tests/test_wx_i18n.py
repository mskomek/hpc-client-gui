import json
from pathlib import Path

from hpc_gui.core.i18n import _flatten_keys, load_language, t


def test_translation_key_sets_match_for_wx_surfaces():
    root = Path("src/hpc_gui/i18n")
    english = json.loads((root / "en.json").read_text(encoding="utf-8"))
    turkish = json.loads((root / "tr.json").read_text(encoding="utf-8"))
    assert _flatten_keys(english) == _flatten_keys(turkish)

    for language in ("en", "tr"):
        load_language(language)
        for key in ("common.close", "help.section_terminal", "jobs.open_output"):
            assert t(key) != f"[{key}]"
