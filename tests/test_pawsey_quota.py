from hpc_gui.services.pawsey_quota import parse_pawsey_account_balance


def test_pawsey_account_balance_parser_reads_software_usage_and_files():
    result = parse_pawsey_account_balance(
        "Filesystem Usage user Usage project % used Files user % files\n"
        "/scratch 1.99 TiB 417.43 GiB 0.0 (project) 192558 19.3 (user)\n"
        "/software 124.66 GiB 161.37 GiB 63.0 (project) 43308 43.3 (user)\n"
    )
    assert result.storage_id == "software"
    assert result.used_bytes == int(124.66 * 1024**3)
    assert result.soft_limit_bytes == int(161.37 * 1024**3)
    assert result.used_files == 43308
