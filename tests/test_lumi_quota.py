from pathlib import Path

import pytest

from hpc_gui.services.lumi_quota import parse_lumi_quota

pytestmark = pytest.mark.contract


def test_lumi_quota_parser_reads_project_storage_and_file_limits():
    text = (Path(__file__).parent / "fixtures/quota/lumi/quota.txt").read_text()
    result = parse_lumi_quota(text)
    assert result.storage_id == "scratch"
    assert result.used_bytes == 12.5 * 1024**4
    assert result.soft_limit_bytes == 50 * 1024**4
    assert result.used_files == 120000
