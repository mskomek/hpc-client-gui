"""Wave 80: i18n integrity test + behavioral tests for Files/Outputs UX."""

from hpc_gui.core.i18n import load_language, t, set_language


# === i18n Integrity Test (spec section 26) ===

class TestI18nIntegrity:
    """Verify all visible i18n keys exist in both EN and TR (spec section 26)."""

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


# === Outputs behavioral tests (spec sections 4-13) ===

class TestOutputsBehavior:
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

    def test_search_label_says_search_not_filter(self):
        """Outputs search uses 'Search' wording, not 'Filter'."""
        load_language("en")
        assert "Search" in t("jobs_outputs.search")
        assert "Search" in t("jobs_outputs.search_hint")
        load_language("tr")
        assert "Ara" in t("jobs_outputs.search")

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

    def test_standard_output_localized(self):
        load_language("en")
        assert t("jobs_outputs.standard_output") == "Standard Output"
        assert t("jobs_outputs.standard_error") == "Standard Error"
        load_language("tr")
        so = t("jobs_outputs.standard_output")
        assert "Çıktı" in so or "Standart" in so
        se = t("jobs_outputs.standard_error")
        assert "Hata" in se or "Standart" in se

    def test_empty_state_message(self):
        load_language("en")
        msg = t("jobs_outputs.no_channels")
        assert "Follow" in msg or "follow" in msg
        load_language("tr")
        msg = t("jobs_outputs.no_channels")
        assert "Takip" in msg or "takip" in msg

    def test_no_selected_job_message(self):
        load_language("en")
        assert "No job selected" in t("jobs_outputs.no_selected_job")
        load_language("tr")
        assert t("jobs_outputs.no_selected_job") != "[jobs_outputs.no_selected_job]"


# === Files behavioral tests (spec sections 14-21) ===

class TestFilesBehavior:
    def test_files_toolbar_controls_exist(self):
        """Files toolbar has expected controls."""
        load_language("en")
        assert t("dirs.back") == "Back"
        assert t("dirs.forward") == "Forward"
        assert t("dirs.up") == "Up"
        assert t("dirs.refresh") == "Refresh"
        assert t("dirs.new_folder") == "New Folder"
        assert t("dirs.new_file") == "New File"

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

    def test_follow_wording_localized(self):
        load_language("en")
        assert "Follow" in t("dirs.follow_track") or "Track" in t("dirs.follow_track")
        load_language("tr")
        assert "Takip" in t("dirs.follow_track") or "takip" in t("dirs.follow_track")

    def test_files_toolbar_visible_labels_localized(self):
        """The real Files toolbar updates its visible labels on language change."""
        import wx
        from hpc_gui.wx_remote_files import WxRemoteDirectoryModel
        from hpc_gui.wx_remote_files_view import build_remote_files_panel

        load_language("en")
        app = wx.GetApp() or wx.App(False)
        frame = wx.Frame(None, size=(1000, 700))
        panel = build_remote_files_panel(
            frame,
            model=WxRemoteDirectoryModel(),
            loader=lambda _path: (),
            operation=lambda *_args: None,
        )
        frame.SetSizer(wx.BoxSizer(wx.VERTICAL))
        frame.GetSizer().Add(panel, 1, wx.EXPAND)
        frame.Show()
        wx.Yield()
        controls = panel._wx_remote_controls
        try:
            assert controls["btn_download"].IsShownOnScreen()
            assert controls["btn_download"].GetLabel() == "Download selected"
            assert controls["btn_upload"].GetLabel() == "Upload"
            set_language("tr")
            assert controls["btn_download"].GetLabel() == t("dirs.download_selected")
            assert controls["btn_download"].GetLabel() != "Download selected"
            assert controls["btn_upload"].GetLabel() == t("dirs.upload")
            assert controls["btn_upload"].GetLabel() != "Upload"
        finally:
            set_language("en")
            if callable(getattr(panel, "_wx_host_close", None)):
                panel._wx_host_close()
            frame.Destroy()
            app.ProcessPendingEvents()

    def test_favorites_localized(self):
        load_language("en")
        assert "Favorites" in t("dirs.favorites")
        load_language("tr")
        val = t("dirs.favorites")
        assert "Favori" in val or "favori" in val

    def test_runtime_language_switch_updates_files(self):
        load_language("en")
        assert t("dirs.back") == "Back"
        set_language("tr")
        assert t("dirs.back") == "Geri"
        set_language("en")
        assert t("dirs.back") == "Back"


