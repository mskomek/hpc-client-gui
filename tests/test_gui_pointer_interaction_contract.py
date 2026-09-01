from pathlib import Path
import re


def test_pointer_contract_ids_are_unique_and_map_to_baseline():
    root = Path(__file__).parents[1]
    contract = (root / "docs" / "v2" / "GUI_POINTER_INTERACTION_CONTRACT.md").read_text(encoding="utf-8")
    baseline = (root / "docs" / "v2" / "GUI_FEATURE_PARITY_BASELINE.md").read_text(encoding="utf-8")
    ids = re.findall(r"\bGUI-[A-Z]+-\d{3}\b", contract)
    baseline_ids = set(re.findall(r"\bGUI-[A-Z]+-\d{3}\b", baseline))
    assert len(ids) == len(set(ids))
    assert all(item.rsplit("-", 1)[0] + "-001" in baseline_ids for item in ids)
