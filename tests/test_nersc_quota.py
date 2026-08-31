import json
from pathlib import Path

import pytest

from hpc_gui.services.nersc_quota import parse_nersc_showquota_json


def test_nersc_json_parser_reads_space_and_inode_quota():
    output = (Path(__file__).parent / "fixtures/quota/nersc/showquota.json").read_text()
    result = parse_nersc_showquota_json(output)
    assert result.used_bytes == 987654321
    assert result.soft_limit_bytes == 21990232555520
    assert result.used_files == 54321
    assert result.soft_limit_files == 10000000


def test_nersc_json_parser_rejects_malformed_or_missing_rows():
    with pytest.raises(ValueError):
        parse_nersc_showquota_json("not json")
    with pytest.raises(ValueError):
        parse_nersc_showquota_json(json.dumps([{"fs": "home"}]))
