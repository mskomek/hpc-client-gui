from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pytest

from local_transfer_gate import (
    SCHEMA,
    TURKISH_FILENAME,
    run_sftp_smoke_gate,
    run_turkish_round_trip,
    save_artifact,
)


def test_turkish_round_trip_passes_with_exact_byte_and_name_equality() -> None:
    result = run_turkish_round_trip()

    assert result["status"] == "PASS"
    assert result["gate"] == "turkish_round_trip"
    assert result["filename"] == TURKISH_FILENAME
    assert result["bytes_verified"] > 0


def test_sftp_smoke_gate_passes_and_saves_artifact_with_schema(tmp_path) -> None:
    version_dir = tmp_path / "v1.0.0"
    version_dir.mkdir()

    report = run_sftp_smoke_gate(temp_dir_name=lambda: "smoke_dir")
    assert report["status"] == "PASS"

    target = save_artifact(report, release_root=str(tmp_path), version="1.0.0")
    assert target == version_dir / "sftp-smoke.json"

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema"] == "sftp-smoke/1"
    assert payload["schema"] == SCHEMA
    assert payload["status"] == "PASS"
    assert payload["temp_dir"] == "smoke_dir"


def test_save_artifact_refuses_to_overwrite_existing_file(tmp_path) -> None:
    version_dir = tmp_path / "v1.0.0"
    version_dir.mkdir()
    target = version_dir / "sftp-smoke.json"
    target.write_bytes(b"ORIGINAL")

    report = run_sftp_smoke_gate(temp_dir_name=lambda: "smoke_dir")
    with pytest.raises(FileExistsError):
        save_artifact(report, release_root=str(tmp_path), version="1.0.0")

    assert target.read_bytes() == b"ORIGINAL"


def test_save_artifact_fails_when_version_directory_is_missing(tmp_path) -> None:
    with pytest.raises(FileNotFoundError):
        save_artifact(
            {"status": "PASS"},
            release_root=str(tmp_path),
            version="9.9.9",
        )
