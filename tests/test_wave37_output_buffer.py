from hpc_gui.ui.widgets.jobs_outputs_widget import (
    _OUTPUT_MAX_LINES,
    _OUTPUT_TRUNCATION_MARKER,
    _ansi_to_html,
    _bounded_output_text,
)


def test_output_buffer_keeps_newest_lines_and_bound_marker() -> None:
    value = "\n".join(f"line-{index}" for index in range(_OUTPUT_MAX_LINES + 20))
    bounded = _bounded_output_text(value)
    lines = bounded.splitlines()
    assert lines[0] == _OUTPUT_TRUNCATION_MARKER
    assert len(lines) == _OUTPUT_MAX_LINES + 1
    assert lines[-1] == f"line-{_OUTPUT_MAX_LINES + 19}"


def test_output_buffer_preserves_active_ansi_state_after_truncation() -> None:
    value = "\x1b[31m" + "\n".join(f"line-{index}" for index in range(_OUTPUT_MAX_LINES + 2))
    bounded = _bounded_output_text(value)
    assert bounded.startswith("\x1b[31m" + _OUTPUT_TRUNCATION_MARKER)
    assert "color:#cd3131" in _ansi_to_html(bounded)
