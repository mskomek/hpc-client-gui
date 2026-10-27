"""W65 r16 host integration and safe job-draft tests (guest runners only)."""

from __future__ import annotations

import hashlib
from pathlib import Path
import stat
from types import SimpleNamespace

import pytest

from hpc_gui.plugin_engines.openfoam_studio import job_draft
from hpc_gui.plugin_engines.openfoam_studio.job_draft import (
    JobSpec,
    build_draft_bundle,
    check_parallel_consistency,
    render_slurm_wrapper,
    validate_job_spec,
)
from hpc_gui.plugin_engines.openfoam_studio import job_draft_store


class _Parsed:
    def __init__(self, mapping):
        self._mapping = dict(mapping)

    def value(self, key, scope=()):
        return self._mapping.get((key, tuple(scope)))


class _Document:
    def __init__(self, text="", mapping=None):
        self.text = text
        self._parsed = _Parsed(mapping or {})

    @property
    def parsed(self):
        return self._parsed

    def to_bytes(self):
        return self.text.encode("utf-8")


def _catalog():
    return {
        "product": "OpenFOAM.com / ESI",
        "version": "v2312",
        "commands": [
            {"name": "blockMesh", "category": "Meshing", "verification_status": "runtime-inventory",
             "parameters": [], "execution": "draft-only"},
            {"name": "simpleFoam", "category": "Solver", "verification_status": "runtime-inventory",
             "parameters": [], "execution": "draft-only"},
        ],
    }


def _documents(nsub=None):
    docs = {
        "system/controlDict": _Document("application simpleFoam;", {("application", ()): "simpleFoam"}),
    }
    if nsub is not None:
        docs["system/decomposeParDict"] = _Document(
            f"numberOfSubdomains {nsub};", {("numberOfSubdomains", ()): str(nsub)}
        )
    return docs


def test_validate_job_spec_accepts_safe_inputs():
    spec = validate_job_spec(job_name="case-01", nodes=2, ntasks=4,
                             time="02:00:00", partition="cpu", module="apps/openfoam/v2312-2025")
    assert isinstance(spec, JobSpec) and spec.ntasks == 4


@pytest.mark.parametrize("kwargs", [
    {"job_name": ""},
    {"job_name": "bad name!"},
    {"nodes": 0},
    {"ntasks": 0},
    {"time": "99:99:99"},
    {"partition": "bad/part?"},
    {"module": "../evil"},
])
def test_validate_job_spec_rejects_unsafe_inputs(kwargs):
    with pytest.raises(ValueError):
        validate_job_spec(**kwargs)


def test_catalog_must_be_real_v2312():
    with pytest.raises(ValueError):
        job_draft.require_catalog_v2312({"product": "Other", "version": "v2312", "commands": []})
    with pytest.raises(ValueError):
        job_draft.require_catalog_v2312({"product": "OpenFOAM.com / ESI", "version": "v2312", "commands": []})


def test_decompose_match_and_mismatch():
    check_parallel_consistency(_documents(4), 4)
    with pytest.raises(ValueError, match="rank mismatch"):
        check_parallel_consistency(_documents(4), 2)


def test_parallel_without_decompose_is_blocked():
    with pytest.raises(ValueError, match="decomposeParDict"):
        check_parallel_consistency(_documents(None), 4)
    check_parallel_consistency(_documents(None), 1)


def test_build_bundle_uses_exact_bytes_digest():
    spec = validate_job_spec(ntasks=1)
    bundle = build_draft_bundle(_documents(None), _catalog(), ("blockMesh",), spec)
    assert bundle.allrun_sha256 == hashlib.sha256(bundle.allrun_text.encode("utf-8")).hexdigest()
    assert bundle.allrun_sha256 in bundle.slurm_text
    assert bundle.slurm_text.count(bundle.allrun_text) == 0


def test_wrapper_has_no_submit_invocation():
    spec = validate_job_spec()
    text = render_slurm_wrapper(spec, allrun_sha256="a" * 64)
    assert "sbatch " not in text and "sbatch\n" not in text
    for forbidden in ("Popen", "os.system", "shell=True"):
        assert forbidden not in text
    assert "DRAFT ONLY" in text


