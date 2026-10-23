"""Schema, provider contract, error UX, and regression audits."""


import pytest
from hpc_gui.services.parser_registry import (
    ParseError,
)
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.services.provider_contract import extract_contract, parse_with_contract
from hpc_gui.services.parser_error_ux import format_error_for_user, format_error_with_raw_hint
from hpc_gui.plugins.validator import validate_cluster_profile_dict
from hpc_gui.plugins.models import build_cluster_profile


# === Schema v4 validation audit ===

@pytest.mark.contract
class TestSchemaV4Audit:
    def test_v4_valid(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm"}
        assert validate_cluster_profile_dict(p) == []

    def test_v4_unknown_adapter_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "job_details": {"adapter": "evil.inject", "parser": "slurm.scontrol.v1"}}
        errors = validate_cluster_profile_dict(p)
        assert any("evil.inject" in e for e in errors)

    def test_v4_unknown_parser_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "job_details": {"adapter": "slurm.scontrol.job", "parser": "evil.parser"}}
        errors = validate_cluster_profile_dict(p)
        assert any("evil.parser" in e for e in errors)

    def test_v4_executable_source_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "job_details": {"adapter": "slurm.scontrol.job", "source": "import os"}}
        errors = validate_cluster_profile_dict(p)
        assert any("executable" in e for e in errors)

    def test_v4_executable_eval_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "job_details": {"eval": "code"}}
        errors = validate_cluster_profile_dict(p)
        assert any("executable" in e for e in errors)

    def test_v4_executable_exec_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "cluster_status": {"exec": "code"}}
        errors = validate_cluster_profile_dict(p)
        assert any("executable" in e for e in errors)

    def test_v4_executable_callback_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "accounting": {"callback": "func"}}
        errors = validate_cluster_profile_dict(p)
        assert any("executable" in e for e in errors)

    def test_v4_executable_shell_rejected(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "job_details": {"shell": "bash"}}
        errors = validate_cluster_profile_dict(p)
        assert any("executable" in e for e in errors)

    def test_v4_optional_sections_ok(self):
        p = {
            "schema_version": 4,
            "profile_id": "t",
            "name": "T",
            "scheduler": "slurm",
            "job_details": {
                "adapter": "slurm.scontrol.job",
                "parser": "slurm.scontrol.v1",
            },
            "accounting": {
                "adapter": "slurm.sacct.job",
                "parser": "slurm.sacct.pipe.v1",
            },
            "cluster_status": {
                "adapter": "truba.lssrv",
                "parser": "truba.lssrv.v1",
            },
        }
        assert validate_cluster_profile_dict(p) == []

    def test_v4_partial_sections_ok(self):
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm",
             "job_details": {"adapter": "slurm.scontrol.job"}}
        assert validate_cluster_profile_dict(p) == []

    def test_v1_still_valid(self):
        p = {"schema_version": 1, "profile_id": "t", "name": "T", "scheduler": "slurm"}
        assert validate_cluster_profile_dict(p) == []

    def test_v2_still_valid(self):
        p = {"schema_version": 2, "profile_id": "t", "name": "T", "scheduler": "slurm"}
        assert validate_cluster_profile_dict(p) == []

    def test_v3_still_valid(self):
        p = {"schema_version": 3, "profile_id": "t", "name": "T", "scheduler": "slurm"}
        assert validate_cluster_profile_dict(p) == []

    def test_v5_rejected(self):
        p = {"schema_version": 5, "profile_id": "t", "name": "T", "scheduler": "slurm"}
        errors = validate_cluster_profile_dict(p)
        assert any("schema_version" in e for e in errors)


# === Backward compatibility audit ===

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


# === ProviderContract audit ===

@pytest.mark.contract
class TestProviderContractAudit:
    def test_full_contract(self):
        t = {
            "job_details": {"adapter": "a", "parser": "p"},
            "accounting": {"adapter": "b", "parser": "q"},
            "cluster_status": {"adapter": "c", "parser": "r"},
        }
        c = extract_contract(t)
        assert c.has_job_details and c.has_accounting and c.has_cluster_status

    def test_none_contract(self):
        c = extract_contract(None)
        assert not c.has_job_details and not c.has_accounting and not c.has_cluster_status

    def test_empty_dict(self):
        c = extract_contract({})
        assert not c.has_job_details

    def test_malformed_section(self):
        c = extract_contract({"job_details": "not a dict"})
        assert not c.has_job_details

    def test_partial_adapter_no_parser(self):
        c = extract_contract({"job_details": {"adapter": "slurm.scontrol.job"}})
        assert c.has_job_details
        assert c.job_details_parser is None

    def test_partial_parser_no_adapter(self):
        c = extract_contract({"accounting": {"parser": "slurm.sacct.pipe.v1"}})
        assert c.has_accounting
        assert c.accounting_adapter is None

    def test_parse_with_none_parser(self):
        r = parse_with_contract(None, "data")
        assert not r.ok and r.error.kind == "unsupported"


# === ParserErrorUX audit ===

@pytest.mark.unit
class TestParserErrorUXAudit:
    def test_backend_failure_format(self):
        err = ParseError(kind="backend_failure", message="SSH timeout")
        msg = format_error_for_user(err)
        assert "Command failed" in msg and "SSH timeout" in msg

    def test_parser_failure_format(self):
        err = ParseError(kind="parser_failure", message="bad")
        msg = format_error_for_user(err)
        assert "could not understand" in msg

    def test_unsupported_format(self):
        err = ParseError(kind="unsupported", message="no parser")
        msg = format_error_for_user(err)
        assert "does not support" in msg

    def test_empty_data_format(self):
        err = ParseError(kind="empty_data", message="nothing")
        msg = format_error_for_user(err)
        assert "No data" in msg

    def test_raw_hint_format(self):
        err = ParseError(kind="parser_failure", message="bad")
        msg = format_error_with_raw_hint(err)
        assert "raw" in msg.lower()


# === RawCommandResult audit ===

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


# === Wave 78 regression check ===

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
