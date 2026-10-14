from hpc_gui.wx_logs import collapse_repeated_log_lines


def test_repeat_collapse_groups_adjacent_messages_without_hiding_later_occurrences():
    text = (
        "2026-10-15 10:00:00 | INFO | app | connected\n"
        "2026-10-15 10:00:01 | INFO | app | connected\n"
        "2026-10-15 10:00:02 | INFO | app | refreshed\n"
        "2026-10-15 10:00:03 | INFO | app | connected\n"
    )

    result = collapse_repeated_log_lines(text, "{count} kez tekrarlandı")

    assert result.count("| connected") == 2
    assert "1 kez tekrarlandı" in result
    assert "| refreshed" in result
