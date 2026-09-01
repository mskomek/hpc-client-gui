import hashlib

import pytest

from hpc_gui.services.transfer_integrity import (
    VerificationCancelled,
    VerificationState,
    sha256_file,
    verify_transfer,
)


def test_streaming_match_and_mismatch(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"data" * 1000)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    assert verify_transfer(path, digest).state is VerificationState.VERIFIED
    assert verify_transfer(path, "0" * 64).state is VerificationState.FAILED


def test_unsupported_and_cancellable(tmp_path):
    path = tmp_path / "data.bin"
    path.write_bytes(b"data")
    assert verify_transfer(path, None).state is VerificationState.UNSUPPORTED
    with pytest.raises(VerificationCancelled):
        sha256_file(path, cancel=lambda: True)


def test_large_stream_reports_progress(tmp_path):
    path = tmp_path / "large.bin"
    path.write_bytes(b"x" * (2 * 1024 * 1024 + 1))
    progress = []
    digest = sha256_file(path, progress=lambda done, total: progress.append((done, total)))
    assert digest == hashlib.sha256(path.read_bytes()).hexdigest()
    assert progress[-1] == (path.stat().st_size, path.stat().st_size)
