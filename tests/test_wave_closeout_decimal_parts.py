"""Decimal split parts (W57.1) resolve to their own Wave, not to their base number."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "validate_wave_closeout.py"


def test_decimal_parts_are_distinct_waves(tmp_path):
    spec = importlib.util.spec_from_file_location("closeout", SCRIPT)
    closeout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(closeout)
    pending = tmp_path / "waves" / "pending"
    pending.mkdir(parents=True)
    for name in ("W56.md", "W57.1.md", "W57.2.md"):
        (pending / name).write_text("---\nwave_id: x\n---\n", encoding="utf-8")
    profile = {"wave": {"file_regex": r"^W(?P<number>\d{2})(?:\.(?P<part>[1-9]))?\.md$", "id_format": "W{number:02d}"},
               "paths": {"done": "waves/done", "pending": "waves/pending", "blocked": "waves/blocked",
                         "postponed": "waves/postponed"}}
    found = closeout._canonical_wave_files(tmp_path, profile)
    assert set(found) == {"W56", "W57.1", "W57.2"}
    assert found["W57.1"].name == "W57.1.md"
