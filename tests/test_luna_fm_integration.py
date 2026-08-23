"""FM-06 integration tests across the Luna FM-01..FM-05 feature set."""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from hpc_gui.config.file_manager_profile import (  # noqa: E402
    normalize_file_manager_settings,
    update_profile_file_manager_settings,
)
from hpc_gui.config.jump_host_profile import normalize_jump_host_settings  # noqa: E402
from hpc_gui.config.storage import (  # noqa: E402
    load_profiles,
    merge_profile_patch,
    upsert_profile,
)
from hpc_gui.services.directory_comparison import CompareStatus  # noqa: E402


def _base_profile(name: str) -> dict:
    return {
        "id": f"id-{name}",
        "name": name,
        "host": f"{name}.example.org",
        "port": 22,
        "username": "user",
        "save_password": False,
        "password": "",
    }


class ProfileCompatibilityMatrixTests(unittest.TestCase):
    """Part A: fixture matrix survives edit/save round trips."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        home = mock.patch.object(Path, "home")
        home.start().return_value = Path(self._tmp.name)
        self.addCleanup(home.stop)

    def _round_trip(self, profile: dict, edits: dict) -> dict:
        upsert_profile(dict(profile))
        stored = next(
            p for p in load_profiles() if p.get("name") == profile["name"]
        )
        upsert_profile(merge_profile_patch(stored, edits))
        return next(p for p in load_profiles() if p.get("id") == profile["id"])

    def test_legacy_basic_profile_round_trip(self) -> None:
        saved = self._round_trip(_base_profile("legacy"), {"host": "new"})
        self.assertEqual(saved["id"], "id-legacy")
        self.assertEqual(saved["host"], "new")

    def test_encrypted_password_preserved_unless_disabled(self) -> None:
        profile = _base_profile("enc")
        profile.update({"password_enc": "tok", "password_salt": "salt"})
        saved = self._round_trip(profile, {"username": "user2"})
        self.assertEqual(saved["password_enc"], "tok")
        self.assertEqual(saved["password_salt"], "salt")
        # Disabling saved password intentionally clears the secret fields
        # (the exact keys LoginWidget.remove_keys lists).
        upsert_profile(dict(profile))
        stored = next(p for p in load_profiles() if p.get("name") == "enc")
        merged = merge_profile_patch(
            stored,
            {"save_password": False},
            remove_keys=("password_dpapi", "password_enc", "password_salt"),
        )
        upsert_profile(merged)
        saved = load_profiles()[0]
        self.assertNotIn("password_enc", saved)

    def test_plugin_provenance_survives_unrelated_edit(self) -> None:
        profile = _base_profile("plug")
        profile["system_template_source"] = {"kind": "plugin", "plugin_id": "p"}
        saved = self._round_trip(profile, {"port": 2222})
        self.assertEqual(saved["system_template_source"]["plugin_id"], "p")

    def test_unknown_top_level_and_nested_keys_survive(self) -> None:
        profile = _base_profile("future")
        profile["vendor_extension"] = {"custom": [1, 2]}
        profile["file_manager"] = {
            "local_start_dir": "/w",
            "mystery_key": {"deep": True},
        }
        profile["jump_host"] = {
            **normalize_jump_host_settings({"enabled": True, "host": "gw"}),
            "future_jump_field": 7,
        }
        saved = self._round_trip(profile, {"username": "u2"})
        self.assertEqual(saved["vendor_extension"], {"custom": [1, 2]})
        self.assertEqual(saved["file_manager"]["mystery_key"], {"deep": True})
        self.assertEqual(saved["jump_host"]["future_jump_field"], 7)
        self.assertTrue(saved["jump_host"]["enabled"])

    def test_malformed_optional_data_normalizes_without_corruption(self) -> None:
        profile = _base_profile("broken")
        profile["file_manager"] = "not-a-dict"
        profile["jump_host"] = 12345
        upsert_profile(dict(profile))
        stored = load_profiles()[0]
        fm = normalize_file_manager_settings(stored.get("file_manager"))
        jump = normalize_jump_host_settings(stored.get("jump_host"))
        self.assertFalse(fm["sync"]["enabled"])
        self.assertFalse(jump["enabled"])
        # Raw values stay untouched on disk until an intentional save.
        self.assertEqual(stored.get("file_manager"), "not-a-dict")

    def test_comparison_enabled_persists_per_profile(self) -> None:
        upsert_profile(_base_profile("cmp"))
        updated = update_profile_file_manager_settings(
            "cmp", {"comparison_enabled": True}
        )
        self.assertTrue(updated["comparison_enabled"])
        self.assertTrue(load_profiles()[0]["file_manager"]["comparison_enabled"])

    def test_renamed_profile_keeps_stable_id_and_state(self) -> None:
        profile = _base_profile("old-name")
        profile["file_manager"] = normalize_file_manager_settings(
            {"local_start_dir": "/keep"}
        )
        upsert_profile(dict(profile))
        stored = load_profiles()[0]
        merged = merge_profile_patch(stored, {"name": "new-name"})
        upsert_profile(merged)
        profiles = load_profiles()
        self.assertEqual(len(profiles), 1)
        self.assertEqual(profiles[0]["name"], "new-name")
        self.assertEqual(profiles[0]["id"], "id-old-name")
        self.assertEqual(profiles[0]["file_manager"]["local_start_dir"], "/keep")

    def test_merge_never_writes_plaintext_password_from_secrets(self) -> None:
        profile = _base_profile("secret")
        profile.update({"password_enc": "tok", "password_salt": "s"})
        upsert_profile(dict(profile))
        merged = merge_profile_patch(load_profiles()[0], {"username": "u3"})
        self.assertEqual(merged.get("password", ""), "")


class _WidgetHarness:
    """Shared get_ftp_state/update_ftp_state patching for widget tests."""

    def __init__(self, local_dir: str | None = None) -> None:
        state_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_state",
            return_value={
                "local_dir": local_dir or os.getcwd(),
                "active_remote": "scratch",
                "splitter_sizes": [500, 500],
            },
        )
        type_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.get_ftp_transfer_type",
            return_value="auto",
        )
        update_patch = mock.patch(
            "hpc_gui.ui.widgets.ftp_widget.update_ftp_state",
            return_value={},
        )
        state_patch.start()
        type_patch.start()
        update_patch.start()
        self._patches = (state_patch, type_patch, update_patch)

    def stop(self) -> None:
        for patcher in reversed(self._patches):
            patcher.stop()


class ProfileSessionIsolationTests(unittest.TestCase):
    """Part B: A -> disconnect -> B -> disconnect -> A leaks nothing."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def _cfg(self, name: str):
        fm = normalize_file_manager_settings(
            {
                "local_start_dir": f"/start/{name}",
                "comparison_enabled": True,
                "sync": {
                    "enabled": True,
                    "local_root": f"/L/{name}",
                    "remote_root": f"/R/{name}",
                },
            }
        )
        return SimpleNamespace(
            username=f"user-{name}",
            system_settings={
                "scratch_dir": "/arf/scratch/{user}",
                "home_dir": "/arf/home/{user}",
            },
            file_manager_settings=fm,
            jump_host_settings=normalize_jump_host_settings(
                {"enabled": True, "host": f"gw-{name}", "port": 2222}
            ),
            transfer_parallelism=4 if name == "beta" else 1,
            keepalive_interval_seconds=60 if name == "beta" else 30,
            host_key_policy="strict" if name == "beta" else "accept-new",
            ssh_timeout=None,
        )

    def test_switching_profiles_does_not_leak_state(self) -> None:
        from hpc_gui.ui.widgets.ftp_widget import FtpWidget

        harness = _WidgetHarness()
        self.addCleanup(harness.stop)
        widget = FtpWidget()
        self.addCleanup(widget.shutdown)
        self.addCleanup(widget.deleteLater)
        files = SimpleNamespace(
            supports_progressive_listing=False,
            listdir_entries=lambda _d: [],
        )

        def connect(cfg_name):
            widget.set_session(
                {
                    "connected": True,
                    "files": files,
                    "cfg": self._cfg(cfg_name),
                    "profile_name": cfg_name,
                }
            )

        connect("alpha")
        alpha_roots = widget._sync_roots
        alpha_parallelism = widget.session["cfg"].transfer_parallelism
        alpha_policy = widget.session["cfg"].host_key_policy
        widget.set_session(None)
        connect("beta")
        self.assertNotEqual(
            (widget._sync_roots.local_root, widget._sync_roots.remote_root),
            (alpha_roots.local_root, alpha_roots.remote_root),
        )
        self.assertEqual(widget.session["cfg"].transfer_parallelism, 4)
        self.assertEqual(widget.session["cfg"].keepalive_interval_seconds, 60)
        self.assertEqual(widget.session["cfg"].host_key_policy, "strict")
        self.assertEqual(widget.session["cfg"].jump_host_settings["host"], "gw-beta")
        widget.set_session(None)
        connect("alpha")
        self.assertEqual(
            (widget._sync_roots.local_root, widget._sync_roots.remote_root),
            ("/L/alpha", "/R/alpha"),
        )
        self.assertEqual(widget.session["cfg"].transfer_parallelism, alpha_parallelism)
        self.assertEqual(widget.session["cfg"].host_key_policy, alpha_policy)
        self.assertEqual(widget.session["cfg"].jump_host_settings["host"], "gw-alpha")


