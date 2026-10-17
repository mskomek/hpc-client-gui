"""GUI-FILE-003 final stress and invariant campaign.

Every stress group drives real wx events through the production view handlers
and records the measured invariants in ``METRICS``.  The last test in the file
prints the whole scoreboard and asserts the mandatory zeros, so a regression
shows up as a measured number rather than as a missing assertion.
"""

from __future__ import annotations

pytest_plugins = ('support.test_wx_file003_final_stress_shared',)
from support.test_wx_file003_final_stress_shared import (
    Path,
    pytest,
    subprocess,
    sys,
)

pytestmark = [pytest.mark.wx]

@pytest.mark.gui
@pytest.mark.subprocess
@pytest.mark.regression
def test_editor_wx_lifecycle_predecessor_preserves_context_menu_runtime():
    root = Path(__file__).resolve().parents[1]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_wx_editor_window_parity.py",
            "tests/test_wx_embedded_terminal.py",
            "tests/test_wx_file003_final_stress.py::test_stress_a_right_click_retarget",
            "-q",
        ],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=90,
    )
    assert result.returncode == 0, f"child failed {result.returncode}:\n{result.stdout}\n{result.stderr}"