def test_wrapper_revalidates_forged_job_spec():
    forged = JobSpec(job_name="safe\n#SBATCH --partition=admin")
    with pytest.raises(ValueError):
        render_slurm_wrapper(forged, allrun_sha256="a" * 64)


def test_bundle_bounds_workflow_step_count():
    with pytest.raises(ValueError, match="at most"):
        build_draft_bundle(_documents(), _catalog(), ["blockMesh"] * 129, validate_job_spec())


def test_no_submit_imports_in_host_modules():
    repo = Path(__file__).resolve().parents[1]
    for relative in (
        "src/hpc_gui/plugin_engines/openfoam_studio/job_draft.py",
        "src/hpc_gui/plugin_engines/openfoam_studio/job_draft_store.py",
        "src/hpc_gui/plugin_engines/openfoam_studio/qt_job_draft.py",
        "src/hpc_gui/plugin_engines/openfoam_studio/wx_job_draft.py",
    ):
        source = (repo / relative).read_text(encoding="utf-8")
        assert "subprocess" not in source
        assert "Popen" not in source
        assert "os.system" not in source
        assert "shell=True" not in source
        assert "sbatch " not in source


def test_local_create_only_collision(tmp_path):
    root = tmp_path / "case"
    (root / "system").mkdir(parents=True)
    target = root / "job.slurm"
    target.write_text("existing", encoding="utf-8")
    with pytest.raises(FileExistsError):
        job_draft_store.create_local_job(str(root), "new-content", filename="job.slurm")
    assert target.read_text(encoding="utf-8") == "existing"


def test_local_symlink_target_refused(tmp_path):
    root = tmp_path / "case"
    root.mkdir()
    outside = tmp_path / "outside.slurm"
    outside.write_text("x", encoding="utf-8")
    link = root / "job.slurm"
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip("symlinks unavailable")
    with pytest.raises(FileExistsError):
        job_draft_store.create_local_job(str(root), "new", filename="job.slurm")


def test_local_create_rejects_symlinked_case_root(tmp_path):
    real = tmp_path / "real-case"
    real.mkdir()
    alias = tmp_path / "case-link"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        pytest.skip("directory symlinks unavailable")
    with pytest.raises(ValueError, match="link|junction"):
        job_draft_store.create_local_job(str(alias), "draft")


class _FakeFiles:
    def __init__(self):
        self.files = {}
        self.dirs = {"/"}
        self.links = set()

    def is_dir(self, path):
        return path in self.dirs

    def exists(self, path):
        return path in self.files

    def upload(self, local, remote):
        self.files[remote] = Path(local).read_bytes()

    def upload_exclusive(self, local, remote):
        if remote in self.files or remote in self.dirs or remote in self.links:
            raise FileExistsError(remote)
        self.files[remote] = Path(local).read_bytes()

    def download(self, remote, local):
        Path(local).write_bytes(self.files[remote])

    def rename(self, src, dst):
        self.files[dst] = self.files.pop(src)

    def rename_noreplace(self, src, dst):
        if dst in self.files or dst in self.dirs or dst in self.links:
            raise FileExistsError(dst)
        self.files[dst] = self.files.pop(src)

    def remove(self, path):
        del self.files[path]

    def lstat_entry(self, path):
        if path in self.links:
            return SimpleNamespace(mode=stat.S_IFLNK | 0o777, size=0)
        if path in self.dirs:
            return SimpleNamespace(mode=stat.S_IFDIR | 0o755, size=0)
        if path in self.files:
            return SimpleNamespace(mode=stat.S_IFREG | 0o644, size=len(self.files[path]))
        raise FileNotFoundError(path)


def test_remote_create_only_collision():
    files = _FakeFiles()
    files.dirs.add("/case")
    files.files["/case/job.slurm"] = b"existing"
    with pytest.raises(FileExistsError):
        job_draft_store.create_remote_job("/case", files, "new", filename="job.slurm")
    assert files.files["/case/job.slurm"] == b"existing"


