"""Wave 79: schema/raw-result/backward-compatibility contract tests (split)."""


import pytest

from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.plugins.validator import validate_cluster_profile_dict


# ---------------------------------------------------------------------------
# ParserRegistry tests
# ---------------------------------------------------------------------------

@pytest.mark.contract
class TestSchemaV4Validation:
    def test_v4_valid(self):
        profile = {
            "schema_version": 4,
            "profile_id": "truba",
            "name": "TRUBA",
            "scheduler": "slurm",
            "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
            "accounting": {"adapter": "slurm.sacct.job", "parser": "slurm.sacct.pipe.v1"},
            "cluster_status": {"adapter": "truba.lssrv", "parser": "truba.lssrv.v1"},
        }
        errors = validate_cluster_profile_dict(profile)
        assert errors == []

    def test_v4_unknown_adapter_rejected(self):
        profile = {
            "schema_version": 4,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
            "job_details": {"adapter": "evil.inject", "parser": "slurm.scontrol.v1"},
        }
        errors = validate_cluster_profile_dict(profile)
        assert any("evil.inject" in e for e in errors)

    def test_v4_unknown_parser_rejected(self):
        profile = {
            "schema_version": 4,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
            "job_details": {"adapter": "slurm.scontrol.job", "parser": "evil.parser"},
        }
        errors = validate_cluster_profile_dict(profile)
        assert any("evil.parser" in e for e in errors)

    def test_v4_executable_code_rejected(self):
        profile = {
            "schema_version": 4,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
            "job_details": {"adapter": "slurm.scontrol.job", "source": "import os; os.system('rm -rf /')"},
        }
        errors = validate_cluster_profile_dict(profile)
        assert any("executable" in e for e in errors)

    def test_v3_still_valid(self):
        profile = {
            "schema_version": 3,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
            "job_outputs": {"strategy": "explicit", "streams": []},
        }
        errors = validate_cluster_profile_dict(profile)
        assert errors == []

    def test_v1_still_valid(self):
        profile = {
            "schema_version": 1,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
        }
        errors = validate_cluster_profile_dict(profile)
        assert errors == []

    def test_v4_optional_sections(self):
        profile = {
            "schema_version": 4,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
        }
        errors = validate_cluster_profile_dict(profile)
        assert errors == []


# ---------------------------------------------------------------------------
# RawCommandResult tests
# ---------------------------------------------------------------------------

@pytest.mark.unit
class TestRawCommandResult:
    def test_from_response(self):
        r = RawCommandResult.from_response(
            source_id="scontrol",
            command="scontrol show job 1001",
            stdout="JobId=1001",
            stderr="",
            exit_code=0,
        )
        assert r.source_id == "scontrol"
        assert r.stdout == "JobId=1001"
        assert not r.has_error
        assert r.timestamp  # auto-generated

    def test_has_error(self):
        r = RawCommandResult.from_response(
            source_id="sacct",
            command="sacct -j 1001",
            stdout="",
            stderr="permission denied",
            exit_code=1,
        )
        assert r.has_error

    def test_display_command_fallback(self):
        r = RawCommandResult(source_id="scontrol", command="", stdout="")
        assert r.display_command == "[scontrol]"

    def test_unknown_exit_code_is_not_reported_as_error(self):
        r = RawCommandResult.from_response(source_id="scontrol", stdout="legacy callback")
        assert r.exit_code == -1
        assert not r.has_error


# ---------------------------------------------------------------------------
# Backward compatibility tests
# ---------------------------------------------------------------------------

@pytest.mark.contract
class TestBackwardCompatibility:
    def test_v1_profile_loads(self):
        from hpc_gui.plugins.models import build_cluster_profile
        raw = {"schema_version": 1, "profile_id": "test", "name": "Test", "scheduler": "slurm"}
        profile = build_cluster_profile(raw)
        assert profile.schema_version == 1
        assert profile.job_details is None
        assert profile.accounting is None
        assert profile.cluster_status is None

    def test_v3_profile_loads(self):
        from hpc_gui.plugins.models import build_cluster_profile
        raw = {
            "schema_version": 3,
            "profile_id": "test",
            "name": "Test",
            "scheduler": "slurm",
            "job_outputs": {"strategy": "explicit", "streams": []},
        }
        profile = build_cluster_profile(raw)
        assert profile.schema_version == 3
        assert profile.job_outputs is not None
        assert profile.job_details is None

    def test_v4_profile_loads(self):
        from hpc_gui.plugins.models import build_cluster_profile
        raw = {
            "schema_version": 4,
            "profile_id": "truba",
            "name": "TRUBA",
            "scheduler": "slurm",
            "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
            "accounting": {"adapter": "slurm.sacct.job", "parser": "slurm.sacct.pipe.v1"},
            "cluster_status": {"adapter": "truba.lssrv", "parser": "truba.lssrv.v1"},
        }
        profile = build_cluster_profile(raw)
        assert profile.schema_version == 4
        assert profile.job_details is not None
        assert profile.accounting is not None
        assert profile.cluster_status is not None

    def test_v4_to_system_settings_includes_contracts(self):
        from hpc_gui.plugins.models import build_cluster_profile
        raw = {
            "schema_version": 4,
            "profile_id": "truba",
            "name": "TRUBA",
            "scheduler": "slurm",
            "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
        }
        profile = build_cluster_profile(raw)
        settings = profile.to_system_settings()
        assert "provider_template" in settings
        assert settings["provider_template"]["job_details"]["adapter"] == "slurm.scontrol.job"
