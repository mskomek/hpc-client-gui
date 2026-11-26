"""Qt-free contracts for the FTP test backends."""

from support.ftp_widget_backend_fakes import _CountingFiles, _Files


def test_memory_backend_round_trips_upload_download_and_metadata(tmp_path):
    source = tmp_path / "payload.txt"
    target = tmp_path / "downloaded.txt"
    source.write_bytes(b"payload")

    files = _Files()
    files.upload(str(source), "/remote/payload.txt")
    files.download("/remote/payload.txt", str(target))

    assert target.read_bytes() == b"payload"
    assert files.exists("/remote/payload.txt")
    assert files.stat("/remote/payload.txt") == (7, 1)
    assert files.listdir_entries("/remote")[0].path == "/remote/payload.txt"


def test_counting_backend_tracks_directory_reads():
    files = _CountingFiles()

    assert [entry.name for entry in files.listdir_entries("/remote")] == [
        "child",
        "root.txt",
    ]
    assert files.calls == ["/remote"]