def test_remote_create_blocks_symlinked_case_root():
    files = _FakeFiles()
    files.links.add("/case")
    with pytest.raises(ValueError, match="symbolic|link|directory"):
        job_draft_store.create_remote_job("/case", files, "new", filename="job.slurm")


def test_remote_create_requires_atomic_backend_capability():
    class _Unsafe(_FakeFiles):
        upload_exclusive = None

    files = _Unsafe()
    files.dirs.add("/case")
    with pytest.raises(NotImplementedError, match="exclusive upload"):
        job_draft_store.create_remote_job("/case", files, "new", filename="job.slurm")


def test_remote_no_replace_race_preserves_concurrent_target():
    files = _FakeFiles()
    files.dirs.add("/case")
    files.files["/case/job.slurm"] = b"operator-content"
    with pytest.raises(FileExistsError):
        files.rename_noreplace("/case/.stage", "/case/job.slurm")
    assert files.files["/case/job.slurm"] == b"operator-content"


def test_remote_writer_preserves_target_that_appears_during_stage(monkeypatch):
    files = _FakeFiles()
    files.dirs.add("/case")
    original_download = files.download

    def download_and_race(remote, local):
        original_download(remote, local)
        if remote.endswith(".stage"):
            files.files["/case/job.slurm"] = b"written-by-another-user"

    files.download = download_and_race
    with pytest.raises(FileExistsError):
        job_draft_store.create_remote_job("/case", files, "candidate-content")
    assert files.files["/case/job.slurm"] == b"written-by-another-user"
    assert any(path.endswith(".stage") for path in files.files)


def test_remote_writer_never_removes_preexisting_stage(monkeypatch):
    files = _FakeFiles()
    files.dirs.add("/case")
    fixed = "a" * 32
    monkeypatch.setattr(job_draft_store.uuid, "uuid4", lambda: SimpleNamespace(hex=fixed))
    stage = f"/case/.job.slurm.{fixed}.stage"
    files.files[stage] = b"operator-stage"
    with pytest.raises(FileExistsError):
        job_draft_store.create_remote_job("/case", files, "candidate-content")
    assert files.files[stage] == b"operator-stage"


def test_missing_linter_fails_closed(monkeypatch):
    import hpc_gui.plugin_engines.openfoam_studio.qt_review as review

    monkeypatch.setattr(review, "load_installed_plugins", None, raising=False)
    assert review._resolve_linter_tool() is None


def test_qt_action_state_flow_offscreen(monkeypatch):
    pytest.importorskip("PySide6.QtWidgets")
    import os

    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from hpc_gui.plugin_engines.openfoam_studio import qt_job_draft

    class _Status:
        def __init__(self):
            self.text = ""

        def setText(self, value):
            self.text = str(value)

    class _Page:
        def __init__(self, workspace):
            self.workspace = workspace
            self.status = _Status()
            self.opened = False

        def _show_error(self, message):
            self.status.setText(str(message))

    class _Actions:
        def __init__(self, page):
            self._page = page

        def _open_case(self):
            self._page.opened = True

    page = _Page(None)
    page.case_manager_actions = _Actions(page)
    assert qt_job_draft.ensure_case_for_draft(page) is False
    assert page.opened is True
    page2 = _Page(object())
    assert qt_job_draft.ensure_case_for_draft(page2) is True

    page3 = _Page(None)
    page3.case_manager_actions = _Actions(page3)

    def open_case_successfully():
        page3.opened = True
        page3.workspace = object()

    page3.case_manager_actions._open_case = open_case_successfully
    assert qt_job_draft.ensure_case_for_draft(page3) is True


def test_wx_action_state_continues_after_case_selection():
    from hpc_gui.plugin_engines.openfoam_studio import wx_job_draft

    class _Status:
        def SetLabel(self, _value):
            pass

    class _Page:
        workspace = None
        status = _Status()

        def _show_error(self, _message):
            pass

    page = _Page()

    class _Actions:
        def _open_case(self, _event):
            page.workspace = object()

    page.case_manager_actions = _Actions()
    assert wx_job_draft.ensure_case_for_draft(page) is True
