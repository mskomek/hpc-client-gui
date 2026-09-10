"""Wave 79 deep audit — edge cases, fallbacks, regressions."""

from pathlib import Path

import pytest
from hpc_gui.services.parser_registry import (
    parse, register_parser, known_parser_ids, ParseError,
)
from hpc_gui.services.parsers import (
    _parse_scontrol_v1, _parse_sacct_pipe_v1, _parse_truba_lssrv_v1,
)
from hpc_gui.services.cluster_server_status import ClusterServerStatus
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.services.provider_contract import extract_contract, parse_with_contract
from hpc_gui.services.parser_error_ux import format_error_for_user, format_error_with_raw_hint
from hpc_gui.plugins.validator import validate_cluster_profile_dict
from hpc_gui.plugins.models import build_cluster_profile


# === ParserRegistry audit ===

class TestParserRegistryAudit:
    def test_fail_closed_unknown(self):
        r = parse("nonexistent.parser", "data")
        assert not r.ok and r.error.kind == "unsupported"

    def test_exception_becomes_typed_error(self):
        def boom(t, c):
            raise RuntimeError("crash")
        register_parser("test.boom", boom)
        try:
            r = parse("test.boom", "x")
            assert not r.ok and r.error.kind == "parser_failure"
        finally:
            from hpc_gui.services.parser_registry import _REGISTRY
            _REGISTRY.pop("test.boom", None)

    def test_raw_preserved_on_error(self):
        r = parse("nonexistent", "raw text", raw_source_id="scontrol")
        assert not r.ok
        assert isinstance(r.error, ParseError)
        assert r.error.raw_source_id == "scontrol"

    def test_parse_result_ok_true(self):
        r = parse("slurm.scontrol.v1", "JobId=1")
        assert r.ok and r.data is not None

    def test_parse_result_ok_false(self):
        r = parse("nonexistent", "data")
        assert not r.ok and r.error is not None

    def test_parse_with_none_config(self):
        r = parse("slurm.scontrol.v1", "JobId=1", None)
        assert r.ok

    def test_parse_with_empty_config(self):
        r = parse("slurm.scontrol.v1", "JobId=1", {})
        assert r.ok

    def test_known_ids_nonempty(self):
        assert len(known_parser_ids()) >= 3


# === slurm.scontrol.v1 audit ===

class TestScontrolV1Audit:
    def test_valid_full(self):
        raw = (
            "JobId=123 JobName=test UserId=user(1000) "
            "JobState=RUNNING Partition=short Elapsed=00:05:30 "
            "NumNodes=1 NumCPUs=4 Reason=None "
            "WorkDir=/home/user/test StdOut=/home/user/test.out "
            "StdErr=/home/user/test.err Command=/home/user/run.sh "
            "NodeList=node001 ExitCode=0:0"
        )
        d = _parse_scontrol_v1(raw, None)
        assert d.job_id == "123"
        assert d.name == "test"
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

    def test_reordered_fields(self):
        raw = "WorkDir=/work JobId=99 JobState=PENDING JobName=reordered"
        d = _parse_scontrol_v1(raw, None)
        assert d.job_id == "99" and d.workdir == "/work"

    def test_missing_optional_fields(self):
        raw = "JobId=50 JobState=COMPLETED"
        d = _parse_scontrol_v1(raw, None)
        assert d.job_id == "50"
        assert d.workdir == ""
        assert d.stdout_path == ""
        assert d.stderr_path == ""

    def test_multiline(self):
        raw = "JobId=100 JobName=multi\nJobState=RUNNING Partition=gpu\nWorkDir=/data"
        d = _parse_scontrol_v1(raw, None)
        assert d.job_id == "100" and d.workdir == "/data"

    def test_malformed_no_fields(self):
        with pytest.raises(ValueError):
            _parse_scontrol_v1("no equals signs here", None)

    def test_empty_raw(self):
        with pytest.raises(ValueError):
            _parse_scontrol_v1("", None)

    def test_unknown_fields_metadata(self):
        raw = "JobId=1 UnknownField=custom_value JobState=RUNNING"
        d = _parse_scontrol_v1(raw, None)
        assert d.metadata.get("UnknownField") == "custom_value"

    def test_raw_preserved(self):
        raw = "JobId=1 JobState=RUNNING"
        d = _parse_scontrol_v1(raw, None)
        assert d.raw == raw


# === slurm.sacct.pipe.v1 audit ===