class _Entry:
    def __init__(self, name: str, *, size: int = 1):
        self.name = name
        self.path = name
        self.is_dir = False
        self.size = size
        self.mtime = int(time.time())
        self.mode = 0o644


class _FakeActivePanel:
    """Minimal active-remote-panel double for comparison orchestration."""

    def __init__(self, directory: str) -> None:
        self.current_dir = directory
        self._snapshot: tuple[str, list] = ("", [])

    def set_dir(self, target: str) -> None:
        self.current_dir = target

    def commit(self, directory: str, entries: list) -> None:
        self._snapshot = (directory, list(entries))

    def current_entries_snapshot(self):
        if self._snapshot[0] != self.current_dir:
            return "", []
        return self._snapshot

    def clear_comparison_statuses(self) -> None:
        return None

    def apply_comparison_statuses(self, statuses: dict) -> None:
        self.applied = dict(statuses)


class SyncPlusComparisonOrderingTests(unittest.TestCase):
    """Part C critical scenario: never render B(local) vs A(remote)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def _run_pending(self, widget) -> None:
        widget._comparison_recompute_timer.stop()
        widget._recompute_directory_comparison()

    def test_navigation_ordering_never_shows_mixed_result(self) -> None:
        with tempfile.TemporaryDirectory() as root_a, tempfile.TemporaryDirectory() as root_b:
            Path(root_a, "markerA.txt").write_text("a", encoding="utf-8")
            Path(root_b, "markerB.txt").write_text("b", encoding="utf-8")
            harness = _WidgetHarness(local_dir=root_a)
            self.addCleanup(harness.stop)
            from hpc_gui.ui.widgets.ftp_widget import FtpWidget

            listing_calls: list[str] = []

            def fake_listdir(d):
                listing_calls.append(d)
                # Remote B contains markerB; remote A contains markerA.
                if d.rstrip("/").endswith("/remote/B"):
                    return [_Entry("markerB.txt")]
                return [_Entry("markerA.txt")]

            files = SimpleNamespace(
                supports_progressive_listing=False,
                listdir_entries=fake_listdir,
            )
            cfg = SimpleNamespace(
                username="user",
                system_settings={
                    "scratch_dir": "/arf/scratch/{user}",
                    "home_dir": "/arf/home/{user}",
                },
                file_manager_settings=normalize_file_manager_settings(
                    {
                        "comparison_enabled": True,
                        "sync": {
                            "enabled": True,
                            "local_root": "/syncroot",
                            "remote_root": "/remote",
                        },
                    }
                ),
            )
            widget = FtpWidget()
            self.addCleanup(widget.shutdown)
            self.addCleanup(widget.deleteLater)
            widget.set_session(
                {
                    "connected": True,
                    "files": files,
                    "cfg": cfg,
                    "profile_name": "lab",
                }
            )
            active_panel = _FakeActivePanel("/remote/A")
            with mock.patch.object(
                FtpWidget, "active_remote_panel", return_value=active_panel
            ):
                widget.btn_sync_browsing.setChecked(True)
                # Stage 1: A/A displayed and compared as SAME.
                widget.local_panel.refresh()
                active_panel.commit(
                    "/remote/A",
                    [
                        SimpleNamespace(
                            name="markerA.txt",
                            path="/remote/A/markerA.txt",
                            is_dir=False,
                            size=1,
                            mtime=int(time.time()),
                            mode=0o644,
                        )
                    ],
                )
                self._run_pending(widget)
                self.assertEqual(
                    widget.local_panel._comparison_statuses.get("markerA.txt"),
                    CompareStatus.SAME,
                )
                # Stage 2/3: user navigates local to B; sync maps the remote
                # side immediately.  While the remote B listing has not
                # landed, the old result must be cleared/waiting - never a
                # mixed A/B view.
                widget.local_panel.current_dir = root_b
                widget.local_panel.refresh()
                active_panel.set_dir("/remote/B")
                self._run_pending(widget)
                self.assertEqual(widget.local_panel._comparison_statuses or {}, {})
                self.assertNotEqual(widget._comparison_waiting_reason, "")
                # Stage 5/7: remote B listing lands and commits.
                active_panel.commit(
                    "/remote/B",
                    [
                        SimpleNamespace(
                            name="markerB.txt",
                            path="/remote/B/markerB.txt",
                            is_dir=False,
                            size=1,
                            mtime=int(time.time()),
                            mode=0o644,
                        )
                    ],
                )
                self._run_pending(widget)
                # Only B-vs-B is rendered, exactly once coherent.
                self.assertEqual(
                    widget.local_panel._comparison_statuses,
                    {"markerB.txt": CompareStatus.SAME},
                )


class ZeroExtraNetworkIntegrationTests(unittest.TestCase):
    """Part E: comparison never causes extra SFTP traffic end-to-end."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = QApplication.instance() or QApplication([])
        from hpc_gui.core.i18n import load_language

        load_language("en")

    def test_full_scenario_counters(self) -> None:
        with tempfile.TemporaryDirectory() as local_dir:
            Path(local_dir, "same.txt").write_text("x", encoding="utf-8")
            harness = _WidgetHarness(local_dir=local_dir)
            self.addCleanup(harness.stop)
            from hpc_gui.ui.widgets.ftp_widget import FtpWidget

            counters = {"list": 0, "stat": 0, "checksum": 0}

            def counting_listdir(_d):
                counters["list"] += 1
                return [_Entry("same.txt")]

            files = SimpleNamespace(
                supports_progressive_listing=False,
                listdir_entries=counting_listdir,
                stat=lambda *_a, **_k: counters.__setitem__("stat", counters["stat"] + 1),
            )
            cfg = SimpleNamespace(
                username="user",
                system_settings={
                    "scratch_dir": "/arf/scratch/{user}",
                    "home_dir": "/arf/home/{user}",
                },
                file_manager_settings=normalize_file_manager_settings({}),
            )
            widget = FtpWidget()
            self.addCleanup(widget.shutdown)
            self.addCleanup(widget.deleteLater)

            def run_pending():
                if widget._comparison_recompute_timer.isActive():
                    widget._comparison_recompute_timer.stop()
                    widget._recompute_directory_comparison()

            # 1. normal remote folder load -> exactly one listing (from
            # set_session's Scratch navigation).
            widget.set_session(
                {
                    "connected": True,
                    "files": files,
                    "cfg": cfg,
                    "profile_name": "lab",
                }
            )
            baseline = counters["list"]
            self.assertGreaterEqual(baseline, 1)
            # 2. enable comparison -> unchanged.
            widget.panel_scratch.current_dir = "/arf/scratch/user"
            widget.panel_scratch._commit_snapshot("/arf/scratch/user", [_Entry("same.txt")])
            widget.btn_compare_directories.setChecked(True)
            # 3. repeated recomputes -> unchanged.
            for _ in range(3):
                widget._schedule_comparison_recompute()
                run_pending()
            self.assertEqual(counters["list"], baseline)
            self.assertEqual(counters["stat"], 0)
            self.assertEqual(counters["checksum"], 0)
            # 4. explicit refresh -> increments exactly because of refresh.
            widget.panel_scratch.refresh(force=True)
            self.assertEqual(counters["list"], baseline + 1)
            # 5. comparison after refresh -> no further increment.
            widget._schedule_comparison_recompute()
            run_pending()
            self.assertEqual(counters["list"], baseline + 1)


class TransferSourceOfTruthAndSecurityTests(unittest.TestCase):
    """Part F/G spot checks that pin the integrated guarantees."""

    def test_global_parallel_setting_is_not_imported_by_remote_panel(self) -> None:
        from hpc_gui.ui.widgets import remote_dir_panel

        self.assertFalse(
            hasattr(remote_dir_panel, "get_transfer_parallelism"),
            "Remote panel must not consult the deprecated global setting",
        )

    def test_no_auto_add_policy_anywhere_in_ssh_layer(self) -> None:
        for source in (
            Path("src/hpc_gui/ssh/client.py"),
            Path("src/hpc_gui/ssh/jump.py"),
        ):
            text = source.read_text(encoding="utf-8")
            self.assertNotIn("AutoAddPolicy", text)

    def test_jump_profile_schema_has_no_password_key(self) -> None:
        settings = normalize_jump_host_settings(
            {"enabled": True, "host": "gw", "password": "should-not-survive"}
        )
        self.assertNotIn("password", settings)


if __name__ == "__main__":
    unittest.main()
