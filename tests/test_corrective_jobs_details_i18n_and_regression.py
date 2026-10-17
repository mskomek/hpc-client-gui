"""Corrective tests for Jobs + Details tabs — Sections 3-48."""
from support.test_corrective_jobs_details_shared import (
    _build_panel,
    _close,
    load_language,
    pytest,
    t,
    wx,
)


class TestSec27_I18N:
    @pytest.mark.contract
    def test_parse_warning_keys_exist(self):
        load_language("en")
        assert "Job details could not be parsed" in t("jobs_outputs.parse_error_details")
        assert "Accounting data could not be parsed" in t("jobs_outputs.parse_error_accounting")
        assert "Cluster partition information could not be parsed" in t("jobs_outputs.parse_error_cluster")
        assert "raw scheduler response" in t("jobs_outputs.parse_error_details").lower() or "raw" in t("jobs_outputs.parse_error_details").lower()
        load_language("tr")
        assert t("jobs_outputs.parse_error_details") != "[jobs_outputs.parse_error_details]"
        assert t("jobs_outputs.parse_error_accounting") != "[jobs_outputs.parse_error_accounting]"
        assert t("jobs_outputs.parse_error_cluster") != "[jobs_outputs.parse_error_cluster]"

    @pytest.mark.contract
    def test_raw_viewer_source_key(self):
        load_language("en")
        assert t("raw_viewer.source") == "Source"
        load_language("tr")
        assert t("raw_viewer.source") == "Kaynak"

    @pytest.mark.contract
    def test_raw_not_available_key(self):
        load_language("en")
        assert "not available" in t("jobs_outputs.raw_not_available").lower()
        load_language("tr")
        assert t("jobs_outputs.raw_not_available") != "[jobs_outputs.raw_not_available]"

class TestRegression_FilesOutputs:
    @pytest.mark.gui
    @pytest.mark.wx
    def test_files_tab_untouched(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            assert nb.GetPageCount() == 5
            assert nb.GetPageText(0) == "Jobs"
            assert nb.GetPageText(1) == "Cluster"
            assert nb.GetPageText(2) == "Details"
            assert nb.GetPageText(3) == "Files"
            assert nb.GetPageText(4) == "Outputs"
            # Files browser exists
            assert hasattr(ctrls["files_browser"], "_wx_remote_controls")
        finally:
            _close(frame)

    @pytest.mark.contract
    @pytest.mark.wx
    def test_outputs_tab_untouched(self):
        load_language("en")
        app, frame, panel = _build_panel()
        try:
            ctrls = panel._wx_jobs_controls
            nb = ctrls["notebook"]
            nb.SetSelection(4)
            wx.Yield()
            # Outputs controls exist
            assert "outputs_refresh" in ctrls
            assert "outputs_follow" in ctrls
        finally:
            _close(frame)