class TestSacctPipeV1Audit:
    def test_valid_pipe(self):
        raw = "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n12345|COMPLETED|00:10:12|1024M||0:0\n"
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 1
        assert r.rows[0].job_id == "12345"
        assert r.rows[0].state == "COMPLETED"

    def test_header_skipped(self):
        raw = "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n100|RUNNING|00:01:00|512M||0:0\n"
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 1 and r.rows[0].job_id == "100"

    def test_empty_fields_preserved(self):
        raw = "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n100|||0K||\n"
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 1
        assert r.rows[0].state == ""

    def test_job_step_rows(self):
        raw = (
            "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n"
            "12345|COMPLETED|00:10:12|1024M||0:0\n"
            "12345.batch|COMPLETED|00:10:10|512M||0:0\n"
        )
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 2
        assert r.rows[1].job_id == "12345.batch"

    def test_malformed_line_warning(self):
        raw = (
            "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n"
            "12345|COMPLETED|00:10:12|1024M||0:0\n"
            "only_one_field\n"
            "12346|PENDING|00:00:00|0K||0:0\n"
        )
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 2
        assert len(r.warnings) == 1

    def test_blank_lines_ignored(self):
        raw = "\n\nJobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n\n12345|COMPLETED|00:10:12|1024M||0:0\n\n"
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 1

    def test_raw_preserved(self):
        raw = "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n100|RUNNING|00:01:00|512M||0:0\n"
        r = _parse_sacct_pipe_v1(raw, None)
        assert "100" in r.raw_text

    def test_empty_input(self):
        r = _parse_sacct_pipe_v1("", None)
        assert len(r.rows) == 0

    def test_header_only_no_data(self):
        r = _parse_sacct_pipe_v1("JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n", None)
        assert len(r.rows) == 0

    def test_multiple_steps(self):
        raw = (
            "JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n"
            "100|COMPLETED|00:10:00|1G||0:0\n"
            "100.batch|COMPLETED|00:09:50|512M||0:0\n"
            "100.0|COMPLETED|00:09:45|256M||0:0\n"
        )
        r = _parse_sacct_pipe_v1(raw, None)
        assert len(r.rows) == 3


# === truba.lssrv.v1 audit ===

class TestTrubaLssrvV1Audit:
    VALID_LSSRV = (
        "Slurm partitions state\n"
        "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
        "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
        "\x1b[37mshort 8 32 0 1 2 1-00:00:00 1 2 16 4096\x1b[0m\n"
        "long 16 64 0 2 4 2-00:00:00 1 4 32 8192\n"
        "Last update: 10 Sep 26 10:00\n"
    )

    def test_valid_real_lssrv_table(self):
        raw = self.VALID_LSSRV
        r = _parse_truba_lssrv_v1(raw, None)
        assert len(r) == 2
        assert isinstance(r[0], ClusterServerStatus)
        assert r[0].name == "short"
        assert r[0].free_cpus == "8"
        assert r[0].total_cpus == "32"
        assert r[0].memory_mb_per_core == "4096"

    def test_documented_box_table_fixture(self):
        raw = (Path(__file__).parent / "fixtures" / "lssrv" / "truba_partitions_state.txt").read_text(encoding="utf-8")
        rows = _parse_truba_lssrv_v1(raw, None)
        assert len(rows) == 9
        assert rows[0].partition == "single"
        assert rows[0].free_cpus == "190"
        assert rows[0].total_cpus == "192"
        assert rows[0].max_nodes_per_job == "UNLIMITED"
        assert rows[0].memory_mb_per_core == "9500 MB"

    def test_real_lssrv_spacing_variation(self):
        raw = (
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "  short    8    32    0    1    2    1-00:00:00    1    2    16    4096  \n"
        )
        r = _parse_truba_lssrv_v1(raw, None)
        assert len(r) == 1
        assert r[0].total_cpus == "32"

    def test_legacy_server_shape_is_rejected(self):
        with pytest.raises(ValueError):
            _parse_truba_lssrv_v1("SERVER STATE CPU MEMORY\nnode001 available 32 128G\n", None)

    def test_empty(self):
        r = _parse_truba_lssrv_v1("", None)
        assert r == []

    def test_single_column_skipped(self):
        with pytest.raises(ValueError):
            _parse_truba_lssrv_v1("SERVER\nnode001\n", None)

    def test_malformed_skipped(self):
        with pytest.raises(ValueError):
            _parse_truba_lssrv_v1("onlyoneword\n", None)

# === Schema v4 validation audit ===

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
        p = {"schema_version": 4, "profile_id": "t", "name": "T", "scheduler": "slurm"}
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
    def test_wave78_tabs_still_exist(self):
        """Verify the notebook structure hasn't regressed."""
        from hpc_gui.core.i18n import load_language, t
        load_language("en")
        # Just verify the i18n keys exist
        assert t("jobs.title") == "Jobs"
        assert t("jobs.details") == "Details"
        assert t("jobs_outputs.files_title") == "Files"
        assert t("jobs_outputs.outputs_title") == "Outputs"

    def test_wave78_raw_command_result_still_works(self):
        r = RawCommandResult.from_response(source_id="test", stdout="data")
        assert r.stdout == "data"

    def test_wave78_no_job_selected_key(self):
        from hpc_gui.core.i18n import load_language, t
        load_language("en")
        assert t("jobs.no_job_selected") == "No job selected"

    def test_wave78_go_to_jobs_key(self):
        from hpc_gui.core.i18n import load_language, t
        load_language("en")
        assert t("jobs.go_to_jobs") == "Go to Jobs"
