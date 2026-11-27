from __future__ import annotations

import json

from hpc_gui.config import storage


def test_file_associations_persist_and_preserve_profiles(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    monkeypatch.setattr("hpc_gui.config._storage_core._config_path", lambda: config_path)
    storage.save_config({"profiles": [{"name": "keep"}], "settings": {"other": 7}})

    assert storage.get_file_associations() == {}
    assert storage.set_file_association("slurm", "C:/tools/editor.exe") == {
        ".slurm": "C:/tools/editor.exe"
    }
    assert storage.get_file_association(".SLURM") == "C:/tools/editor.exe"
    assert json.loads(config_path.read_text(encoding="utf-8"))["profiles"] == [{"name": "keep"}]

    assert storage.clear_file_association("slurm") == {}
    assert storage.get_file_associations() == {}
    saved = json.loads(config_path.read_text(encoding="utf-8"))
    assert saved["settings"]["other"] == 7
    assert saved["settings"]["file_associations"] == {}
    assert saved["profiles"] == [{"name": "keep"}]
