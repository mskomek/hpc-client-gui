from __future__ import annotations

import builtins
import os

from hpc_gui.services.transfer_resume_store import local_file_identity


def test_local_file_identity_reads_only_bounded_edge_samples(tmp_path, monkeypatch):
    source = tmp_path / "large.bin"
    source.write_bytes(b"x" * (256 * 1024))
    reads: list[int] = []
    real_open = builtins.open

    def tracked_open(path, *args, **kwargs):
        stream = real_open(path, *args, **kwargs)
        if os.fspath(path) == os.fspath(source):
            read = stream.read

            def tracked_read(size: int = -1) -> bytes:
                reads.append(size)
                return read(size)

            stream.read = tracked_read
        return stream

    monkeypatch.setattr(builtins, "open", tracked_open)
    identity = local_file_identity(str(source))

    assert identity["size"] == source.stat().st_size
    assert reads == [64 * 1024, 64 * 1024]
    assert all(0 < size < source.stat().st_size for size in reads)
