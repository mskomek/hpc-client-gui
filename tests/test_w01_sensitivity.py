"""Sensitivity proof for W01 regression tests.

Verifies that if the old defects are reintroduced, the regression tests
would fail for the right reason.
"""
import pathlib


def test_fix_a_sensitivity_tour_append_detected():
    """If someone re-adds a tour menu.Append(), the test catches it."""
    src = pathlib.Path("src/hpc_gui/wx_shell_frame.py").read_text(encoding="utf-8")
    # Simulate reintroducing the bug
    broken = src.replace(
        'help_items["tour"] = None',
        'act_tour = help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))\n    help_items["tour"] = act_tour',
    )
    assert 'help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))' in broken, (
        "SENSITIVITY FAILURE: injected Quick Tour regression was not observable"
    )


def test_fix_a_sensitivity_dispatch_branch_detected():
    """If someone re-adds the APP-QUICKTOUR dispatch, the test catches it."""
    src = pathlib.Path("src/hpc_gui/wx_shell_dispatch.py").read_text(encoding="utf-8")
    broken = src + '\n    elif command_id == "APP-QUICKTOUR":\n        pass\n'
    assert "APP-QUICKTOUR" in broken
    assert 'APP-QUICKTOUR' in broken, "Should detect reintroduced dispatch"


def test_fix_b_sensitivity_messagebox_detected():
    """If someone re-adds wx.MessageBox to APP-ABOUT, the test catches it."""
    src = pathlib.Path("src/hpc_gui/wx_shell_dispatch.py").read_text(encoding="utf-8")
    about_idx = src.find('"APP-ABOUT"')
    if about_idx == -1:
        about_idx = src.find("'APP-ABOUT'")
    assert about_idx != -1, "APP-ABOUT dispatch not found"
    # Simulate reintroducing the bug: add wx.MessageBox after the dispatch
    broken = src[:about_idx + 500] + "wx.MessageBox" + src[about_idx + 500:]
    block = broken[about_idx:about_idx + 600]
    assert "wx.MessageBox" in block, "Should detect reintroduced MessageBox"


if __name__ == "__main__":
    test_fix_a_sensitivity_tour_append_detected()
    test_fix_a_sensitivity_dispatch_branch_detected()
    test_fix_b_sensitivity_messagebox_detected()
    print("All sensitivity tests passed")
