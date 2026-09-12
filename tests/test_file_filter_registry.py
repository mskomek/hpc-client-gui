"""Unit tests for the file filter registry with overlapping-view semantics."""

from __future__ import annotations

import pytest
from dataclasses import dataclass

from hpc_gui.services.file_filter_registry import (
    FileFilter,
    FileFilterRegistry,
    build_core_registry,
)


@dataclass
class FakeEntry:
    name: str
    is_dir: bool = False


# ---------------------------------------------------------------------------
# Core filter registration
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestCoreFilters:
    def test_all_core_filters_registered(self):
        reg = build_core_registry()
        ids = [f.id for f in reg.all_filters()]
        assert "folders" in ids
        assert "iso" in ids
        assert "archives" in ids
        assert "slurm" in ids
        assert "shell" in ids

    def test_core_filter_order_is_deterministic(self):
        reg = build_core_registry()
        ids = [f.id for f in reg.all_filters()]
        assert ids == sorted(ids, key=lambda fid: next(f.order for f in reg.all_filters() if f.id == fid))

    def test_visible_filter_ids_includes_all_and_other(self):
        reg = build_core_registry()
        ids = reg.visible_filter_ids()
        assert ids[0] == "all"
        assert ids[-1] == "other"

    def test_reserved_ids_cannot_be_registered(self):
        reg = FileFilterRegistry()
        try:
            reg.register(FileFilter(id="all", label_en="Bad"))
            assert False, "should raise"
        except ValueError:
            pass


# ---------------------------------------------------------------------------
# Individual core filter matching
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestFilterMatching:
    def test_all_matches_everything(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("anything.txt"), "all") is True
        assert reg.matches(FakeEntry("anything.txt", is_dir=True), "all") is True

    def test_folders_matches_directories(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("output", is_dir=True), "folders") is True
        assert reg.matches(FakeEntry("file.txt"), "folders") is False

    def test_iso_matches_dot_iso(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("image.iso"), "iso") is True
        assert reg.matches(FakeEntry("image.ISO"), "iso") is True
        assert reg.matches(FakeEntry("image.txt"), "iso") is False

    def test_archives_matches_common_formats(self):
        reg = build_core_registry()
        for name in ("data.zip", "data.rar", "data.7z", "data.tgz", "data.tar.gz", "data.tar"):
            assert reg.matches(FakeEntry(name), "archives") is True, f"{name} should match archives"
        assert reg.matches(FakeEntry("data.txt"), "archives") is False

    def test_slurm_matches_slurm_files(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("job.slurm"), "slurm") is True
        assert reg.matches(FakeEntry("job.sbatch"), "slurm") is True
        assert reg.matches(FakeEntry("job.sh"), "slurm") is False

    def test_shell_matches_sh_files(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("run.sh"), "shell") is True
        assert reg.matches(FakeEntry("run.bash"), "shell") is True
        assert reg.matches(FakeEntry("run.slurm"), "shell") is False

    def test_other_excludes_all_specialized_matches(self):
        reg = build_core_registry()
        # A .txt file matches no specialized filter -> should be in "other"
        assert reg.matches(FakeEntry("readme.txt"), "other") is True
        # A .sh file matches shell -> should NOT be in "other"
        assert reg.matches(FakeEntry("run.sh"), "other") is False
        # A directory matches folders -> should NOT be in "other"
        assert reg.matches(FakeEntry("output", is_dir=True), "other") is False

    def test_unknown_filter_id_returns_false(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("x.txt"), "nonexistent") is False


# ---------------------------------------------------------------------------
# Overlapping filter semantics
# ---------------------------------------------------------------------------

class TestOverlappingFilters:
    @pytest.mark.unit
    def test_file_can_match_multiple_filters(self):
        reg = build_core_registry()
        # Register a custom "logs" filter that matches *.log
        reg.register(FileFilter(id="logs", label_en="Logs", globs=("*.log",), order=100))
        entry = FakeEntry("solver.log")
        # Matches "logs" (custom) and "other" (no core match) ... wait,
        # "other" should NOT match because it matches "logs" specialized.
        assert reg.matches(entry, "logs") is True
        assert reg.matches(entry, "other") is False  # matched a specialized filter
        # Also matches "all"
        assert reg.matches(entry, "all") is True

    @pytest.mark.contract
    def test_provider_filter_coexists_with_core(self):
        reg = build_core_registry()
        reg.register(FileFilter(
            id="fluent",
            label_en="Fluent",
            globs=("*.cas.h5", "*.dat.h5", "*.trn"),
            order=200,
            source="provider",
        ))
        entry = FakeEntry("case.cas.h5")
        assert reg.matches(entry, "fluent") is True
        assert reg.matches(entry, "other") is False
        assert reg.matches(entry, "all") is True

    @pytest.mark.unit
    def test_custom_filter_does_not_steal_from_other(self):
        reg = build_core_registry()
        reg.register(FileFilter(id="logs", label_en="Logs", globs=("*.log",), order=100))
        # readme.txt: no core match, no custom match -> should be in "other"
        assert reg.matches(FakeEntry("readme.txt"), "other") is True
        # solver.log: matches custom "logs" -> should NOT be in "other"
        assert reg.matches(FakeEntry("solver.log"), "other") is False


# ---------------------------------------------------------------------------
# Provider/plugin filter registration
# ---------------------------------------------------------------------------

class TestProviderFilters:
    @pytest.mark.integration
    def test_register_provider_filter(self):
        reg = build_core_registry()
        reg.register(FileFilter(
            id="truba_logs",
            label_en="TRUBA Logs",
            label_tr="TRUBA Gunlukleri",
            globs=("*.truba.log",),
            order=150,
            source="provider",
        ))
        assert reg.get("truba_logs") is not None
        assert reg.get("truba_logs").source == "provider"

    @pytest.mark.integration
    def test_remove_filter(self):
        reg = build_core_registry()
        reg.register(FileFilter(id="temp", label_en="Temp", order=200))
        assert reg.get("temp") is not None
        assert reg.remove("temp") is True
        assert reg.get("temp") is None

    @pytest.mark.integration
    def test_register_replaces_existing(self):
        reg = build_core_registry()
        reg.register(FileFilter(id="custom", label_en="V1", order=100))
        reg.register(FileFilter(id="custom", label_en="V2", order=100))
        filters = [f for f in reg.all_filters() if f.id == "custom"]
        assert len(filters) == 1
        assert filters[0].label_en == "V2"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestEdgeCases:
    def test_empty_name_entry(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry(""), "all") is True
        assert reg.matches(FakeEntry(""), "other") is True

    def test_dict_entry(self):
        reg = build_core_registry()
        assert reg.matches({"name": "run.sh", "is_dir": False}, "shell") is True
        assert reg.matches({"name": "output", "is_dir": True}, "folders") is True

    def test_case_insensitive_glob(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("RUN.SH"), "shell") is True
        assert reg.matches(FakeEntry("IMAGE.ISO"), "iso") is True

    def test_tar_gz_suffix(self):
        reg = build_core_registry()
        assert reg.matches(FakeEntry("backup.tar.gz"), "archives") is True
        assert reg.matches(FakeEntry("backup.tgz"), "archives") is True
