"""Wave 79 deep audit — edge cases, fallbacks, regressions."""
from support.test_wave79_audit_shared import (
    RawCommandResult,
    build_cluster_profile,
    pytest,
)


@pytest.mark.contract
class TestBackwardCompatAudit:
    def test_v1_loads(self):
        raw = {"schema_version": 1, "profile_id": "t", "name": "T", "scheduler": "slurm"}
        p = build_cluster_profile(raw)
        assert p.schema_version == 1
        assert p.job_details is None
        assert p.accounting is None
        assert p.cluster_status is None

    def test_v2_loads(self):
        raw = {"schema_version": 2, "profile_id": "t", "name": "T", "scheduler": "slurm",
               "metadata": {"maintainer": "test"}}
        p = build_cluster_profile(raw)
        assert p.schema_version == 2
        assert p.job_details is None

    def test_v3_loads(self):
        raw = {"schema_version": 3, "profile_id": "t", "name": "T", "scheduler": "slurm",
               "job_outputs": {"strategy": "explicit", "streams": []}}
        p = build_cluster_profile(raw)
        assert p.schema_version == 3
        assert p.job_outputs is not None
        assert p.job_details is None

    def test_v4_loads(self):
        raw = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
               "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
               "accounting": {"adapter": "slurm.sacct.job", "parser": "slurm.sacct.pipe.v1"},
               "cluster_status": {"adapter": "truba.lssrv", "parser": "truba.lssrv.v1"}}
        p = build_cluster_profile(raw)
        assert p.schema_version == 4
        assert p.job_details is not None
        assert p.accounting is not None
        assert p.cluster_status is not None

    def test_v4_to_system_settings(self):
        raw = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
               "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"}}
        p = build_cluster_profile(raw)
        s = p.to_system_settings()
        assert "provider_template" in s
        assert s["provider_template"]["job_details"]["adapter"] == "slurm.scontrol.job"

@pytest.mark.unit
class TestRawCommandResultAudit:
    def test_from_response(self):
        r = RawCommandResult.from_response(source_id="s", command="c", stdout="out", exit_code=0)
        assert r.source_id == "s" and r.stdout == "out" and not r.has_error

    def test_has_error(self):
        r = RawCommandResult.from_response(source_id="s", command="c", exit_code=1)
        assert r.has_error

    def test_display_command(self):
        r = RawCommandResult(source_id="s", command="cmd")
        assert r.display_command == "cmd"

    def test_display_command_fallback(self):
        r = RawCommandResult(source_id="s", command="")
        assert r.display_command == "[s]"

    def test_timestamp_auto_generated(self):
        r = RawCommandResult.from_response(source_id="s")
        assert r.timestamp  # non-empty

class TestWave78RegressionAudit:
    @pytest.mark.contract
    def test_wave78_tabs_still_exist(self):
        """Verify the notebook structure hasn't regressed."""
        from hpc_gui.core.i18n import load_language, t
        load_language("en")
        # Just verify the i18n keys exist
        assert t("jobs.title") == "Jobs"
        assert t("jobs.details") == "Details"
        assert t("jobs_outputs.files_title") == "Files"
        assert t("jobs_outputs.outputs_title") == "Outputs"

    @pytest.mark.unit
    def test_wave78_raw_command_result_still_works(self):
        r = RawCommandResult.from_response(source_id="test", stdout="data")
        assert r.stdout == "data"

    @pytest.mark.contract
    def test_wave78_no_job_selected_key(self):
        from hpc_gui.core.i18n import load_language, t
        load_language("en")
        assert t("jobs.no_job_selected") == "No job selected"

    @pytest.mark.contract
    def test_wave78_go_to_jobs_key(self):
        from hpc_gui.core.i18n import load_language, t
        load_language("en")
        assert t("jobs.go_to_jobs") == "Go to Jobs"
