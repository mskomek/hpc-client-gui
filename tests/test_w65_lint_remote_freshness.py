"""W65 LINT-013: remote surfaces newer than the remote mesh points are reported."""
from __future__ import annotations

import stat
from types import SimpleNamespace

from hpc_gui.plugin_engines.openfoam_lint.remote_case import lint_remote_path


CONTROL = b"application icoFoam;\n"


class _Remote:
    def __init__(self, points_time, surface_time, surfaces=("body.stl",)):
        self.points_time = points_time
        self.surface_time = surface_time
        self.surfaces = list(surfaces)

    def _mode(self, path):
        if path in ("/", "/case", "/case/system", "/case/constant"):
            return stat.S_IFDIR | 0o755
        if path == "/case/system/controlDict":
            return stat.S_IFREG | 0o644
        if path == "/case/constant/polyMesh/points":
            return stat.S_IFREG | 0o644
        for name in self.surfaces:
            if path == f"/case/constant/triSurface/{name}":
                return stat.S_IFREG | 0o644
        raise OSError(path)

    def lstat_entry(self, path):
        return SimpleNamespace(mode=self._mode(path), size=len(CONTROL))

    def stat(self, path):
        self._mode(path)
        if path == "/case/constant/polyMesh/points":
            if self.points_time is None:
                raise OSError(path)
            return 1024, self.points_time
        if path.startswith("/case/constant/triSurface/"):
            return 2048, self.surface_time
        return len(CONTROL), 0

    def listdir(self, path):
        if path == "/case":
            return ["system", "constant"]
        if path == "/case/system":
            return ["controlDict"]
        if path == "/case/constant":
            return ["polyMesh", "triSurface"]
        if path == "/case/constant/polyMesh":
            return ["points"]
        if path == "/case/constant/triSurface":
            return self.surfaces
        raise OSError(path)

    def download(self, remote, local):
        if remote != "/case/system/controlDict":
            raise OSError(remote)
        with open(local, "wb") as handle:
            handle.write(CONTROL)


def _reported(files):
    result = lint_remote_path("/case", files)
    return [d for d in result.diagnostics if d.rule_id == "OF-CROSS-006"]


def test_newer_remote_surface_is_reported():
    reported = _reported(_Remote(points_time=1_900_000_000, surface_time=2_000_000_000))

    assert [d.path for d in reported] == ["/case/constant/triSurface/body.stl"]


def test_older_remote_surface_is_clean():
    assert _reported(_Remote(points_time=2_000_000_000, surface_time=1_900_000_000)) == []


def test_missing_remote_points_is_not_judged():
    assert _reported(_Remote(points_time=None, surface_time=2_000_000_000)) == []


def test_non_surface_entries_are_ignored():
    remote = _Remote(1_900_000_000, 2_000_000_000, surfaces=("notes.txt", "mesh.stl"))

    reported = _reported(remote)

    assert [d.path for d in reported] == ["/case/constant/triSurface/mesh.stl"]
