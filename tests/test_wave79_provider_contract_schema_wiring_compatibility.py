"""Wave 79: Provider Adapter/Parser Contract + TRUBA Parser Integration tests."""
from support.test_wave79_provider_contract_shared import (
    RawCommandResult,
    SimpleNamespace,
    execute_adapter,
    extract_contract,
    known_adapter_ids,
    known_parser_ids,
    parse_with_contract,
    pytest,
    validate_cluster_profile_dict,
)


@pytest.mark.contract
class TestProviderContract:
    def test_extract_full_contract(self):
        template = {
            "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
            "accounting": {"adapter": "slurm.sacct.job", "parser": "slurm.sacct.pipe.v1"},
            "cluster_status": {"adapter": "truba.lssrv", "parser": "truba.lssrv.v1"},
        }
        contract = extract_contract(template)
        assert contract.job_details_adapter == "slurm.scontrol.job"
        assert contract.job_details_parser == "slurm.scontrol.v1"
        assert contract.accounting_adapter == "slurm.sacct.job"
        assert contract.accounting_parser == "slurm.sacct.pipe.v1"
        assert contract.cluster_status_adapter == "truba.lssrv"
        assert contract.cluster_status_parser == "truba.lssrv.v1"
        assert contract.has_job_details
        assert contract.has_accounting
        assert contract.has_cluster_status

    def test_extract_partial_contract(self):
        template = {"job_details": {"adapter": "slurm.scontrol.job"}}
        contract = extract_contract(template)
        assert contract.job_details_adapter == "slurm.scontrol.job"
        assert contract.job_details_parser is None
        assert not contract.has_accounting
        assert not contract.has_cluster_status

    def test_extract_empty_contract(self):
        contract = extract_contract(None)
        assert not contract.has_job_details
        assert not contract.has_accounting
        assert not contract.has_cluster_status

    def test_extract_malformed_section(self):
        template = {"job_details": "not a dict"}
        contract = extract_contract(template)
        assert not contract.has_job_details

    def test_parse_with_contract(self):
        result = parse_with_contract(
            "slurm.scontrol.v1",
            "JobId=100 JobState=RUNNING",
        )
        assert result.ok
        assert result.data.job_id == "100"

    def test_parse_with_none_parser(self):
        result = parse_with_contract(None, "data")
        assert not result.ok
        assert result.error.kind == "unsupported"

class TestProductionContractWiring:
    @pytest.mark.contract
    def test_builtin_registry_is_available_without_parser_module_import(self):
        assert {"slurm.scontrol.job", "slurm.sacct.job", "truba.lssrv"} <= known_adapter_ids()
        assert {"slurm.scontrol.v1", "slurm.sacct.pipe.v1", "truba.lssrv.v1"} <= known_parser_ids()

    @pytest.mark.contract
    def test_adapter_preserves_raw_command_result(self):
        class Backend:
            def scontrol_show_job(self, job_id):
                return RawCommandResult.from_response(
                    source_id="scontrol", command="trusted", stdout=f"JobId={job_id}", exit_code=0,
                )

        result = execute_adapter("slurm.scontrol.job", slurm_backend=Backend(), job_id="42")
        assert isinstance(result, RawCommandResult)
        assert result.stdout == "JobId=42"
        assert result.command == "trusted"

    @pytest.mark.integration
    def test_production_jobs_callback_uses_declared_adapter(self):
        class Backend:
            def scontrol_show_job(self, job_id):
                return f"JobId={job_id} JobState=RUNNING"

        session_state = {
            "session": {
                "slurm": Backend(),
                "profile": {
                    "username": "alice",
                    "provider_template": {
                        "job_details": {"adapter": "slurm.scontrol.job", "parser": "slurm.scontrol.v1"},
                    },
                },
            },
        }
        from hpc_gui.wx_shell import _jobs_callbacks

        callbacks = _jobs_callbacks(
            session_state,
            None,
            SimpleNamespace(register_cleanup=lambda _callback: None),
        )
        result = callbacks["show_job_details"]("42")
        assert isinstance(result, RawCommandResult)
        assert result.stdout == "JobId=42 JobState=RUNNING"
        assert result.exit_code == -1

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
