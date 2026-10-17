"""Wave 80: i18n integrity test + behavioral tests for Files/Outputs UX."""
from support.test_wave80_files_outputs_shared import (
    load_language,
    pytest,
    set_language,
    t,
)


class TestI18nIntegrity:
    """Verify all visible i18n keys exist in both EN and TR (spec section 26)."""

    @pytest.mark.contract
    def test_wave80_keys_work_in_en(self):
        load_language("en")
        wave80_keys = [
            "jobs_outputs.search", "jobs_outputs.search_hint", "jobs_outputs.find_next",
            "jobs_outputs.jump_to_latest", "jobs_outputs.open_in_window",
            "jobs_outputs.show_in_files", "jobs_outputs.path", "jobs_outputs.status",
            "jobs_outputs.status_following", "jobs_outputs.status_paused",
            "jobs_outputs.status_waiting", "jobs_outputs.status_disconnected",
            "jobs_outputs.status_completed", "jobs_outputs.status_error",
            "jobs_outputs.standard_output", "jobs_outputs.standard_error",
            "jobs_outputs.combined_output", "jobs_outputs.no_selected_job",
            "jobs_outputs.no_selected_job_hint", "jobs_outputs.refresh_all",
            "jobs_outputs.pause_all", "jobs_outputs.resume_all",
            "jobs_outputs.auto_scroll_all",
        ]
        for key in wave80_keys:
            val = t(key)
            assert not val.startswith("["), f"Missing in EN: {key} -> {val}"

    @pytest.mark.contract
    def test_wave80_keys_work_in_tr(self):
        load_language("tr")
        wave80_keys = [
            "jobs_outputs.search", "jobs_outputs.search_hint", "jobs_outputs.find_next",
            "jobs_outputs.jump_to_latest", "jobs_outputs.open_in_window",
            "jobs_outputs.show_in_files", "jobs_outputs.path", "jobs_outputs.status",
            "jobs_outputs.status_following", "jobs_outputs.status_paused",
            "jobs_outputs.status_waiting", "jobs_outputs.status_disconnected",
            "jobs_outputs.status_completed", "jobs_outputs.status_error",
            "jobs_outputs.standard_output", "jobs_outputs.standard_error",
            "jobs_outputs.combined_output", "jobs_outputs.no_selected_job",
            "jobs_outputs.no_selected_job_hint", "jobs_outputs.refresh_all",
            "jobs_outputs.pause_all", "jobs_outputs.resume_all",
            "jobs_outputs.auto_scroll_all",
        ]
        for key in wave80_keys:
            val = t(key)
            assert not val.startswith("["), f"Missing in TR: {key} -> {val}"

    @pytest.mark.contract
    def test_no_placeholder_fallback_for_critical_keys(self):
        """Verify no [key] placeholder appears for critical visible keys."""
        load_language("en")
        critical_keys = [
            "jobs.title", "jobs.details", "jobs.no_job_selected", "jobs.go_to_jobs",
            "jobs_outputs.files_title", "jobs_outputs.outputs_title",
            "jobs_outputs.no_channels", "jobs_outputs.search",
            "jobs_outputs.find_next", "jobs_outputs.jump_to_latest",
            "jobs_outputs.open_in_window", "jobs_outputs.show_in_files",
            "jobs_outputs.path", "jobs_outputs.status",
            "jobs_outputs.standard_output", "jobs_outputs.standard_error",
            "dirs.back", "dirs.forward", "dirs.up", "dirs.new_folder",
            "dirs.new_file", "dirs.refresh",
        ]
        for key in critical_keys:
            val = t(key)
            assert not val.startswith("["), f"Missing i18n key: {key} -> {val}"

    @pytest.mark.contract
    def test_turkish_critical_keys_not_placeholder(self):
        load_language("tr")
        critical_keys = [
            "jobs.title", "jobs.details", "jobs.no_job_selected", "jobs.go_to_jobs",
            "jobs_outputs.files_title", "jobs_outputs.outputs_title",
            "jobs_outputs.no_channels", "jobs_outputs.search",
            "dirs.back", "dirs.forward", "dirs.up",
        ]
        for key in critical_keys:
            val = t(key)
            assert not val.startswith("["), f"Missing i18n key (TR): {key} -> {val}"

    @pytest.mark.contract
    def test_turkish_no_mojibake_in_critical_keys(self):
        """Verify critical TR keys have no mojibake."""
        load_language("tr")
        critical_keys = [
            "jobs_outputs.search", "jobs_outputs.find_next",
            "jobs_outputs.jump_to_latest", "jobs_outputs.open_in_window",
            "jobs_outputs.show_in_files", "jobs_outputs.path",
            "jobs_outputs.status", "jobs_outputs.standard_output",
            "jobs_outputs.standard_error", "jobs_outputs.no_channels",
        ]
        for key in critical_keys:
            val = t(key)
            assert not val.startswith("["), f"Missing key: {key}"
            assert "\u00c3" not in val, f"Mojibake in {key}: {val}"

