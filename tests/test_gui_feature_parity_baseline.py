from pathlib import Path
import re


def test_gui_feature_parity_ids_are_unique_and_cover_required_surfaces():
    path = Path(__file__).parents[1] / "docs" / "v2" / "GUI_FEATURE_PARITY_BASELINE.md"
    ids = re.findall(r"\bGUI-[A-Z]+-\d{3}\b", path.read_text(encoding="utf-8"))
    assert len(ids) == len(set(ids))
    for prefix in ("GUI-CONN-", "GUI-TERM-", "GUI-FILE-", "GUI-XFER-", "GUI-JOBS-", "GUI-EDIT-", "GUI-PLUGIN-", "GUI-HELP-"):
        assert any(item.startswith(prefix) for item in ids)
