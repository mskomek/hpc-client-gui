from __future__ import annotations

from support.ftp_widget_test_support import (
    FtpWidgetTestCase,
    LoginWidget,
    SimpleNamespace,
    _Files,
    patch,
    pytest,
)


class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    def test_context_menu_can_set_current_scratch_as_profile_default(self) -> None:
        cfg = SimpleNamespace(
            username="alice",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
        )
        self.widget.set_session(
            {
                "connected": True,
                "files": _Files(),
                "cfg": cfg,
                "profile_name": "alice@truba",
            }
        )
        self.widget.panel_scratch.current_dir = "/arf/scratch/alice/project"
        emitted = []
        self.widget.defaultPathsRequested.connect(
            lambda scratch, home: emitted.append((scratch, home))
        )

        self.widget.panel_scratch.set_default_requested.emit()

        self.assertEqual(
            emitted,
            [("/arf/scratch/alice/project", "/arf/home/alice")],
        )

    @pytest.mark.gui
    @pytest.mark.qt

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_profile_update_preserves_other_fields_and_refreshes_session(self) -> None:
        login = LoginWidget()
        cfg = SimpleNamespace(
            system_settings={
                "scratch_dir": "/old/scratch",
                "home_dir": "/old/home",
            }
        )
        login._session = {
            "connected": True,
            "profile_name": "alice@truba",
            "cfg": cfg,
        }
        original = {
            "name": "alice@truba",
            "host": "arf.truba.gov.tr",
            "password_dpapi": "protected-secret",
            "system": {
                "scratch_dir": "/old/scratch",
                "home_dir": "/old/home",
                "status_command": "lssrv-custom",
            },
        }
        emitted = []
        login.session_changed.connect(lambda session: emitted.append(session))
        try:
            with (
                patch.object(
                    login,
                    "_load_profile_by_name",
                    return_value=original,
                ),
                patch.object(login, "refresh_profiles"),
                patch(
                    "hpc_gui.ui.widgets.login_widget.upsert_profile"
                ) as save_profile,
            ):
                self.assertTrue(
                    login.update_active_profile_remote_defaults(
                        "/new/scratch",
                        "/new/home",
                    )
                )
            saved = save_profile.call_args.args[0]
            self.assertEqual(saved["password_dpapi"], "protected-secret")
            self.assertEqual(saved["system"]["status_command"], "lssrv-custom")
            self.assertEqual(saved["system"]["scratch_dir"], "/new/scratch")
            self.assertEqual(cfg.system_settings["home_dir"], "/new/home")
            self.assertEqual(emitted[-1], login._session)
        finally:
            login.deleteLater()

    @pytest.mark.gui
    @pytest.mark.qt
    @pytest.mark.semantic

    @pytest.mark.contract
    @pytest.mark.regression

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_session_uses_configured_scratch_and_home_roots(self) -> None:
        files = _Files()
        cfg = SimpleNamespace(
            username="alice",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
        )
        self.widget.set_session(
            {"connected": True, "files": files, "cfg": cfg}
        )
        self.assertEqual(self.widget.panel_scratch.current_dir, "/arf/scratch/alice")
        self.assertEqual(self.widget.panel_home.current_dir, "/arf/home/alice")
