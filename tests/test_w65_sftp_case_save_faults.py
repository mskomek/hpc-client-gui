"""W65 SFTP-014: staged remote-case save faults over a real SFTP server."""
from __future__ import annotations

import os

import paramiko
import pytest

from hpc_gui.plugin_engines.openfoam_studio.models import CaseDocument
from hpc_gui.plugin_engines.openfoam_studio.remote_case import (
    _RECOVERY_NAME,
    recover_remote_case,
    save_remote_case,
)
from sftp_harness_support import PASSWORD, ROOT_ENV, remote_backend, serve
from hpc_gui.services.files_ssh import SSHFilesBackend
from hpc_gui.ssh.client import SSHClientWrapper
from hpc_gui.ssh.contracts import SSHConnInfo

NAMES = ("system/controlDict", "system/fvSchemes")
DENY = "W65_SFTP_DENY_RENAME"


class _DeadProbeBackend:
    """Delegate to a backend whose artifact probes fail like a dead link.

    The shipped exists() returns False for every error, so this wrapper also
    answers False while stat() raises: a save must still keep its staged
    artifacts recoverable.
    """

    def __init__(self, backend):
        self._backend = backend

    def __getattr__(self, name):
        return getattr(self._backend, name)

    @staticmethod
    def _artifact(path):
        return ".stage" in path or ".backup" in path

    def stat(self, path):
        if self._artifact(path):
            raise TimeoutError("SSH transport is gone")
        return self._backend.stat(path)

    def exists(self, path):
        if self._artifact(path):
            return False
        return self._backend.exists(path)


class _CountingBackend:
    """Delegate to a backend while recording swap and cleanup calls."""

    def __init__(self, backend):
        self._backend = backend
        self.renames = []
        self.removes = []

    def __getattr__(self, name):
        return getattr(self._backend, name)

    def rename(self, src, dst):
        self.renames.append((src, dst))
        return self._backend.rename(src, dst)

    def remove(self, path, recursive=False):
        self.removes.append(path)
        return self._backend.remove(path, recursive=recursive)


@pytest.fixture
def case_root(tmp_path, monkeypatch):
    root = tmp_path / "case"
    for name in NAMES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(f"FoamFile {{ version 2.0; }}\n// {name}\n", encoding="utf-8")
    monkeypatch.setenv(ROOT_ENV, str(root))
    monkeypatch.delenv(DENY, raising=False)
    return root


def _edited(root, name):
    document = CaseDocument.from_bytes(name, "/" + name, (root / name).read_bytes(), remote=True)
    document.set_text(document.text + "edited true; // staged\n")
    assert document.modified
    return document


def _originals(root):
    return {name: (root / name).read_bytes() for name in NAMES}


def _on_disk(root, path):
    return (root / path.lstrip("/")).exists()


def _kinds(paths):
    found = set()
    for path in paths:
        match = _RECOVERY_NAME.fullmatch(path.rsplit("/", 1)[-1])
        if match:
            found.add(match.group("kind"))
    return found


def test_two_file_save_commits_both_documents(case_root):
    documents = {name: _edited(case_root, name) for name in NAMES}
    with serve() as port, remote_backend(port) as backend:
        report = save_remote_case("/", backend, documents)

    assert report.success is True
    assert report.partial is False
    assert sorted(report.saved) == sorted(NAMES)
    assert report.errors == ()
    assert report.recovery_paths == ()
    for name, document in documents.items():
        assert (case_root / name).read_bytes() == document.to_bytes()


def test_denied_backup_rename_reports_partial_and_keeps_targets(case_root, monkeypatch):
    originals = _originals(case_root)
    documents = {name: _edited(case_root, name) for name in NAMES}
    monkeypatch.setenv(DENY, ".backup")
    with serve() as port, remote_backend(port) as backend:
        report = save_remote_case("/", backend, documents)
        stages = [path for path in report.recovery_paths if ".stage" in path]
        assert stages and all(_on_disk(case_root, path) for path in stages)
        recovered = recover_remote_case("/", backend, report.recovery_paths, documents)

    assert report.success is False
    assert report.partial is True
    assert report.errors
    assert _kinds(report.recovery_paths) == {"stage"}
    for name, data in originals.items():
        assert (case_root / name).read_bytes() == data
    assert recovered.success is True
    assert recovered.recovery_paths == ()
    assert not any(_on_disk(case_root, path) for path in stages)


