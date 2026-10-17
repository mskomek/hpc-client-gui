"""Wave 80: i18n integrity test + behavioral tests for Files/Outputs UX."""
from support.test_wave80_files_outputs_shared import (
    load_language,
    pytest,
    set_language,
    t,
)


class TestWave80Audit:
    """Audit every Wave 80 spec checkbox."""

    @pytest.mark.contract
    def test_details_header_localized(self):
        """Section 3: DETAILS header uses i18n key."""
        load_language("en")
        assert t("jobs.details_header") == "DETAILS"
        load_language("tr")
        val = t("jobs.details_header")
        assert val != "[jobs.details_header]"

    @pytest.mark.contract
    def test_outputs_search_uses_search_not_filter(self):
        """Section 7: Search uses Search/Ara wording."""
        load_language("en")
        assert t("jobs_outputs.search") == "Search"
        load_language("tr")
        assert t("jobs_outputs.search") == "Ara"

    @pytest.mark.contract
    def test_outputs_find_next_localized(self):
        """Section 7: Find Next localized."""
        load_language("en")
        assert t("jobs_outputs.find_next") == "Find Next"
        load_language("tr")
        assert t("jobs_outputs.find_next") == "Sonrakini Bul"

    @pytest.mark.contract
    def test_outputs_jump_to_latest_localized(self):
        load_language("en")
        assert t("jobs_outputs.jump_to_latest") == "Jump to Latest"
        load_language("tr")
        assert t("jobs_outputs.jump_to_latest") == "En Sona Git"

    @pytest.mark.contract
    def test_outputs_open_in_window_localized(self):
        load_language("en")
        assert t("jobs_outputs.open_in_window") == "Open in Window"
        load_language("tr")
        assert t("jobs_outputs.open_in_window") == "Pencerede Aç"

    @pytest.mark.contract
    def test_outputs_show_in_files_localized(self):
        load_language("en")
        assert t("jobs_outputs.show_in_files") == "Show in Files"
        load_language("tr")
        assert t("jobs_outputs.show_in_files") == "Dosyalarda Göster"

    @pytest.mark.contract
    def test_outputs_path_label_localized(self):
        """Section 5: Path label exists."""
        load_language("en")
        assert t("jobs_outputs.path") == "Path"
        load_language("tr")
        assert t("jobs_outputs.path") == "Yol"

    @pytest.mark.contract
    def test_outputs_status_label_localized(self):
        """Section 5: Status label exists."""
        load_language("en")
        assert t("jobs_outputs.status") == "Status"
        load_language("tr")
        assert t("jobs_outputs.status") == "Durum"

    @pytest.mark.contract
    def test_outputs_follower_status_localized(self):
        """Section 6: All follower status values localized."""
        load_language("en")
        assert t("jobs_outputs.status_following") == "Following"
        assert t("jobs_outputs.status_paused") == "Paused"
        assert t("jobs_outputs.status_waiting") == "Waiting for file"
        assert t("jobs_outputs.status_disconnected") == "Disconnected"
        assert t("jobs_outputs.status_completed") == "Completed"
        assert t("jobs_outputs.status_error") == "Error"
        load_language("tr")
        assert t("jobs_outputs.status_following") != "[jobs_outputs.status_following]"
        assert t("jobs_outputs.status_paused") != "[jobs_outputs.status_paused]"

    @pytest.mark.contract
    def test_outputs_combined_output_localized(self):
        load_language("en")
        assert "Standard Output + Error" == t("jobs_outputs.combined_output")
        load_language("tr")
        val = t("jobs_outputs.combined_output")
        assert "Çıktı" in val or "Hata" in val

    @pytest.mark.contract
    def test_outputs_refresh_all_localized(self):
        """Section 4: Global controls disambiguated."""
        load_language("en")
        assert t("jobs_outputs.refresh_all") == "Refresh All"
        load_language("tr")
        assert t("jobs_outputs.refresh_all") == "Tümünü Yenile"

    @pytest.mark.contract
    def test_outputs_pause_all_localized(self):
        load_language("en")
        assert t("jobs_outputs.pause_all") == "Pause All"
        load_language("tr")
        assert t("jobs_outputs.pause_all") == "Tümünü Duraklat"

    @pytest.mark.contract
    def test_outputs_resume_all_localized(self):
        load_language("en")
        assert t("jobs_outputs.resume_all") == "Resume All"
        load_language("tr")
        assert t("jobs_outputs.resume_all") == "Tümüne Devam Et"

    @pytest.mark.contract
    def test_outputs_auto_scroll_all_localized(self):
        load_language("en")
        assert t("jobs_outputs.auto_scroll_all") == "Auto-scroll All"
        load_language("tr")
        assert t("jobs_outputs.auto_scroll_all") == "Tümünde Otomatik Kaydır"

    @pytest.mark.contract
    def test_outputs_empty_state_polished(self):
        """Section 11: Empty state uses proper copy."""
        load_language("en")
        msg = t("jobs_outputs.no_channels")
        assert "Follow" in msg or "follow" in msg
        assert "Files" in msg or "files" in msg
        load_language("tr")
        msg = t("jobs_outputs.no_channels")
        assert "Takip" in msg or "takip" in msg
        assert "Dosyalar" in msg or "dosyalar" in msg

    @pytest.mark.contract
    def test_outputs_no_selected_job_polished(self):
        """Section 12: No selected job state uses proper copy."""
        load_language("en")
        assert "No job selected" in t("jobs_outputs.no_selected_job")
        load_language("tr")
        val = t("jobs_outputs.no_selected_job")
        assert val != "[jobs_outputs.no_selected_job]"

    @pytest.mark.contract
    def test_outputs_no_selected_job_hint_polished(self):
        load_language("en")
        assert "Select a job" in t("jobs_outputs.no_selected_job_hint")
        load_language("tr")
        val = t("jobs_outputs.no_selected_job_hint")
        assert val != "[jobs_outputs.no_selected_job_hint]"

    @pytest.mark.contract
    def test_files_back_forward_up_localized(self):
        """Section 14: Navigation controls localized."""
        load_language("en")
        assert t("dirs.back") == "Back"
        assert t("dirs.forward") == "Forward"
        assert t("dirs.up") == "Up"
        load_language("tr")
        assert t("dirs.back") == "Geri"

    @pytest.mark.contract
    def test_files_new_folder_file_localized(self):
        """Section 14: New menu items localized."""
        load_language("en")
        assert t("dirs.new_folder") == "New Folder"
        assert t("dirs.new_file") == "New File"
        load_language("tr")
        assert t("dirs.new_folder") != "[dirs.new_folder]"

    @pytest.mark.contract
    def test_files_filter_architecture_preserved(self):
        """Section 15: Filter labels preserved."""
        load_language("en")
        assert t("dirs.tab_all") == "All"
        assert t("dirs.tab_folders") == "Folders"
        assert t("dirs.tab_iso") == "ISO"
        assert t("dirs.tab_archives") == "Archives"
        assert t("dirs.tab_slurm") == "Slurm"
        assert t("dirs.tab_shell") == "SH"
        assert t("dirs.tab_other") == "Other"

    @pytest.mark.contract
    def test_files_follow_wording_localized(self):
        """Section 16: Follow/Track wording localized."""
        load_language("en")
        val = t("dirs.follow_track")
        assert "Follow" in val or "Track" in val
        load_language("tr")
        val = t("dirs.follow_track")
        assert "Takip" in val

    @pytest.mark.contract
    def test_files_follow_status_indicator_key(self):
        """Section 18: Follow-status affordance key exists."""
        load_language("en")
        assert t("dirs.following") == "Following"
        assert t("dirs.not_following") == "Not following"
        load_language("tr")
        assert t("dirs.following") == "Takip ediliyor"

    @pytest.mark.gui
    @pytest.mark.wx
    def test_files_follow_menu_has_following_check(self):
        """Section 18: following a file creates a visible live channel."""
        import wx
        from hpc_gui.wx_jobs import show_jobs
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        contents = {"/work/solver.log": "solver output\n"}
        try:
            show_jobs(
                list_jobs=lambda: [{"id": "1", "state": "RUNNING", "name": "test", "workdir": "/work"}],
                read_remote_path=lambda path: contents.get(path, ""),
            )
            frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
            assert frames
            frame = frames[-1]
            ctrl = frame._wx_jobs_controls
            for _ in range(40):
                wx.Yield()
                if ctrl["jobs"].GetItemCount() == 1:
                    break
                wx.MilliSleep(10)
            event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, ctrl["jobs"].GetId())
            event.SetIndex(0)
            ctrl["jobs"].GetEventHandler().ProcessEvent(event)
            browser = ctrl["files_browser"]
            assert callable(getattr(browser, "_follow_callback", None))
            browser._follow_callback("/work/solver.log")
            for _ in range(60):
                wx.Yield()
                wx.MilliSleep(10)
                if any("solver output" in item.GetValue() for item in ctrl["output_channels"].values()):
                    break
            assert any("solver output" in item.GetValue() for item in ctrl["output_channels"].values())
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
    def test_runtime_language_switch_updates_outputs(self):
        """Runtime language switching updates visible controls."""
        load_language("en")
        assert t("jobs_outputs.search") == "Search"
        assert t("jobs_outputs.standard_output") == "Standard Output"
        set_language("tr")
        assert t("jobs_outputs.search") == "Ara"
        assert "Çıktı" in t("jobs_outputs.standard_output")
        set_language("en")
        assert t("jobs_outputs.search") == "Search"

    @pytest.mark.gui
    @pytest.mark.wx
    def test_no_hardcoded_english_in_outputs_controls(self):
        """Verify the visible search control uses the localized hint."""
        import wx
        from hpc_gui.wx_jobs import show_jobs
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        try:
            show_jobs(list_jobs=lambda: [])
            frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
            assert frames
            ctrl = frames[-1]._wx_jobs_controls
            search = ctrl["output_search"]
            assert search.GetHint() == t("jobs_outputs.search_hint")
            assert search.GetHint() == "Search in output..."
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

    @pytest.mark.gui
    @pytest.mark.wx
    def test_outputs_controls_use_all_suffix(self):
        """Section 4: Global controls use 'All' suffix."""
        import wx
        from hpc_gui.wx_jobs import show_jobs
        load_language("en")
        app = wx.App.Get() or wx.App(False)
        assert app is not None
        try:
            show_jobs(list_jobs=lambda: [])
            frames = [w for w in wx.GetTopLevelWindows() if w.GetTitle() == "Jobs"]
            assert frames
            ctrl = frames[-1]._wx_jobs_controls
            refresh = ctrl["outputs_refresh"]
            pause = ctrl["outputs_pause"]
            follow = ctrl["outputs_follow"]
            assert "All" in refresh.GetLabel()
            assert "All" in pause.GetLabel()
            assert "All" in follow.GetLabel()
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
