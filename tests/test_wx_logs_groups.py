from __future__ import annotations

from hpc_gui.wx_logs import LogDisplayEntry, group_repeated_ssh_commands


def _record(second: int, message: str, *, level: str = "INFO") -> str:
    return f"2026-10-21 12:00:{second:02d} | {level} | hpc_gui.ssh.client | {message}\n"


def _query(second: int, command: str, *, output: str = "") -> str:
    result = _record(second, f"SSH$ {command}")
    if output:
        result += _record(second, output)
    return result + _record(second, "[exit=0 duration=0.21s]")


def _groups(text: str) -> list[LogDisplayEntry]:
    return [entry for entry in group_repeated_ssh_commands(text) if entry.is_group]


def test_groups_adjacent_squeue_queries_and_preserves_every_raw_line():
    text = (
        _query(1, 'squeue -h -u alice -o "%A"', output="1001\n1002")
        + _query(2, 'squeue -h -u alice -o "%i|%T"', output="1003")
    )

    entries = group_repeated_ssh_commands(text)

    assert len(entries) == 1
    assert entries[0].is_group
    assert entries[0].command_family == "squeue"
    assert entries[0].command_count == 2
    assert entries[0].first_timestamp == "2026-10-21 12:00:01"
    assert entries[0].last_timestamp == "2026-10-21 12:00:02"
    assert "1001\n1002" in "".join(entries[0].raw_lines)
    assert "1003" in "".join(entries[0].raw_lines)
    assert "squeue -h -u alice -o \"%i|%T\"" in "".join(entries[0].raw_lines)
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_groups_sacct_and_tail_commands_even_when_tail_paths_differ():
    sacct = _query(1, "sacct -n -P -j 1001 -o JobID,State") + _query(
        2, "sacct -n -P -j 1002 -o JobID,State"
    )
    tail = _query(3, "tail -n 200 -- /scratch/run one/slurm.out") + _query(
        4, "tail -n 200 -- /scratch/run two/slurm.out"
    )

    entries = group_repeated_ssh_commands(sacct + tail)

    assert [(entry.command_family, entry.command_count) for entry in entries] == [
        ("sacct", 2),
        ("tail", 2),
    ]
    assert "/scratch/run one/slurm.out" in "".join(entries[1].raw_lines)
    assert "/scratch/run two/slurm.out" in "".join(entries[1].raw_lines)


def test_different_commands_and_intervening_lines_end_groups():
    text = (
        _query(1, "squeue -h")
        + _query(2, "squeue -h")
        + _query(3, "sacct -n -P")
        + _query(4, "sacct -n -P")
        + _record(5, "SSH: reconnecting...")
        + _query(6, "squeue -h")
        + _query(7, "squeue -h")
    )

    entries = group_repeated_ssh_commands(text)

    assert [(entry.command_family, entry.command_count) for entry in _groups(text)] == [
        ("squeue", 2),
        ("sacct", 2),
        ("squeue", 2),
    ]
    rendered = "".join(line for entry in entries for line in entry.raw_lines)
    assert "SSH: reconnecting" in rendered
    assert rendered == text


def test_failure_timeout_stderr_and_errors_are_never_hidden_in_groups():
    samples = (
        _query(1, "squeue -h")
        + _record(2, "SSH$ squeue -h")
        + _record(2, "[exit=2 duration=0.21s]")
        + _record(3, "SSH$ sacct -n -P")
        + _record(3, "[timeout after 1.0s exit=124]")
        + _record(4, "SSH$ tail -n 20 -- out.log")
        + _record(4, "STDERR:\npermission denied")
        + _record(4, "[exit=0 duration=0.21s]")
        + _record(5, "SSH channel open failed", level="ERROR")
        + _record(6, "Traceback (most recent call last):", level="ERROR")
        + _query(7, "squeue -h")
    )

    entries = group_repeated_ssh_commands(samples)

    assert _groups(samples) == []
    rendered = "".join(line for entry in entries for line in entry.raw_lines)
    assert rendered == samples
    for marker in ("exit=2", "timeout after", "STDERR:", "permission denied", "channel open failed", "Traceback"):
        assert marker in rendered


def test_ambiguous_interleaving_and_unsupported_commands_remain_raw():
    text = (
        _record(1, "SSH$ squeue -h")
        + _record(1, "SSH$ sacct -n -P")
        + _record(1, "[exit=0 duration=0.21s]")
        + _record(1, "[exit=0 duration=0.21s]")
        + _query(2, "sbatch job.slurm")
        + _query(3, "scancel 1001")
        + _query(4, "bash -lc 'squeue -h'")
    )

    entries = group_repeated_ssh_commands(text)

    assert _groups(text) == []
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_single_successful_query_is_not_a_group():
    text = _query(1, "squeue -h")

    entries = group_repeated_ssh_commands(text)

    assert not any(entry.is_group for entry in entries)
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_unprefixed_warning_or_connection_error_interrupts_a_run():
    text = (
        _query(1, "squeue -h")
        + "WARNING: scheduler response is incomplete\n"
        + _query(2, "squeue -h")
        + "SSH authentication timeout\n"
        + _query(3, "squeue -h")
    )

    entries = group_repeated_ssh_commands(text)

    assert _groups(text) == []
    assert "".join(line for entry in entries for line in entry.raw_lines) == text


def test_shell_pipelines_are_not_treated_as_direct_automatic_queries():
    text = _query(1, "squeue -h | head -n 10") + _query(2, "squeue -h | head -n 10")

    assert _groups(text) == []