class TestOutputsBehavior:
    @pytest.mark.gui
    @pytest.mark.wx
    def test_outputs_tab_exists(self):
        """Outputs tab is present in the notebook."""
        import wx
        from hpc_gui.wx_jobs import show_jobs
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        try:
            show_jobs(list_jobs=lambda: [])
            frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
            assert frames
            frame = frames[-1]
            nb = frame._wx_jobs_controls["notebook"]
            texts = [nb.GetPageText(i) for i in range(nb.GetPageCount())]
            assert "Outputs" in texts
        finally:
            for w in list(wx.GetTopLevelWindows()):
                try:
                    if hasattr(w, "_wx_jobs_state"):
                        w.Hide()
                        w.Destroy()
                except Exception:
                    pass
            for _ in range(3):
                wx.Yield()

    @pytest.mark.contract
    def test_search_label_says_search_not_filter(self):
        """Outputs search uses 'Search' wording, not 'Filter'."""
        load_language("en")
        assert "Search" in t("jobs_outputs.search")
        assert "Search" in t("jobs_outputs.search_hint")
        load_language("tr")
        assert "Ara" in t("jobs_outputs.search")

    @pytest.mark.contract
    def test_status_keys_localized(self):
        load_language("en")
        assert t("jobs_outputs.status_following") == "Following"
        assert t("jobs_outputs.status_paused") == "Paused"
        assert t("jobs_outputs.status_waiting") == "Waiting for file"
        assert t("jobs_outputs.status_disconnected") == "Disconnected"
        assert t("jobs_outputs.status_completed") == "Completed"
        assert t("jobs_outputs.status_error") == "Error"
        load_language("tr")
        assert t("jobs_outputs.status_following") != "[jobs_outputs.status_following]"

    @pytest.mark.contract
    def test_standard_output_localized(self):
        load_language("en")
        assert t("jobs_outputs.standard_output") == "Standard Output"
        assert t("jobs_outputs.standard_error") == "Standard Error"
        load_language("tr")
        so = t("jobs_outputs.standard_output")
        assert "Çıktı" in so or "Standart" in so
        se = t("jobs_outputs.standard_error")
        assert "Hata" in se or "Standart" in se

    @pytest.mark.contract
    def test_empty_state_message(self):
        load_language("en")
        msg = t("jobs_outputs.no_channels")
        assert "Follow" in msg or "follow" in msg
        load_language("tr")
        msg = t("jobs_outputs.no_channels")
        assert "Takip" in msg or "takip" in msg

    @pytest.mark.contract
    def test_no_selected_job_message(self):
        load_language("en")
        assert "No job selected" in t("jobs_outputs.no_selected_job")
        load_language("tr")
        assert t("jobs_outputs.no_selected_job") != "[jobs_outputs.no_selected_job]"

