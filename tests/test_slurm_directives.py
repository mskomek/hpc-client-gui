from hpc_gui.services.slurm_directives import (
    get_directive,
    parse_slurm_directives,
    remove_directive,
    set_directive,
)


def test_get_set_remove_common_directives():
    text = "#!/bin/bash\n# comment\n#SBATCH --array=1-4%2\n#SBATCH -p short\necho run\n"
    doc = parse_slurm_directives(text)
    assert doc.get("array") == "1-4%2"
    assert doc.get("partition") == "short"
    edited = doc.set("walltime", "02:00:00")
    edited = set_directive(edited, "dependency", "afterok:42")
    assert get_directive(edited, "walltime") == "02:00:00"
    assert remove_directive(edited, "array").count("--array") == 0


def test_unknown_and_body_are_preserved():
    text = "#!/bin/bash\n#SBATCH --comment=keep\n#SBATCH --partition=old\necho '#SBATCH --partition=bad'\n"
    edited = set_directive(text, "partition", "new")
    assert "#SBATCH --comment=keep" in edited
    assert "echo '#SBATCH --partition=bad'" in edited
    assert sum(line.startswith("#SBATCH --partition=") for line in edited.splitlines()) == 1


def test_last_duplicate_wins_and_set_collapses_target():
    text = "#SBATCH -p first\n#SBATCH --partition=last\n"
    doc = parse_slurm_directives(text)
    assert doc.get("partition") == "last"
    edited = doc.set("partition", "new")
    assert edited.count("--partition=") == 1
    assert get_directive(edited, "-p") == "new"


def test_resources_and_comments_shebang_are_supported():
    text = "#!/bin/bash\n\n# note\n#SBATCH -N 2\n#SBATCH --mem=8G\nrun\n"
    doc = parse_slurm_directives(text)
    assert doc.get("resources") == {"nodes": "2", "memory": "8G"}
    edited = doc.set("resources", {"cpus_per_task": 8, "gres": "gpu:1"})
    assert get_directive(edited, "cpus_per_task") == "8"
    assert "#SBATCH --gres=gpu:1" in edited
    assert len(remove_directive(edited, "resources").splitlines()) == 4


def test_malformed_scripts_fail_soft_and_do_not_edit_late_directives():
    text = "#!/bin/bash\n#SBATCH --partition\necho start\n#SBATCH --partition=late\n"
    assert get_directive(text, "partition") == ""
    edited = set_directive(text, "partition", "safe")
    assert "#SBATCH --partition=safe" in edited
    assert "#SBATCH --partition=late" in edited


def test_insert_preserves_shebang_without_trailing_newline():
    edited = set_directive("#!/bin/bash", "partition", "short")
    assert edited == "#!/bin/bash\n#SBATCH --partition=short\n"
