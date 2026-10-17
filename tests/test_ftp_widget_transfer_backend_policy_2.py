from __future__ import annotations

from support.ftp_widget_test_support import (
    FTP_TEST_MODE_ENV,
    FtpWidgetTestCase,
    LoginWidget,
    MockFilesBackend,
    Path,
    RemoteDirPanel,
    is_ftp_mock_host,
    is_ftp_test_mode_enabled,
    os,
    patch,
    pytest,
    tempfile,
)

class FtpWidgetTests(FtpWidgetTestCase):
    @pytest.mark.integration
    @pytest.mark.semantic
    @pytest.mark.regression
    @pytest.mark.qt
    def test_ftp_mock_round_trips_turkish_file_and_directory_names(self) -> None:
        files = MockFilesBackend()
        panel = self.widget.panel_scratch
        panel.set_session({"connected": True, "files": files})
        remote_dir = "/arf/scratch/user/klasör_çğışü"

        with tempfile.TemporaryDirectory() as tmp:
            local_dir = Path(tmp, "yerel_klasör_İçerik")
            local_dir.mkdir()
            local_file = local_dir / "dosya_çığöşü.txt"
            content = "Türkçe içerik: ÇĞİÖŞÜ çğıöşü\n".encode("utf-8")
            local_file.write_bytes(content)

            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(panel._apply_local_upload([str(local_dir)], remote_dir))

            remote_file = (
                remote_dir
                + "/yerel_klasör_İçerik/dosya_çığöşü.txt"
            )
            self.assertEqual(files._files[remote_file], content)

            target_dir = Path(tmp, "indirilenler_İstanbul")
            target_dir.mkdir()
            with patch.object(
                RemoteDirPanel,
                "_run_plan_with_progress",
                self._run_plan_synchronously,
            ):
                self.assertTrue(
                    panel._apply_remote_download(
                        [remote_dir + "/yerel_klasör_İçerik"],
                        str(target_dir),
                    )
                )

            self.assertEqual(
                (
                    target_dir
                    / "yerel_klasör_İçerik"
                    / "dosya_çığöşü.txt"
                ).read_bytes(),
                content.replace(b"\n", os.linesep.encode("utf-8")),
            )
    @pytest.mark.contract
    @pytest.mark.semantic
    @pytest.mark.qt
    def test_ftp_mock_connection_is_environment_gated(self) -> None:
        with patch.dict(os.environ, {FTP_TEST_MODE_ENV: ""}):
            self.assertFalse(is_ftp_test_mode_enabled())
            self.assertTrue(is_ftp_mock_host("mock"))

        with patch.dict(os.environ, {FTP_TEST_MODE_ENV: "1"}):
            login = LoginWidget()
            try:
                login.host.setText("mock")
                login.username.setText("user")
                emitted = []
                login.session_changed.connect(lambda session: emitted.append(session))
                self.assertTrue(login.connect_clicked())
                self.assertTrue(emitted[-1]["connected"])
                self.assertIsInstance(emitted[-1]["files"], MockFilesBackend)
                self.assertTrue(emitted[-1]["cfg"].dry_run)
            finally:
                login.deleteLater()
