"""Plugin installer tests: Payload path validation and exact-file downloads."""

from __future__ import annotations

import pytest

from plugin_installer_test_support import (
    DownloadError,
    OFFICIAL_RAW_BASE,
    Path,
    download_exact_file,
    make_fetcher,
    payload_url,
    sha256_bytes,
    validate_payload_rel_path,
)



@pytest.mark.parametrize(
    "bad",
    [
        "",
        "../escape.json",
        "a/../../b.json",
        "/absolute.json",
        "C:\\evil.json",
        "%2e%2e%2fescape.json",
        "file\0.txt",
        "a//b.json",
    ],
)
@pytest.mark.contract
def test_unsafe_payload_paths_rejected(bad):
    with pytest.raises(DownloadError):
        validate_payload_rel_path(bad)


@pytest.mark.contract
def test_payload_url_requires_official_https_base():
    url = payload_url("plugins/truba/1.0.0/cluster-profile.json")
    assert url.startswith("https://raw.githubusercontent.com/")
    with pytest.raises(DownloadError):
        payload_url("x.json", raw_base="http://insecure.example/")


@pytest.mark.unit
def test_download_exact_file_verifies_hash_and_size(tmp_path: Path):
    payload = b'{"hello": "world"}'
    fetcher = make_fetcher(
        {OFFICIAL_RAW_BASE + "data/file.json": payload}
    )
    destination = download_exact_file(
        rel_path="data/file.json",
        destination_dir=tmp_path,
        expected_sha256=sha256_bytes(payload),
        expected_size=len(payload),
        fetcher=fetcher,
    )
    assert destination.read_bytes() == payload
    assert not list(tmp_path.rglob("*.part"))

    with pytest.raises(DownloadError, match="SHA-256"):
        download_exact_file(
            rel_path="data/file.json",
            destination_dir=tmp_path / "bad-hash",
            expected_sha256="0" * 64,
            fetcher=fetcher,
        )

    with pytest.raises(DownloadError, match="unexpected size"):
        download_exact_file(
            rel_path="data/file.json",
            destination_dir=tmp_path / "bad-size",
            expected_sha256=sha256_bytes(payload),
            expected_size=len(payload) + 5,
            fetcher=fetcher,
        )


@pytest.mark.unit
def test_download_missing_file_raises(tmp_path: Path):
    with pytest.raises(DownloadError):
        download_exact_file(
            rel_path="missing.json",
            destination_dir=tmp_path,
            expected_sha256="0" * 64,
            fetcher=make_fetcher({}),
        )
