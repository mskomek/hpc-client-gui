import pytest

from hpc_gui.services.slurm_dependencies import (
    DependencyType,
    SlurmDependency,
    get_dependency,
    parse_dependency,
    remove_dependency,
    set_dependency,
)


@pytest.mark.parametrize("kind", list(DependencyType))
def test_all_dependency_types_render(kind):
    dependency = SlurmDependency(kind, ("12345", "12345_2"))
    assert parse_dependency(dependency.render()) == dependency


def test_manual_multiple_ids_and_existing_directive():
    text = "#!/bin/bash\n#SBATCH --dependency=afterok:10\n#SBATCH --comment=keep\necho run\n"
    edited = set_dependency(text, "afterany:20,21_3")
    assert get_dependency(edited).render() == "afterany:20,21_3"
    assert edited.count("--dependency=") == 1
    assert "echo run" in edited
    assert "--dependency" not in remove_dependency(edited)


def test_connection_context_invalidates_on_profile_switch():
    dependency = parse_dependency("afterok:12345_2", connection_id="arf")
    assert dependency.valid_for_connection("arf")
    assert not dependency.valid_for_connection("other")
    assert dependency.valid_for_connection(None) is False


def test_invalid_dependency_fails_closed():
    for value in ("afterok:", "afterok:abc", "unknown:123", "afterok:1,1"):
        with pytest.raises(ValueError):
            parse_dependency(value)
