"""W04 support matrix acceptance tests: support freeze."""

import pytest
import pathlib
import re
import hpc_gui.wx_shell as wx_shell
from hpc_gui.core.i18n import t
from hpc_gui.core.i18n import load_language
from w04_support_freeze_support import CLOSED_VOCABULARY, FROZEN_COUNTS, REQUIRED_COLUMNS, _MessageBoxCapture, _close_shell, _menu_labels, _parse_freeze_matrix, _shell_menu_labels, wx


@pytest.fixture(autouse=True)
def _english_bundle():
    load_language("en")
    yield
    load_language("en")


@pytest.fixture
def wx_app():
    app = wx.App.Get()
    if app is None:
        app = wx.App(False)
    yield app
    for window in wx.GetTopLevelWindows():
        try:
            if window:
                window.Destroy()
        except Exception:
            pass
    app.ProcessPendingEvents()
    wx.SafeYield()
    app.Destroy()


def test_matrix__has_all_required_columns():
    header, rows = _parse_freeze_matrix()
    for column in REQUIRED_COLUMNS:
        assert column in header, f"required column missing: {column}"
    assert len(rows) == sum(FROZEN_COUNTS.values()) == 56


def test_matrix__ids_unique_and_dispositions_closed():
    _, rows = _parse_freeze_matrix()
    ids = [row["ID"].strip("`") for row in rows]
    assert len(ids) == len(set(ids)) == 56
    for row in rows:
        assert row["Support disposition"] in CLOSED_VOCABULARY, row["ID"]


def test_matrix__freeze_totals_are_exact():
    _, rows = _parse_freeze_matrix()
    counts = {}
    for row in rows:
        counts[row["Support disposition"]] = counts.get(row["Support disposition"], 0) + 1
    for state, expected in FROZEN_COUNTS.items():
        assert counts.get(state, 0) == expected, f"{state}: {counts.get(state, 0)} != {expected}"


def test_matrix__supported_means_evidence_backed():
    """TRUTH-047/054: SUPPORTED rows carry evidence; EXPERIMENTAL rows carry
    an open gap (never bare)."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        if row["Support disposition"] == "SUPPORTED":
            assert row["Evidence IDs"].strip("` ") not in ("", "—", "none"), row["ID"]
        if row["Support disposition"] == "EXPERIMENTAL":
            assert row["Open gap"].strip().lower() not in ("", "none", "—"), row["ID"]


def test_matrix__rev_means_backend_dependent():
    """TRUTH-049/054: REV rows require non-dev-only evidence (external or
    package), never plain source trace."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        if row["Support disposition"] == "REQUIRES_EXTERNAL_VALIDATION":
            required = row["Required evidence class"].lower()
            assert "external" in required or "package" in required, row["ID"]


def test_matrix__rows_without_wave_owner_need_no_gap():
    """W01-D/TODO SUPPORT-EVIDENCE-001: every row either names a verification
    owner Wave or is a fully-proven native/local row with no open gap."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        owner = row["Verification owner Wave"]
        if re.fullmatch(r"—.*", owner):
            assert row["Support disposition"] == "SUPPORTED", row["ID"]
            assert row["Open gap"].strip().lower().startswith("none"), row["ID"]
        else:
            assert re.search(r"W\d\d", owner), f"{row['ID']}: no verification owner Wave"


def test_matrix__every_dispatch_literal_resolves_to_a_row():
    """TRUTH-056/058: every static dispatch literal maps to a freeze row."""
    shell_modules = sorted(pathlib.Path("src/hpc_gui").glob("wx_shell_*.py"))
    source = "\n".join(path.read_text(encoding="utf-8") for path in shell_modules)
    literals = set(re.findall(r'_dispatch\("([A-Z0-9-]+)"', source))
    assert literals, "dispatch extraction found nothing"
    _, rows = _parse_freeze_matrix()
    actions = " \n ".join(row["Action"] for row in rows)
    for literal in sorted(literals):
        if literal == "APP-COMMAND-PALETTE":
            help_center = next(r for r in rows if r["ID"].strip("`") == "HELP-CENTER")
            assert literal in help_center["Action"]
            continue
        assert literal in actions, f"dispatch {literal!r} has no freeze-matrix row"


def test_matrix__removed_baseline_actions_retain_disposition():
    """TRUTH-056/W01-C: removed baseline rows keep ID + final disposition."""
    _, rows = _parse_freeze_matrix()
    by_id = {row["ID"].strip("`"): row for row in rows}
    tour = by_id["`APP-QUICKTOUR`".strip("`")] if "`APP-QUICKTOUR`" in by_id else by_id.get("APP-QUICKTOUR")
    assert tour is not None
    assert tour["Support disposition"] == "NOT-IN-V2"
    assert "DEC-W01-QUICKTOUR" in tour["Decision ID"]
    assert re.search(r"W\d\d", tour["Verification owner Wave"])


def test_quicktour__absent_from_wx_help_menu(wx_app):
    """The removed ghost control is absent from the live wx menu."""
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        assert frame._wx_shell_help_items["tour"] is None
        labels = _menu_labels(frame._wx_shell_help_menu)
        assert not [label for label in labels if "tour" in label.casefold()]
    finally:
        _close_shell(frame)


def test_quicktour__no_dispatch_reaches_ui(wx_app, monkeypatch):
    """No APP-QUICKTOUR dispatch exists: firing it shows nothing and opens
    nothing (removed dispatch is not reachable)."""
    capture = _MessageBoxCapture(monkeypatch)
    before = set(wx.GetTopLevelWindows())
    wx_shell._dispatch("APP-QUICKTOUR", None, None, {})
    wx_app.ProcessPendingEvents()
    assert capture.calls == []
    assert set(wx.GetTopLevelWindows()) == before


def test_quicktour__absence_detector_is_sensitive(wx_app):
    """W01-E sensitivity: temporarily restoring the ghost item makes the
    absence detector fail for the right reason (proves the test is not
    vacuous); removal restores green."""

    def _tour_present(frame):
        return any("tour" in label.casefold() for label in _menu_labels(frame._wx_shell_help_menu))

    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        assert not _tour_present(frame)
        probe = frame._wx_shell_help_menu.Append(wx.ID_ANY, t("menu.quick_tour"))
        try:
            assert _tour_present(frame), "fault-injected tour item must trip the detector"
        finally:
            frame._wx_shell_help_menu.DestroyItem(probe)
        assert not _tour_present(frame)
    finally:
        _close_shell(frame)


def test_baseline_removals__no_wx_surface_for_legacy_keys(wx_app):
    """TRUTH-071: `menu.quick_tour` / `menu.command_palette` resolve in the
    bundle (Qt-legacy retention) but bind to no wx visible item — retained
    keys, not masking UI."""
    assert t("menu.quick_tour") != "[menu.quick_tour]"
    assert t("menu.command_palette") != "[menu.command_palette]"
    frame, _lifecycle, _session = wx_shell.create_shell_frame(wx_app)
    try:
        labels = _shell_menu_labels(frame)
        assert t("menu.quick_tour") not in labels
        assert t("menu.command_palette") not in labels
        assert frame._wx_shell_help_items["tour"] is None
    finally:
        _close_shell(frame)
