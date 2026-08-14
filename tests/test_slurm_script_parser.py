from hpc_gui.services.slurm_script_parser import parse_output_error


def test_parse_output_error_accepts_slurm_equals_and_space_forms() -> None:
    assert parse_output_error(
        "#SBATCH --output=run.out\n#SBATCH --error run.err\n"
    ) == ("run.out", "run.err")


def test_parse_output_error_accepts_compact_short_forms() -> None:
    assert parse_output_error("#SBATCH -orun.out\n#SBATCH -erun.err\n") == (
        "run.out",
        "run.err",
    )
