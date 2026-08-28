from hpc_gui.services.slurm_script_parser import parse_job_paths, parse_output_error


def test_parse_output_error_accepts_slurm_equals_and_space_forms() -> None:
    assert parse_output_error(
        "#SBATCH --output=run.out\n#SBATCH --error run.err\n"
    ) == ("run.out", "run.err")


def test_parse_output_error_accepts_compact_short_forms() -> None:
    assert parse_output_error("#SBATCH -orun.out\n#SBATCH -erun.err\n") == (
        "run.out",
        "run.err",
    )


def test_job_paths_use_chdir_and_slurm_default_without_executing_script() -> None:
    paths = parse_job_paths(
        "#!/bin/bash\n"
        "#SBATCH --chdir=results\n"
        "#SBATCH --output=%x-%A.out\n"
        "echo '#SBATCH --output=ignored.out'\n",
        "/home/alice/jobs/run.slurm",
        job_id="42",
        job_name="train",
        submission_dir="/home/alice/jobs",
    )
    assert paths.workdir == "/home/alice/jobs/results"
    assert paths.stdout == "/home/alice/jobs/results/train-42.out"
    assert paths.stderr == paths.stdout


def test_directives_after_first_executable_line_are_ignored() -> None:
    paths = parse_job_paths(
        "#!/bin/bash\n"
        "echo ready\n"
        "#SBATCH --output=late.out\n",
        "/home/alice/run.slurm",
        job_id="7",
    )
    assert paths.stdout == "/home/alice/slurm-7.out"
