from hpc_gui.services.cineca_quota import parse_cineca_cinquota


def test_cinquota_parser_reads_work_row_and_file_count():
    result = parse_cineca_cinquota(
        "Filesystem used quota grace files\n"
        "/leonardo/home/user 22.66G 50G - 194295\n"
        "/leonardo_work/project 366.3G 1T - 548665\n"
    )
    assert result.storage_id == "work"
    assert result.used_bytes == 366_300_000_000
    assert result.soft_limit_bytes == 1_000_000_000_000
    assert result.used_files == 548665


def test_cinquota_parser_rejects_unstructured_output():
    import pytest

    with pytest.raises(ValueError):
        parse_cineca_cinquota("cinQuota failed")
