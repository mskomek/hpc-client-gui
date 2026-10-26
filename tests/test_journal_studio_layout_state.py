from __future__ import annotations

from hpc_gui import wx_journal_studio_layout_state as layout_state


def test_load_journal_studio_layout_accepts_valid_values(monkeypatch):
    monkeypatch.setattr(
        layout_state,
        "load_config",
        lambda: {
            "ui": {
                "journal_studio_layout": {
                    "structure_ratio": 0.21,
                    "library_ratio": 0.73,
                    "results_tab": 2,
                }
            }
        },
    )

    assert layout_state.load_journal_studio_layout() == {
        "structure_ratio": 0.21,
        "library_ratio": 0.73,
        "results_tab": 2,
    }


def test_load_journal_studio_layout_discards_invalid_values(monkeypatch):
    monkeypatch.setattr(
        layout_state,
        "load_config",
        lambda: {
            "ui": {
                "journal_studio_layout": {
                    "structure_ratio": 0.99,
                    "library_ratio": float("nan"),
                    "results_tab": 8,
                }
            }
        },
    )

    assert layout_state.load_journal_studio_layout() == {}


def test_save_journal_studio_layout_preserves_other_preferences(monkeypatch):
    config = {"ui": {"main_window": {"width": 1440}, "theme": "dark"}}
    saved = {}
    monkeypatch.setattr(layout_state, "load_config", lambda: config)
    monkeypatch.setattr(layout_state, "save_config", lambda value: saved.update(value))

    assert layout_state.save_journal_studio_layout(
        {"structure_ratio": 0.2, "library_ratio": 0.7, "results_tab": 3}
    )

    assert saved["ui"]["main_window"] == {"width": 1440}
    assert saved["ui"]["theme"] == "dark"
    assert saved["ui"]["journal_studio_layout"] == {
        "structure_ratio": 0.2,
        "library_ratio": 0.7,
        "results_tab": 3,
    }


def test_save_journal_studio_layout_rejects_empty_or_unsafe_values(monkeypatch):
    calls = []
    monkeypatch.setattr(layout_state, "load_config", lambda: {})
    monkeypatch.setattr(layout_state, "save_config", calls.append)

    assert not layout_state.save_journal_studio_layout(
        {"structure_ratio": 0.99, "results_tab": -1}
    )
    assert calls == []
