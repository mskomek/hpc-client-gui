"""Remote SSH filesystem error translation preserves CLI-facing contracts."""

from __future__ import annotations

import errno

import pytest

from hpc_gui.services.files_ssh_support import _raise_on_failed_run, _translate_remote_errors


pytestmark = pytest.mark.unit


def test_timeout_exit_code_has_distinct_error_class():
    with pytest.raises(TimeoutError, match="sha256sum timed out"):
        _raise_on_failed_run(124, "remote shell timed out", "sha256sum", path="/work/x")


def test_nonzero_missing_path_uses_path_quoted_in_stderr():
    with pytest.raises(FileNotFoundError) as exc:
        _raise_on_failed_run(
            1, "cp: cannot stat '/remote/missing': No such file or directory",
            "cp", path="/remote/source",
        )
    assert exc.value.errno == errno.ENOENT
    assert exc.value.filename == "/remote/missing"


def test_nonzero_permission_error_retains_fallback_path():
    with pytest.raises(PermissionError) as exc:
        _raise_on_failed_run(
            1, "Permission denied", "rm", path="/remote/protected",
        )
    assert exc.value.errno == errno.EACCES
    assert exc.value.filename == "/remote/protected"


def test_nonzero_without_path_keeps_plain_runtime_error():
    with pytest.raises(RuntimeError) as exc:
        _raise_on_failed_run(7, "permission denied", "mkdir")
    assert type(exc.value) is RuntimeError


def test_success_exit_code_does_not_raise():
    _raise_on_failed_run(0, "", "cp", path="/remote/work")


@pytest.mark.parametrize("error_type,number", [
    (FileNotFoundError, errno.ENOENT),
    (PermissionError, errno.EACCES),
])
def test_sftp_error_translation_attaches_remote_path(error_type, number):
    with pytest.raises(error_type) as exc:
        with _translate_remote_errors("/remote/document.txt"):
            raise error_type(number, "remote SFTP failure")
    assert exc.value.filename == "/remote/document.txt"
    assert exc.value.errno == number


def test_ssh_backend_reexports_original_private_helper_contract():
    from hpc_gui.services import files_ssh

    assert files_ssh._raise_on_failed_run is _raise_on_failed_run
    assert files_ssh._translate_remote_errors is _translate_remote_errors
