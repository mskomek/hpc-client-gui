"""Wave 04 tests: registry client, exact-file downloader, and installer.

All tests use injected fetchers (URL -> bytes); nothing touches the network.
"""

from __future__ import annotations
from support.test_plugin_installer_shared import (
    DownloadError,
    InstallError,
    OFFICIAL_RAW_BASE,
    Path,
    _assert_no_staging_or_part_leftovers,
    download_exact_file,
    full_install_responses,
    install_plugin_from_registry,
    json,
    make_fetcher,
    make_registry_entry,
    packages_dir,
    payload_url,
    pytest,
    read_active_versions,
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

@pytest.mark.integration
def test_only_declared_files_are_downloaded(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()

    def counting_fetch(url: str, max_bytes: int) -> bytes:
        assert url in responses, f"unexpected download of {url}"
        return responses[url]

    entry = make_registry_entry(manifest, manifest_bytes)
    install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=counting_fetch
    )

@pytest.mark.contract
def test_incompatible_app_rejected_before_download(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses(requires_app=">=99.0.0")

    def refusing_fetch(url: str, max_bytes: int) -> bytes:
        raise AssertionError(f"must not download {url}")

    entry = make_registry_entry(manifest, manifest_bytes)
    with pytest.raises(InstallError):
        install_plugin_from_registry(
            entry, root=tmp_path, app_version="1.3.0", fetcher=refusing_fetch
        )

@pytest.mark.integration
def test_conflicting_same_version_payload_is_rejected(tmp_path: Path):
    responses, manifest, manifest_bytes = full_install_responses()
    entry = make_registry_entry(manifest, manifest_bytes)
    install_plugin_from_registry(
        entry, root=tmp_path, app_version="1.4.0", fetcher=make_fetcher(responses)
    )

    # A different payload published under the same immutable version.
    conflicting, conflicting_bytes, _ = full_install_responses(
        plugin_id="org.hpcclient.truba", version="1.0.0"
    )
    tampered_profile = json.loads(conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/cluster-profile.json"])
    tampered_profile["description"] = "A completely different payload."
    new_profile_bytes = json.dumps(tampered_profile).encode("utf-8")
    conflicting_manifest = json.loads(conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/manifest.json"])
    conflicting_manifest["files"][0]["sha256"] = sha256_bytes(new_profile_bytes)
    conflicting_manifest["files"][0]["size"] = len(new_profile_bytes)
    conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/cluster-profile.json"] = new_profile_bytes
    new_manifest_bytes = json.dumps(conflicting_manifest).encode("utf-8")
    conflicting[OFFICIAL_RAW_BASE + "plugins/truba/1.0.0/manifest.json"] = new_manifest_bytes
    conflicting_entry = make_registry_entry(conflicting_manifest, new_manifest_bytes)

    with pytest.raises(InstallError, match="immutable|conflict"):
        install_plugin_from_registry(
            conflicting_entry,
            root=tmp_path,
            app_version="1.4.0",
            fetcher=make_fetcher(conflicting),
        )

    # The previously active version is intact and still active.
    assert read_active_versions(tmp_path) == {"org.hpcclient.truba": "1.0.0"}
    kept = json.loads(
        (packages_dir(tmp_path) / "org.hpcclient.truba" / "1.0.0" / "cluster-profile.json").read_text("utf-8")
    )
    assert "description" not in kept or kept.get("description") != "A completely different payload."
    _assert_no_staging_or_part_leftovers(tmp_path)
