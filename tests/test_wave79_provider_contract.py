"""Wave 79: Provider Adapter/Parser Contract + TRUBA Parser Integration tests."""
from support.test_wave79_provider_contract_shared import (
    ClusterServerStatus,
    ParseResult,
    SacctAccountingResult,
    ScontrolJobDetails,
    format_error_for_user,
    format_error_with_raw_hint,
    is_backend_error,
    is_parser_error,
    known_parser_ids,
    parse,
    pytest,
    register_parser,
)


@pytest.mark.contract
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

@pytest.mark.contract
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

@pytest.mark.contract
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

@pytest.mark.contract
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

@pytest.mark.unit
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
