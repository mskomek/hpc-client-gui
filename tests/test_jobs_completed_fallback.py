"""Completed Slurm Jobs Files/Outputs restore from cached accounting paths."""

from __future__ import annotations

import pytest

from hpc_gui import wx_shell_jobs


class _ExpiredJobSlurm:
    def scontrol_show_job(self, job_id):
        raise RuntimeError(f"slurm_load_jobs error: Invalid job id {job_id}")


class _RemoteFiles:
    def __init__(self):
        self.reads = []
        self.listings = []

    def read_text(self, path):
        self.reads.append(path)
        return f"saved:{path}"

    def iterdir_entries(self, path):
        self.listings.append(path)
        return (f"{path}/result.dat",)


def _callbacks(monkeypatch, *, profile_id="arf", cached_profile_id="arf"):
    monkeypatch.setattr(wx_shell_jobs, "_remote_files_callbacks", lambda *args: {})
    remote = _RemoteFiles()
    state = {
        "session": {
            "slurm": _ExpiredJobSlurm(),
            "files": remote,
            "profile": {
                "id": profile_id, "cluster_id": profile_id,
                "provider_id": "slurm", "username": "solver",
            },
        },
        "_jobs_history_cache": {
            (cached_profile_id, cached_profile_id, "slurm", "solver", 30): {
                "rows": [{
                    "job_id": "432", "state": "COMPLETED",
                    "workdir": "/work/case432",
                    "stdout_path": "/work/case432/stdout.log",
                    "stderr_path": "/work/case432/stderr.log",
                }],
                "read_at": 10, "error": "", "active_ids": frozenset(),
            },
        },
    }
    return wx_shell_jobs._jobs_callbacks(state, None, None), remote


def test_completed_outputs_fall_back_to_matching_profile_accounting_cache(monkeypatch):
    callbacks, remote = _callbacks(monkeypatch)
    outputs = callbacks["read_output"]("432")
    assert outputs == {
        "stdout": "saved:/work/case432/stdout.log",
        "stderr": "saved:/work/case432/stderr.log",
    }
    assert remote.reads == [
        "/work/case432/stdout.log", "/work/case432/stderr.log",
    ]


def test_completed_files_fall_back_to_matching_profile_accounting_cache(monkeypatch):
    callbacks, remote = _callbacks(monkeypatch)
    files = callbacks["list_job_files"]("432")
    assert files == ("/work/case432/result.dat",)
    assert remote.listings == ["/work/case432"]


def test_other_profile_accounting_paths_cannot_leak_into_current_profile(monkeypatch):
    callbacks, remote = _callbacks(
        monkeypatch, profile_id="arf2", cached_profile_id="arf",
    )
    with pytest.raises(RuntimeError, match="Invalid job id"):
        callbacks["read_output"]("432")
    assert callbacks["list_job_files"]("432") == ()
    assert remote.reads == []
    assert remote.listings == []


def test_unknown_completed_job_never_lists_filesystem_root(monkeypatch):
    callbacks, remote = _callbacks(monkeypatch)
    assert callbacks["list_job_files"]("no-such-job") == ()
    assert remote.listings == []