def test_denied_stage_rename_rolls_back_and_keeps_the_stage(case_root, monkeypatch):
    originals = _originals(case_root)
    documents = {name: _edited(case_root, name) for name in NAMES}
    monkeypatch.setenv(DENY, ".stage")
    with serve() as port, remote_backend(port) as backend:
        report = save_remote_case("/", backend, documents)
        stages = [path for path in report.recovery_paths if ".stage" in path]
        assert stages and all(_on_disk(case_root, path) for path in stages)
        recovered = recover_remote_case("/", backend, report.recovery_paths, documents)

    assert report.success is False
    assert report.partial is True
    # The denied commit rename names the stage it refused to move.
    assert any(".stage" in error for error in report.errors)
    assert _kinds(report.recovery_paths) == {"stage"}
    for name, data in originals.items():
        # The half-committed swap must be reverted, never left all-green.
        assert (case_root / name).read_bytes() == data
    assert recovered.success is True
    assert not any(_on_disk(case_root, path) for path in stages)


def test_probe_failure_keeps_staged_artifacts_recoverable(case_root, monkeypatch):
    documents = {name: _edited(case_root, name) for name in NAMES}
    monkeypatch.setenv(DENY, ".backup")
    with serve() as port, remote_backend(port) as backend:
        report = save_remote_case("/", _DeadProbeBackend(backend), documents)

    assert report.success is False
    assert report.partial is True
    # exists() said False for every artifact; the stages are still real files.
    assert "stage" in _kinds(report.recovery_paths)
    stage_paths = [path for path in report.recovery_paths if ".stage" in path]
    assert stage_paths
    assert all(_on_disk(case_root, path) for path in stage_paths)


class _LinkLossBackend:
    """Delegate until the stage->target rename, then the link is gone.

    The dangerous window of a staged save is between ``target -> backup`` and
    ``stage -> target``: for that moment the original file exists only as the
    backup. Losing the connection exactly there must be reported as a partial
    save with the backup listed for recovery, never as a successful save.
    """

    def __init__(self, backend):
        self._backend = backend
        self.dead = False

    def __getattr__(self, name):
        return getattr(self._backend, name)

    def _check(self):
        if self.dead:
            raise TimeoutError("SSH transport is gone")

    def rename(self, src, dst):
        self._check()
        if ".stage" in src:
            # The original has already been moved to its backup; dropping the
            # link here is the one window where a wrong answer loses user data.
            self.dead = True
            raise TimeoutError("SSH transport is gone")
        return self._backend.rename(src, dst)

    def remove(self, path, recursive=False):
        self._check()
        return self._backend.remove(path, recursive=recursive)

    def stat(self, path):
        self._check()
        return self._backend.stat(path)

    def exists(self, path):
        self._check()
        return self._backend.exists(path)


def test_link_loss_between_backup_and_commit_is_reported_partial(case_root):
    name = "system/controlDict"
    original = (case_root / name).read_bytes()
    documents = {name: _edited(case_root, name)}

    with serve() as port, remote_backend(port) as backend:
        dying = _LinkLossBackend(backend)
        report = save_remote_case("/", dying, documents)
        assert dying.dead is True
        assert report.success is False
        assert report.saved == ()
        assert report.partial is True
        assert "backup" in _kinds(report.recovery_paths)
        for path in report.recovery_paths:
            assert _on_disk(case_root, path), path
        # The link is back for this call; recovery must restore the originals.
        recovered = recover_remote_case("/", backend, report.recovery_paths, documents)

    assert (case_root / name).read_bytes() == original
    assert recovered.success is True


