"""Wave 79: Provider Adapter/Parser Contract + TRUBA Parser Integration tests."""

from types import SimpleNamespace
from hpc_gui.services.parser_registry import (
    ParseResult, parse, register_parser, known_parser_ids,
)
from hpc_gui.services.adapter_registry import (
    known_adapter_ids,
)
from hpc_gui.services.parsers import (
    ScontrolJobDetails, SacctAccountingResult,
)
from hpc_gui.services.cluster_server_status import ClusterServerStatus
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.services.provider_contract import (
    execute_adapter, extract_contract, parse_with_contract,
)
from hpc_gui.services.parser_error_ux import (
    format_error_for_user, format_error_with_raw_hint, is_backend_error, is_parser_error,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict


# ---------------------------------------------------------------------------
# ParserRegistry tests
# ---------------------------------------------------------------------------

class TestParserRegistry:
    def test_known_parsers_registered(self):
        ids = known_parser_ids()
        assert "slurm.scontrol.v1" in ids
        assert "slurm.sacct.pipe.v1" in ids
        assert "truba.lssrv.v1" in ids

    def test_unknown_parser_fails_closed(self):
        result = parse("unknown.parser.id", "data")
        assert not result.ok
        assert result.error.kind == "unsupported"
        assert "Unknown parser" in result.error.message

    def test_parser_exception_becomes_parse_error(self):
        def bad_parser(text, config):
            raise ValueError("boom")
        register_parser("test.bad", bad_parser)
        try:
            result = parse("test.bad", "data")
            assert not result.ok
            assert result.error.kind == "parser_failure"
            assert "could not understand" in result.error.message
        finally:
            # cleanup
            from hpc_gui.services.parser_registry import _REGISTRY
            _REGISTRY.pop("test.bad", None)

    def test_raw_never_destroyed_on_parse_error(self):
        result = parse("nonexistent.parser", "some raw text", raw_source_id="scontrol")
        assert not result.ok
        assert result.error.raw_source_id == "scontrol"

    def test_successful_parse(self):
        result = parse("slurm.scontrol.v1", "JobId=123 JobName=test")
        assert result.ok
        assert isinstance(result.data, ScontrolJobDetails)
        assert result.data.job_id == "123"


# ---------------------------------------------------------------------------
# slurm.scontrol.v1 parser tests
# ---------------------------------------------------------------------------

class TestScontrolV1:
    VALID_SCONTROL = (
        "JobId=12345 JobName=testjob UserId=user(1000) "
        "JobState=RUNNING Partition=short Elapsed=00:05:30 "
        "NumNodes=1 NumCPUs=4 Reason=None "
        "WorkDir=/home/user/test StdOut=/home/user/test.out "
        "StdErr=/home/user/test.err Command=/home/user/run.sh "
        "NodeList=node001 ExitCode=0:0"
    )

    def test_valid_scontrol(self):
        result = parse("slurm.scontrol.v1", self.VALID_SCONTROL)
        assert result.ok
        d = result.data
        assert d.job_id == "12345"
        assert d.name == "testjob"
        assert d.state == "RUNNING"
        assert d.partition == "short"
        assert d.elapsed == "00:05:30"
        assert d.nodes == "1"
        assert d.cpus == "4"
        assert d.reason == "None"
        assert d.workdir == "/home/user/test"
        assert d.stdout_path == "/home/user/test.out"
        assert d.stderr_path == "/home/user/test.err"
        assert d.script_path == "/home/user/run.sh"
        assert d.nodelist == "node001"
        assert d.exit_code == "0:0"

    def test_reordered_scontrol_fields(self):
        raw = "WorkDir=/work JobId=99 JobState=PENDING JobName= reordered"
        result = parse("slurm.scontrol.v1", raw)
        assert result.ok
        assert result.data.job_id == "99"
        assert result.data.workdir == "/work"

    def test_missing_optional_scontrol_fields(self):
        raw = "JobId=50 JobState=COMPLETED"
        result = parse("slurm.scontrol.v1", raw)
        assert result.ok
        assert result.data.job_id == "50"
        assert result.data.workdir == ""
        assert result.data.stdout_path == ""

    def test_multiline_scontrol(self):
        raw = (
            "JobId=100 JobName=multi\n"
            "JobState=RUNNING Partition=gpu\n"
            "WorkDir=/data"
        )
        result = parse("slurm.scontrol.v1", raw)
        assert result.ok
        assert result.data.job_id == "100"
        assert result.data.workdir == "/data"

    def test_malformed_scontrol_no_fields(self):
        result = parse("slurm.scontrol.v1", "no equals signs here")
        assert not result.ok
        assert result.error.kind == "parser_failure"

    def test_unknown_fields_preserved_as_metadata(self):
        raw = "JobId=1 UnknownField=custom_value JobState=RUNNING"
        result = parse("slurm.scontrol.v1", raw)
        assert result.ok
        assert result.data.metadata.get("UnknownField") == "custom_value"


# ---------------------------------------------------------------------------
# slurm.sacct.pipe.v1 parser tests
# ---------------------------------------------------------------------------

class TestSacctPipeV1:
    VALID_SACCT = (
        "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n"
        "12345|COMPLETED|00:10:12|1024M||0:0\n"
        "12346|PENDING|00:00:00|0K||0:0\n"
    )

    def test_valid_sacct_pipe(self):
        result = parse("slurm.sacct.pipe.v1", self.VALID_SACCT)
        assert result.ok
        assert isinstance(result.data, SacctAccountingResult)
        assert len(result.data.rows) == 2
        assert result.data.rows[0].job_id == "12345"
        assert result.data.rows[0].state == "COMPLETED"
        assert result.data.rows[0].exit_code == "0:0"

    def test_empty_sacct_fields(self):
        raw = "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n100|||0K||\n"
        result = parse("slurm.sacct.pipe.v1", raw)
        assert result.ok
        assert len(result.data.rows) == 1
        assert result.data.rows[0].job_id == "100"
        assert result.data.rows[0].state == ""

    def test_job_step_accounting_rows(self):
        raw = (
            "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n"
            "12345|COMPLETED|00:10:12|1024M||0:0\n"
            "12345.batch|COMPLETED|00:10:10|512M||0:0\n"
        )
        result = parse("slurm.sacct.pipe.v1", raw)
        assert result.ok
        assert len(result.data.rows) == 2
        assert result.data.rows[1].job_id == "12345.batch"

    def test_malformed_sacct_line(self):
        raw = (
            "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n"
            "12345|COMPLETED|00:10:12|1024M||0:0\n"
            "only_one_field\n"
            "12346|PENDING|00:00:00|0K||0:0\n"
        )
        result = parse("slurm.sacct.pipe.v1", raw)
        assert result.ok
        assert len(result.data.rows) == 2
        assert len(result.data.warnings) == 1

    def test_blank_lines_ignored(self):
        raw = "\n\nJobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n\n12345|COMPLETED|00:10:12|1024M||0:0\n\n"
        result = parse("slurm.sacct.pipe.v1", raw)
        assert result.ok
        assert len(result.data.rows) == 1

    def test_raw_output_preserved(self):
        result = parse("slurm.sacct.pipe.v1", self.VALID_SACCT)
        assert result.ok
        assert "12345" in result.data.raw_text


# ---------------------------------------------------------------------------
# truba.lssrv.v1 parser tests
# ---------------------------------------------------------------------------

class TestTrubaLssrvV1:
    VALID_LSSRV = (
        "Slurm partitions state\n"
        "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
        "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
        "short 8 32 0 1 2 1-00:00:00 1 2 16 4096\n"
        "long 16 64 0 2 4 2-00:00:00 1 4 32 8192\n"
    )

    def test_valid_lssrv(self):
        result = parse("truba.lssrv.v1", self.VALID_LSSRV)
        assert result.ok
        assert isinstance(result.data, list)
        assert len(result.data) == 2
        assert isinstance(result.data[0], ClusterServerStatus)
        assert result.data[0].name == "short"
        assert result.data[0].free_cpus == "8"
        assert result.data[0].total_cpus == "32"
        assert result.data[0].memory_mb_per_core == "4096"

    def test_lssrv_spacing_variation(self):
        raw = (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "  short    8    32    0    1    2    1-00:00:00    1    2    16    4096  \n"
        )
        result = parse("truba.lssrv.v1", raw)
        assert result.ok
        assert len(result.data) == 1
        assert result.data[0].name == "short"

    def test_lssrv_empty(self):
        result = parse("truba.lssrv.v1", "")
        assert result.ok
        assert result.data == []

    def test_lssrv_single_column(self):
        raw = "SERVER\nnode001\n"
        result = parse("truba.lssrv.v1", raw)
        assert not result.ok
        assert result.error.kind == "parser_failure"

    def test_malformed_lssrv(self):
        result = parse("truba.lssrv.v1", "SERVER STATE CPU MEMORY\nnode001 available 32 128G\n")
        assert not result.ok
        assert result.error.kind == "parser_failure"

    def test_unrecognized_lssrv_is_typed_failure(self):
        result = parse("truba.lssrv.v1", "this is not a valid lssrv response")
        assert not result.ok
        assert result.error.kind == "parser_failure"


# ---------------------------------------------------------------------------
# ProviderContract tests
# ---------------------------------------------------------------------------

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
    def test_builtin_registry_is_available_without_parser_module_import(self):
        assert {"slurm.scontrol.job", "slurm.sacct.job", "truba.lssrv"} <= known_adapter_ids()
        assert {"slurm.scontrol.v1", "slurm.sacct.pipe.v1", "truba.lssrv.v1"} <= known_parser_ids()

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


# ---------------------------------------------------------------------------
# ParserErrorUX tests
# ---------------------------------------------------------------------------

class TestParserErrorUX:
    def test_format_backend_error(self):
        from hpc_gui.services.parser_registry import ParseError
        err = ParseError(kind="backend_failure", message="SSH timeout")
        assert "Command failed" in format_error_for_user(err)
        assert "SSH timeout" in format_error_for_user(err)

    def test_format_parser_error(self):
        from hpc_gui.services.parser_registry import ParseError
        err = ParseError(kind="parser_failure", message="unexpected format")
        msg = format_error_for_user(err)
        assert "could not understand" in msg

    def test_format_unsupported(self):
        from hpc_gui.services.parser_registry import ParseError
        err = ParseError(kind="unsupported", message="no parser")
        msg = format_error_for_user(err)
        assert "does not support" in msg

    def test_format_with_raw_hint(self):
        from hpc_gui.services.parser_registry import ParseError
        err = ParseError(kind="parser_failure", message="bad format")
        msg = format_error_with_raw_hint(err)
        assert "raw" in msg.lower()

    def test_is_backend_error(self):
        r = ParseResult.fail("backend_failure", "timeout")
        assert is_backend_error(r)
        assert not is_parser_error(r)

    def test_is_parser_error(self):
        r = ParseResult.fail("parser_failure", "bad")
        assert is_parser_error(r)


# ---------------------------------------------------------------------------
# Schema v4 validation tests
# ---------------------------------------------------------------------------

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
