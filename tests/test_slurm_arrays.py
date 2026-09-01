import pytest

from hpc_gui.services.slurm_arrays import (
    MAX_CONCURRENT,
    SlurmArraySpec,
    apply_array_mode,
    get_array,
    parse_array,
    remove_array,
)
from hpc_gui.services.slurm_script_parser import parse_job_paths


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("0-71", SlurmArraySpec(0, 71)),
        ("0-71%8", SlurmArraySpec(0, 71, max_concurrent=8)),
        ("0-100:2", SlurmArraySpec(0, 100, step=2)),
        ("0-100:2%10", SlurmArraySpec(0, 100, step=2, max_concurrent=10)),
    ],
)
def test_parse_and_render(value, expected):
    assert parse_array(value) == expected
    assert expected.render() == value


def test_array_mode_updates_existing_directive_once_and_single_removes_it():
    text = "#!/bin/bash\n#SBATCH --array=1-2\n#SBATCH --comment=keep\necho $SLURM_ARRAY_TASK_ID\n"
    edited = apply_array_mode(text, True, "0-100:2%10")
    assert get_array(edited).render() == "0-100:2%10"
    assert edited.count("#SBATCH --array=") == 1
    assert "echo $SLURM_ARRAY_TASK_ID" in edited
    assert "--array" not in remove_array(edited)


def test_validation_rejects_malformed_and_excessive_values():
    for value in ("1", "3-1", "0-10:0", "0-10%0", "0-1000000"):
        with pytest.raises(ValueError):
            parse_array(value)
    with pytest.raises(ValueError):
        SlurmArraySpec(0, 10, max_concurrent=MAX_CONCURRENT + 1)


def test_output_paths_keep_array_placeholders():
    script = "#SBATCH --array=0-3\n#SBATCH --output=logs/%A_%a.out\n"
    paths = parse_job_paths(script, "/work/job.slurm", job_id="12345_2")
    assert paths.stdout == "/work/logs/12345_2.out"