def test_resume_completes_after_the_session_is_replaced(case_root):
    payload = os.urandom(2 * 1024 * 1024)
    full = case_root.parent / "full.bin"
    full.write_bytes(payload)
    prefix = case_root.parent / "prefix.bin"
    prefix.write_bytes(payload[: 512 * 1024])
    copy = case_root.parent / "copy.bin"
    seen = []

    with serve() as port, remote_backend(port) as backend:
        backend.upload(str(prefix), "/big.bin")
    # First session is gone; a fresh connect must finish the same remote file.
    with serve() as port, remote_backend(port) as backend:
        backend.resume_upload(str(full), "/big.bin", progress_cb=lambda d, t: seen.append((d, t)))
        backend.download("/big.bin", str(copy))

    assert seen[0] == (512 * 1024, len(payload))
    assert copy.read_bytes() == payload


def test_second_file_rename_failure_rolls_back_the_first(case_root, monkeypatch):
    originals = _originals(case_root)
    documents = {name: _edited(case_root, name) for name in NAMES}
    # The first file's swap completes; the second file's backup rename is
    # refused, so the already-committed first file must be rolled back too.
    monkeypatch.setenv(DENY, "fvSchemes")
    with serve() as port, remote_backend(port) as backend:
        counting = _CountingBackend(backend)
        report = save_remote_case("/", counting, documents)
        recovered = recover_remote_case("/", backend, report.recovery_paths, documents)

    assert report.success is False
    assert report.partial is True
    assert report.saved == ()
    # The first file was swapped (target->backup, stage->target) and rolled
    # back (backup->target); a no-op run would show none of that.
    assert len(counting.renames) >= 3
    assert counting.removes
    assert "stage" in _kinds(report.recovery_paths)
    for name, data in originals.items():
        assert (case_root / name).read_bytes() == data
    assert recovered.success is True
    for name, data in originals.items():
        assert (case_root / name).read_bytes() == data


def test_wrong_profile_is_rejected_before_a_good_connect(case_root):
    payload = b"profile-payload"
    local = case_root.parent / "profile.bin"
    local.write_bytes(payload)
    known_hosts = case_root.parent / "known_hosts"
    with serve() as port:
        wrapper = SSHClientWrapper()
        bad = SSHConnInfo(
            host="127.0.0.1",
            port=port,
            username="user",
            password="wrong-secret",
            known_hosts_path=str(known_hosts),
            host_key_policy="accept-new",
            allow_agent=False,
            look_for_keys=False,
            timeout=20,
        )
        with pytest.raises(paramiko.AuthenticationException):
            wrapper.connect(bad)
        assert wrapper.client is None
        assert wrapper.sftp is None

        good = SSHConnInfo(
            host="127.0.0.1",
            port=port,
            username="user",
            password=PASSWORD,
            known_hosts_path=str(known_hosts),
            host_key_policy="accept-new",
            allow_agent=False,
            look_for_keys=False,
            timeout=20,
        )
        wrapper.connect(good)
        try:
            SSHFilesBackend(wrapper).upload(str(local), "/after.bin")
        finally:
            wrapper.close()

    assert (case_root / "after.bin").read_bytes() == payload


def test_symlinked_case_file_is_refused(case_root, tmp_path):
    target = case_root / "system" / "controlDict"
    other = case_root / "system" / "fvSchemes"
    target.unlink()
    try:
        os.symlink(other, target)
    except (OSError, NotImplementedError):
        pytest.skip("creating symlinks needs an elevated token on this host")
    documents = {name: _edited(case_root, name) for name in NAMES}
    before = other.read_bytes()
    with serve() as port, remote_backend(port) as backend:
        report = save_remote_case("/", backend, documents)

    assert report.success is False
    assert report.partial is False
    assert any("symlink" in error for error in report.errors)
    assert target.is_symlink()
    assert other.read_bytes() == before
