from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from truba_gui.config import storage


def test_save_config_writes_json_atomically_and_leaves_no_temp(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    payload = {"profiles": [], "settings": {"name": "TRÜBA", "count": 2}}
    with patch("truba_gui.config.storage._config_path", return_value=config):
        storage.save_config(payload)
    assert config.exists()
    assert json.loads(config.read_text(encoding="utf-8")) == payload
    assert config.read_text(encoding="utf-8") == json.dumps(
        payload, ensure_ascii=False, indent=2
    )
    assert list(tmp_path.iterdir()) == [config]


def test_save_config_failure_preserves_previous_and_cleans_temp(tmp_path: Path) -> None:
    config = tmp_path / "config.json"
    previous = '{"profiles": [], "settings": {"keep": true}}'
    config.write_text(previous, encoding="utf-8")
    with (
        patch("truba_gui.config.storage._config_path", return_value=config),
        patch("os.replace", side_effect=OSError("boom")),
    ):
        with pytest.raises(OSError):
            storage.save_config({"profiles": [], "settings": {"keep": False}})
    assert config.read_text(encoding="utf-8") == previous
    assert list(tmp_path.iterdir()) == [config]
