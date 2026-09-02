from pathlib import Path

from hpc_gui.services.gesture_help import load_gesture_help


def test_gesture_help_is_generated_from_contract():
    rows = load_gesture_help()
    ids = {row.id for row in rows}
    assert len(rows) >= 20
    assert len(ids) == len(rows)
    assert "GUI-FILE-014" in ids
    assert "GUI-XFER-010" in ids
    assert "GUI-JOBS-010" in ids
    assert any(row.id == "GUI-EDIT-013" and "No current" in row.behavior for row in rows)


def test_gesture_help_keeps_directories_jobs_difference_and_no_new_gesture_source():
    rows = load_gesture_help(Path("docs/v2/GUI_POINTER_INTERACTION_CONTRACT.md"))
    jobs = next(row for row in rows if row.id == "GUI-JOBS-010")
    assert "Directories" in jobs.behavior and "Jobs" in jobs.behavior
    assert not any(row.gesture.startswith("Added") for row in rows)
