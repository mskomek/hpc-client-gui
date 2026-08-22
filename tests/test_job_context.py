"""Wave 10 tests: static Slurm/Fluent job-context parsing and cross checks."""

from __future__ import annotations

import inspect

from hpc_gui.lint.job_context import (
    CROSS_RULE_ID,
    FluentLaunch,
    allocated_cpus,
    cross_diagnostics,
    parse_fluent_launch,
    parse_slurm_context,
)
from hpc_gui.lint.models import Severity


SBATCH_MATCH = """#!/bin/bash
#SBATCH --partition=long
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=112
#SBATCH --time=04:00:00
#SBATCH --mem=224G
fluent 3ddp -g -t112 -i journal.jou
"""


def test_parse_basic_directives():
    context = parse_slurm_context(SBATCH_MATCH)
    assert context is not None
    assert context.partition == "long"
    assert context.nodes == 1
    assert context.ntasks == 1
    assert context.cpus_per_task == 112
    assert context.time_limit_seconds == 4 * 3600
    assert context.memory_bytes == 224 * 1024**3


def test_short_flags_and_space_forms():
    text = "#!/bin/bash\n#SBATCH -N 2\n#SBATCH -n 4\n#SBATCH -c 8\n"
    context = parse_slurm_context(text)
    assert (context.nodes, context.ntasks, context.cpus_per_task) == (2, 4, 8)


def test_last_valid_directive_wins():
    text = (
        "#!/bin/bash\n"
        "#SBATCH --cpus-per-task=16\n"
        "#SBATCH --cpus-per-task=112\n"
        "#SBATCH -c broken value\n"
        "#SBATCH --cpus-per-task=64\n"
    )
    context = parse_slurm_context(text)
    # The invalid line is ignored; the last valid occurrence wins.
    assert context.cpus_per_task == 64


def test_dynamic_values_are_ignored():
    text = "#!/bin/bash\n#SBATCH --cpus-per-task=$SLURM_CPUS\n#SBATCH --mem=$(calc)\n"
    context = parse_slurm_context(text)
    assert context is not None
    assert context.cpus_per_task is None
    assert context.memory_bytes is None


def test_no_sbatch_returns_none():
    assert parse_slurm_context("fluent 3ddp -t8\n") is None


def test_memory_and_time_variants():
    context = parse_slurm_context("#SBATCH --mem=4000M\n#SBATCH --time=2-04:30:00\n")
    assert context.memory_bytes == 4000 * 1024**2
    assert context.time_limit_seconds == ((2 * 24 + 4) * 60 + 30) * 60

    minutes = parse_slurm_context("#SBATCH --time=90\n")
    assert minutes.time_limit_seconds == 90 * 60


def test_fluent_launch_dash_t_attached():
    launch = parse_fluent_launch("fluent 3ddp -g -t56 -i run.jou\n")
    assert launch.processes == 56
    assert launch.headless is True


def test_fluent_launch_dash_t_separate():
    launch = parse_fluent_launch('"/opt/ansys/fluent" 3ddp -t 112 2>&1 | tee out.log\n')
    assert isinstance(launch, FluentLaunch)
    assert launch.processes == 112


def test_quoted_executable_path_is_supported():
    script = '"/usr/local/ansys_inc/v252/fluent" 3ddp -g -t112\n'
    launch = parse_fluent_launch(script)
    assert launch.processes == 112


def test_no_fluent_command_returns_none():
    assert parse_fluent_launch("#!/bin/bash\necho hello\n") is None


def test_commented_launch_lines_are_ignored():
    assert parse_fluent_launch("# fluent 3ddp -t8\n") is None


def test_cpu_match_produces_no_diagnostic():
    context = parse_slurm_context(SBATCH_MATCH)
    launch = parse_fluent_launch(SBATCH_MATCH)
    assert cross_diagnostics(context, launch) == []


def test_cpu_mismatch_warns_with_exact_message():
    script = SBATCH_MATCH.replace("-t112", "-t56")
    context = parse_slurm_context(script)
    launch = parse_fluent_launch(script)
    diags = cross_diagnostics(context, launch)
    assert len(diags) == 1
    diag = diags[0]
    assert diag.rule_id == CROSS_RULE_ID
    assert diag.severity is Severity.WARNING
    assert diag.message == (
        "Slurm allocates 112 CPUs to the task, while Fluent is launched with "
        "56 solver processes."
    )


def test_unknown_cpus_skip():
    script = "#!/bin/bash\n#SBATCH --partition=long\nfluent 3ddp -g -t56\n"
    diags = cross_diagnostics(parse_slurm_context(script), parse_fluent_launch(script))
    assert diags == []


def test_multinode_product_uses_default_ntasks():
    script = (
        "#!/bin/bash\n"
        "#SBATCH --nodes=2\n"
        "#SBATCH --cpus-per-task=56\n"
        "fluent 3ddp -g -t112\n"
    )
    context = parse_slurm_context(script)
    # Slurm defaults --ntasks to 1, so the total is well-defined.
    assert allocated_cpus(context) == 112
    assert cross_diagnostics(context, parse_fluent_launch(script)) == []


def test_fully_explicit_multinode_product_is_used():
    script = (
        "#!/bin/bash\n"
        "#SBATCH --nodes=2\n"
        "#SBATCH --ntasks=1\n"
        "#SBATCH --cpus-per-task=56\n"
        "fluent 3ddp -g -t112\n"
    )
    context = parse_slurm_context(script)
    assert allocated_cpus(context) == 112
    assert len(cross_diagnostics(context, parse_fluent_launch(script))) == 0


def test_ntasks_per_node_makes_allocation_ambiguous():
    script = (
        "#!/bin/bash\n"
        "#SBATCH --ntasks-per-node=2\n"
        "#SBATCH --cpus-per-task=56\n"
        "fluent 3ddp -g -t56\n"
    )
    context = parse_slurm_context(script)
    assert context.allocation_ambiguous is True
    assert allocated_cpus(context) is None
    assert cross_diagnostics(context, parse_fluent_launch(script)) == []


def test_no_fluent_command_means_no_cross_diagnostic():
    script = "#!/bin/bash\n#SBATCH --cpus-per-task=112\nsleep 1\n"
    assert cross_diagnostics(
        parse_slurm_context(script), parse_fluent_launch(script)
    ) == []


def test_parser_never_executes_content():
    import hpc_gui.lint.job_context as module

    source = inspect.getsource(module)
    for forbidden in ("subprocess", "os.system", "Popen", "__import__", "eval(", "exec("):
        assert forbidden not in source


def test_no_truba_constants_in_core_parser():
    import hpc_gui.lint.job_context as module

    source = inspect.getsource(module)
    for forbidden in ("/arf", "truba", "TRUBA", "lssrv"):
        assert forbidden not in source
