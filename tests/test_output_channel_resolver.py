"""Unit tests for the dynamic output channel resolver."""

from __future__ import annotations

from hpc_gui.services.output_channel_resolver import (
    OutputChannelDefinition,
    OutputResolver,
    ResolvedOutputChannel,
    TrackedOutput,
    definitions_from_provider,
)


# ---------------------------------------------------------------------------
# OutputChannelDefinition
# ---------------------------------------------------------------------------

class TestOutputChannelDefinition:
    def test_basic_fields(self):
        d = OutputChannelDefinition(
            id="stdout", role="stdout", label_en="Standard Output",
            resolver="slurm.stdout",
        )
        assert d.id == "stdout"
        assert d.role == "stdout"
        assert d.resolver == "slurm.stdout"

    def test_frozen(self):
        d = OutputChannelDefinition(id="x", role="stdout", label_en="X")
        try:
            d.id = "y"  # type: ignore[misc]
            assert False, "should be frozen"
        except AttributeError:
            pass


# ---------------------------------------------------------------------------
# OutputResolver - legacy (no provider definitions)
# ---------------------------------------------------------------------------

class TestOutputResolverLegacy:
    def test_legacy_creates_stdout_stderr(self):
        resolver = OutputResolver()
        channels = resolver.resolve_legacy(
            job_id="123",
            workdir="/work",
            scontrol_stdout="/work/slurm-123.out",
            scontrol_stderr="/work/slurm-123.err",
        )
        assert len(channels) == 2
        assert channels[0].id == "stdout"
        assert channels[0].path == "/work/slurm-123.out"
        assert channels[1].id == "stderr"
        assert channels[1].path == "/work/slurm-123.err"

    def test_legacy_deduplicates_same_file(self):
        resolver = OutputResolver()
        channels = resolver.resolve_legacy(
            job_id="123",
            workdir="/work",
            scontrol_stdout="/work/slurm-123.out",
            scontrol_stderr="/work/slurm-123.out",  # same file!
        )
        assert len(channels) == 1
        assert channels[0].roles == ("stdout", "stderr")
        assert "Standard Output" in channels[0].label or "Error" in channels[0].label

    def test_legacy_fallback_to_script_directives(self):
        resolver = OutputResolver()
        script = "#SBATCH --output=my-%j.out\n#SBATCH --error=my-%j.err\n"
        channels = resolver.resolve_legacy(
            job_id="42",
            workdir="/scratch/user",
            script_text=script,
        )
        assert len(channels) == 2
        assert "my-42.out" in channels[0].path
        assert "my-42.err" in channels[1].path
        assert channels[0].source == "script"
        assert channels[1].source == "script"

    def test_legacy_default_paths(self):
        resolver = OutputResolver()
        channels = resolver.resolve_legacy(job_id="99")
        # Default: stderr follows stdout in generic Slurm -> deduped
        assert len(channels) == 1
        assert "slurm-99.out" in channels[0].path
        assert channels[0].source == "default"
        assert "stdout" in channels[0].roles
        assert "stderr" in channels[0].roles

    def test_legacy_stderr_follows_stdout_when_no_explicit(self):
        resolver = OutputResolver()
        script = "#SBATCH --output=my-%j.out\n"  # no --error
        channels = resolver.resolve_legacy(
            job_id="42",
            workdir="/work",
            script_text=script,
        )
        # stderr follows stdout since no --error was specified -> deduped
        assert len(channels) == 1
        assert channels[0].roles == ("stdout", "stderr")
        assert "my-42.out" in channels[0].path


# ---------------------------------------------------------------------------
# OutputResolver - with provider definitions
# ---------------------------------------------------------------------------

