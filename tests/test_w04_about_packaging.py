"""W04 support matrix acceptance tests: about packaging."""

import pytest
import pathlib
from hpc_gui.core.i18n import load_language
from w04_support_freeze_support import _MessageBoxCapture, _collect_about_labels, _collect_about_labels_with, _parse_freeze_matrix, wx


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


def test_about__visible_contract_fields(wx_app):
    """W01-E replacement-dialog proof: the About dialog carries the required
    visible contract (version + legal actions + close)."""
    seen, version = _collect_about_labels()
    assert any(version in text for text in seen["texts"]), seen["texts"]
    for required in ("Project Repository", "License", "Third-Party Notices", "Close"):
        assert required in seen["buttons"], seen["buttons"]


def test_about__contract_detector_is_sensitive(wx_app, monkeypatch):
    """W01-E sensitivity: the pre-FIX-W01-002 MessageBox implementation
    cannot satisfy the dialog contract (proves the contract test detects
    the old regression class)."""
    import hpc_gui.wx_about as about_view

    _MessageBoxCapture(monkeypatch)  # legacy impl would block on a real modal
    real = about_view.show_about

    def _legacy_messagebox_impl(_parent=None):
        wx.MessageBox("about", "about")
        return wx.ID_OK

    about_view.show_about = _legacy_messagebox_impl
    try:
        with pytest.raises(Exception):
            _collect_about_labels_with(about_view.show_about)
    finally:
        about_view.show_about = real


def test_packaging__no_artifact_claim_without_sha():
    """TRUTH-064: W04 binds no package artifact, so no SHA-256 is cited;
    every package-dependent row defers to W08/W10 instead of claiming."""
    _, rows = _parse_freeze_matrix()
    for row in rows:
        if "package" in row["Required evidence class"].lower():
            gap = row["Open gap"]
            assert "W08" in gap or "W10" in gap, f"{row['ID']}: package gap must name W08/W10"
    artifact_dir = pathlib.Path("artifacts/v2-final/W04")
    assert artifact_dir.is_dir()
    binaries = [
        path
        for path in artifact_dir.iterdir()
        if path.suffix.lower() in {".exe", ".msi", ".whl", ".zip", ".msix", ".dmg", ".pkg"}
    ]
    assert binaries == [], f"no package artifact may be bound by W04: {binaries}"