# === Regression: Wave 78/79 still work ===

class TestRegression:
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


# === Wave 80 Comprehensive Audit Tests ===

class TestWave80Audit:
    """Audit every Wave 80 spec checkbox."""

    def test_details_header_localized(self):
        """Section 3: DETAILS header uses i18n key."""
        load_language("en")
        assert t("jobs.details_header") == "DETAILS"
        load_language("tr")
        val = t("jobs.details_header")
        assert val != "[jobs.details_header]"

    def test_outputs_search_uses_search_not_filter(self):
        """Section 7: Search uses Search/Ara wording."""
        load_language("en")
        assert t("jobs_outputs.search") == "Search"
        load_language("tr")
        assert t("jobs_outputs.search") == "Ara"

    def test_outputs_find_next_localized(self):
        """Section 7: Find Next localized."""
        load_language("en")
        assert t("jobs_outputs.find_next") == "Find Next"
        load_language("tr")
        assert t("jobs_outputs.find_next") == "Sonrakini Bul"

    def test_outputs_jump_to_latest_localized(self):
        load_language("en")
        assert t("jobs_outputs.jump_to_latest") == "Jump to Latest"
        load_language("tr")
        assert t("jobs_outputs.jump_to_latest") == "En Sona Git"

    def test_outputs_open_in_window_localized(self):
        load_language("en")
        assert t("jobs_outputs.open_in_window") == "Open in Window"
        load_language("tr")
        assert t("jobs_outputs.open_in_window") == "Pencerede Aç"

    def test_outputs_show_in_files_localized(self):
        load_language("en")
        assert t("jobs_outputs.show_in_files") == "Show in Files"
        load_language("tr")
        assert t("jobs_outputs.show_in_files") == "Dosyalarda Göster"

    def test_outputs_path_label_localized(self):
        """Section 5: Path label exists."""
        load_language("en")
        assert t("jobs_outputs.path") == "Path"
        load_language("tr")
        assert t("jobs_outputs.path") == "Yol"

    def test_outputs_status_label_localized(self):
        """Section 5: Status label exists."""
        load_language("en")
        assert t("jobs_outputs.status") == "Status"
        load_language("tr")
        assert t("jobs_outputs.status") == "Durum"

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

    def test_outputs_combined_output_localized(self):
        load_language("en")
        assert "Standard Output + Error" == t("jobs_outputs.combined_output")
        load_language("tr")
        val = t("jobs_outputs.combined_output")
        assert "Çıktı" in val or "Hata" in val

    def test_outputs_refresh_all_localized(self):
        """Section 4: Global controls disambiguated."""
        load_language("en")
        assert t("jobs_outputs.refresh_all") == "Refresh All"
        load_language("tr")
        assert t("jobs_outputs.refresh_all") == "Tümünü Yenile"

    def test_outputs_pause_all_localized(self):
        load_language("en")
        assert t("jobs_outputs.pause_all") == "Pause All"
        load_language("tr")
        assert t("jobs_outputs.pause_all") == "Tümünü Duraklat"

    def test_outputs_resume_all_localized(self):
        load_language("en")
        assert t("jobs_outputs.resume_all") == "Resume All"
        load_language("tr")
        assert t("jobs_outputs.resume_all") == "Tümüne Devam Et"

    def test_outputs_auto_scroll_all_localized(self):
        load_language("en")
        assert t("jobs_outputs.auto_scroll_all") == "Auto-scroll All"
        load_language("tr")
        assert t("jobs_outputs.auto_scroll_all") == "Tümünde Otomatik Kaydır"

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

    def test_outputs_no_selected_job_polished(self):
        """Section 12: No selected job state uses proper copy."""
        load_language("en")
        assert "No job selected" in t("jobs_outputs.no_selected_job")
        load_language("tr")
        val = t("jobs_outputs.no_selected_job")
        assert val != "[jobs_outputs.no_selected_job]"

    def test_outputs_no_selected_job_hint_polished(self):
        load_language("en")
        assert "Select a job" in t("jobs_outputs.no_selected_job_hint")
        load_language("tr")
        val = t("jobs_outputs.no_selected_job_hint")
        assert val != "[jobs_outputs.no_selected_job_hint]"

    def test_files_back_forward_up_localized(self):
        """Section 14: Navigation controls localized."""
        load_language("en")
        assert t("dirs.back") == "Back"
        assert t("dirs.forward") == "Forward"
        assert t("dirs.up") == "Up"
        load_language("tr")
        assert t("dirs.back") == "Geri"

    def test_files_new_folder_file_localized(self):
        """Section 14: New menu items localized."""
        load_language("en")
        assert t("dirs.new_folder") == "New Folder"
        assert t("dirs.new_file") == "New File"
        load_language("tr")
        assert t("dirs.new_folder") != "[dirs.new_folder]"

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

    def test_files_follow_wording_localized(self):
        """Section 16: Follow/Track wording localized."""
        load_language("en")
        val = t("dirs.follow_track")
        assert "Follow" in val or "Track" in val
        load_language("tr")
        val = t("dirs.follow_track")
        assert "Takip" in val

    def test_files_follow_status_indicator_key(self):
        """Section 18: Follow-status affordance key exists."""
        load_language("en")
        assert t("dirs.following") == "Following"
        assert t("dirs.not_following") == "Not following"
        load_language("tr")
        assert t("dirs.following") == "Takip ediliyor"

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

    def test_runtime_language_switch_updates_outputs(self):
        """Visible output-channel tabs follow the selected runtime language."""
        import time
        import wx
        from hpc_gui.wx_jobs import show_jobs

        load_language("en")
        app = wx.GetApp() or wx.App(False)
        try:
            show_jobs(list_jobs=lambda: [{
                "id": "1", "state": "RUNNING", "name": "job",
                "stdout_path": "/work/stdout.log", "stderr_path": "/work/stderr.log",
            }])
            frames = [window for window in wx.GetTopLevelWindows() if hasattr(window, "_wx_jobs_state")]
            assert frames
            frame = frames[-1]
            controls = frame._wx_jobs_controls
            deadline = time.monotonic() + 3
            while controls["jobs"].GetItemCount() == 0 and time.monotonic() < deadline:
                app.ProcessPendingEvents()
                wx.MilliSleep(10)
            assert controls["jobs"].GetItemCount() == 1

            jobs = controls["jobs"]
            jobs.Select(0)
            event = wx.ListEvent(wx.wxEVT_LIST_ITEM_SELECTED, jobs.GetId())
            event.SetIndex(0)
            jobs.GetEventHandler().ProcessEvent(event)
            channels = controls["output_channel_notebook"]
            deadline = time.monotonic() + 3
            while channels.GetPageCount() < 2 and time.monotonic() < deadline:
                app.ProcessPendingEvents()
                wx.MilliSleep(10)
            assert channels.GetPageCount() == 2
            controls["notebook"].SetSelection(4)
            frame.Show()
            wx.Yield()
            assert channels.IsShownOnScreen()
            assert channels.GetPageText(0) == "Standard Output"
            assert channels.GetPageText(1) == "Standard Error"

            set_language("tr")
            wx.Yield()
            assert channels.GetPageText(0) == t("jobs_outputs.standard_output")
            assert channels.GetPageText(1) == t("jobs_outputs.standard_error")
        finally:
            set_language("en")
            for window in list(wx.GetTopLevelWindows()):
                try:
                    if hasattr(window, "_wx_jobs_state"):
                        window.Hide()
                        window.Destroy()
                except Exception:
                    pass
            app.ProcessPendingEvents()

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