class TestOutputResolverWithDefinitions:
    def test_two_channel_definitions(self):
        resolver = OutputResolver()
        defs = [
            OutputChannelDefinition(id="stdout", role="stdout", label_en="Stdout", resolver="slurm.stdout", order=0),
            OutputChannelDefinition(id="stderr", role="stderr", label_en="Stderr", resolver="slurm.stderr", order=1),
        ]
        channels = resolver.resolve(
            defs,
            job_id="100",
            workdir="/work",
            scontrol_stdout="/work/100.out",
            scontrol_stderr="/work/100.err",
        )
        assert len(channels) == 2
        by_id = {c.id: c for c in channels}
        assert "stdout" in by_id
        assert "stderr" in by_id
        assert by_id["stdout"].path == "/work/100.out"
        assert by_id["stderr"].path == "/work/100.err"

    def test_single_channel_definition(self):
        resolver = OutputResolver()
        defs = [
            OutputChannelDefinition(id="output", role="stdout", label_en="Output", resolver="slurm.stdout"),
        ]
        channels = resolver.resolve(
            defs,
            job_id="100",
            workdir="/work",
            scontrol_stdout="/work/100.out",
        )
        assert len(channels) == 1
        assert channels[0].label == "Output"

    def test_dedup_with_definitions(self):
        resolver = OutputResolver()
        defs = [
            OutputChannelDefinition(id="stdout", role="stdout", label_en="Stdout", resolver="slurm.stdout"),
            OutputChannelDefinition(id="stderr", role="stderr", label_en="Stderr", resolver="slurm.stderr"),
        ]
        channels = resolver.resolve(
            defs,
            job_id="100",
            workdir="/work",
            scontrol_stdout="/work/100.out",
            scontrol_stderr="/work/100.out",  # same!
        )
        assert len(channels) == 1
        assert "stdout" in channels[0].roles
        assert "stderr" in channels[0].roles

    def test_empty_definitions_returns_no_channels(self):
        resolver = OutputResolver()
        channels = resolver.resolve([], job_id="100")
        assert channels == []

    def test_invalid_resolver_ignored(self):
        resolver = OutputResolver()
        defs = [
            OutputChannelDefinition(id="bad", role="stdout", label_en="Bad", resolver="evil.command"),
        ]
        channels = resolver.resolve(defs, job_id="100")
        assert channels == []


# ---------------------------------------------------------------------------
# Array job placeholders
# ---------------------------------------------------------------------------

class TestArrayJobPlaceholders:
    def test_array_job_resolves_correctly(self):
        resolver = OutputResolver()
        script = "#SBATCH --output=output-%A_%a.log\n"
        channels = resolver.resolve_legacy(
            job_id="12345_17",
            workdir="/work",
            script_text=script,
        )
        assert len(channels) >= 1
        assert "12345_17" in channels[0].path or "12345" in channels[0].path

    def test_percent_a_uses_master_id(self):
        resolver = OutputResolver()
        script = "#SBATCH --output=job-%A.log\n"
        channels = resolver.resolve_legacy(
            job_id="12345_17",
            workdir="/work",
            script_text=script,
        )
        assert "job-12345.log" in channels[0].path

    def test_percent_x_uses_job_name(self):
        from hpc_gui.services.slurm_script_parser import _resolve_from_dir
        result = _resolve_from_dir("/work", "output-%x.log", "123", "myjob")
        assert "myjob" in result


# ---------------------------------------------------------------------------
# definitions_from_provider
# ---------------------------------------------------------------------------

class TestDefinitionsFromProvider:
    def test_absent_job_outputs_returns_empty(self):
        assert definitions_from_provider(None) == []

    def test_empty_streams_returns_empty(self):
        assert definitions_from_provider({"streams": []}) == []
        assert definitions_from_provider({"streams": "invalid"}) == []

    def test_valid_truba_definition(self):
        provider = {
            "streams": [
                {"id": "stdout", "role": "stdout", "labels": {"en": "Standard Output", "tr": "Standart Cikti"}, "resolver": "slurm.stdout"},
                {"id": "stderr", "role": "stderr", "labels": {"en": "Standard Error", "tr": "Standart Hata"}, "resolver": "slurm.stderr"},
            ]
        }
        defs = definitions_from_provider(provider)
        assert len(defs) == 2
        assert defs[0].id == "stdout"
        assert defs[0].resolver == "slurm.stdout"
        assert defs[1].id == "stderr"
        assert defs[1].label_tr == "Standart Hata"

    def test_invalid_resolver_ignored(self):
        provider = {
            "streams": [
                {"id": "bad", "role": "stdout", "resolver": "evil.cmd"},
            ]
        }
        defs = definitions_from_provider(provider)
        assert len(defs) == 0

    def test_missing_required_fields_ignored(self):
        provider = {
            "streams": [
                {"role": "stdout", "resolver": "slurm.stdout"},  # no id
            ]
        }
        defs = definitions_from_provider(provider)
        assert len(defs) == 0


# ---------------------------------------------------------------------------
# TrackedOutput
# ---------------------------------------------------------------------------

class TestTrackedOutput:
    def test_basic_fields(self):
        t = TrackedOutput(
            tracking_id="t1",
            channel_id="stdout",
            label="Standard Output",
            path="/work/out.log",
            origin="automatic",
        )
        assert t.tracking_id == "t1"
        assert t.origin == "automatic"

    def test_manual_tracking(self):
        t = TrackedOutput(
            tracking_id="t2",
            channel_id=None,
            label="solver.log",
            path="/work/solver.log",
            origin="manual",
        )
        assert t.channel_id is None
        assert t.origin == "manual"