class TestFilesBehavior:
    @pytest.mark.contract
    def test_files_toolbar_controls_exist(self):
        """Files toolbar has expected controls."""
        load_language("en")
        assert t("dirs.back") == "Back"
        assert t("dirs.forward") == "Forward"
        assert t("dirs.up") == "Up"
        assert t("dirs.refresh") == "Refresh"
        assert t("dirs.new_folder") == "New Folder"
        assert t("dirs.new_file") == "New File"

    @pytest.mark.contract
    def test_filter_labels_localized(self):
        load_language("en")
        assert t("dirs.tab_all") == "All"
        assert t("dirs.tab_folders") == "Folders"
        assert t("dirs.tab_iso") == "ISO"
        assert t("dirs.tab_archives") == "Archives"
        assert t("dirs.tab_slurm") == "Slurm"
        assert t("dirs.tab_shell") == "SH"
        assert t("dirs.tab_other") == "Other"
        load_language("tr")
        assert t("dirs.tab_all") == "Tümü"
        assert t("dirs.tab_shell") == "SH"

    @pytest.mark.contract
    def test_follow_wording_localized(self):
        load_language("en")
        assert "Follow" in t("dirs.follow_track") or "Track" in t("dirs.follow_track")
        load_language("tr")
        assert "Takip" in t("dirs.follow_track") or "takip" in t("dirs.follow_track")

    @pytest.mark.contract
    def test_context_menu_labels_localized(self):
        load_language("en")
        assert t("dirs.download") == "Download"
        assert t("dirs.upload") == "Upload"
        assert t("dirs.delete") == "Delete"
        assert t("dirs.copy") == "Copy"
        assert t("dirs.paste") == "Paste"
        assert t("dirs.rename") == "Rename"
        load_language("tr")
        assert t("dirs.download") == "İndir"
        assert t("dirs.delete") == "Sil"

    @pytest.mark.contract
    def test_favorites_localized(self):
        load_language("en")
        assert "Favorites" in t("dirs.favorites")
        load_language("tr")
        val = t("dirs.favorites")
        assert "Favori" in val or "favori" in val

    @pytest.mark.contract
    def test_runtime_language_switch_updates_files(self):
        load_language("en")
        assert t("dirs.back") == "Back"
        set_language("tr")
        assert t("dirs.back") == "Geri"
        set_language("en")
        assert t("dirs.back") == "Back"

class TestRegression:
    @pytest.mark.gui
    @pytest.mark.wx
    def test_wave78_tabs_still_work(self):
        import wx
        from hpc_gui.wx_jobs import show_jobs
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        try:
            show_jobs(list_jobs=lambda: [{"id": "1", "state": "RUNNING", "name": "test"}])
            frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
            assert frames
            nb = frames[-1]._wx_jobs_controls["notebook"]
            assert nb.GetPageCount() == 5
            assert nb.GetPageText(0) == "Jobs"
            assert nb.GetPageText(1) == "Cluster"
            assert nb.GetPageText(2) == "Details"
        finally:
            for w in list(wx.GetTopLevelWindows()):
                try:
                    if hasattr(w, "_wx_jobs_state"):
                        w.Hide()
                        w.Destroy()
                except Exception:
                    pass
            for _ in range(3):
                wx.Yield()

    @pytest.mark.contract
    def test_wave79_parsers_still_work(self):
        from hpc_gui.services.parsers import _parse_scontrol_v1, _parse_sacct_pipe_v1, _parse_truba_lssrv_v1
        d = _parse_scontrol_v1("JobId=1 JobState=RUNNING", None)
        assert d.job_id == "1"
        r = _parse_sacct_pipe_v1("JobIDRaw|State|Elapsed|MaxRSS|AllocTRES|ExitCode\n100|RUNNING|00:01:00|512M||0:0\n", None)
        assert len(r.rows) == 1
        s = _parse_truba_lssrv_v1(
            "Slurm partitions state\n"
            "Partition CPUs Wait. Jobs Wait. Jobs Nodes Max. Job Time Min. Nodes Max. Nodes Core RAM (MB)\n"
            "Name (Free) (Total) (Resources) (Total) (Total) (D-HH:MM:SS) per Job per Job per Node per Core\n"
            "short 8 32 0 1 2 1-00:00:00 1 2 16 4096\n",
            None,
        )
        assert len(s) == 1
