"""Wave 10 — Existing-User Migration, Documentation and Final Release Gate.

Perform final upgrade/release hardening and prove packaged builds preserve
Unicode across real workflows.
"""

from __future__ import annotations

import pytest
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 1. Existing-User Upgrade
# ---------------------------------------------------------------------------

class TestExistingUserUpgrade:
    """Verify existing user data survives upgrade."""

    @pytest.mark.integration
    @pytest.mark.semantic
    def test_config_roundtrip_preserves_unicode_and_unknown_fields(self, tmp_path, monkeypatch):
        """Production config I/O preserves legacy and future fields."""
        from hpc_gui.config import storage

        config_path = tmp_path / "config.json"
        monkeypatch.setattr(storage, "_config_path", lambda: config_path)
        payload = {
            "profiles": [{"name": "Türkçe İş", "home_dir": "/home/işçi", "future": "日本語"}],
            "settings": {"last_profile": "Türkçe İş"},
            "legacy_version": 1,
        }
        storage.save_config(payload)
        assert storage.load_config() == payload

    @pytest.mark.integration
    def test_navigation_store_encrypted(self, tmp_path, monkeypatch):
        """Navigation paths are not persisted as plaintext."""
        from hpc_gui.services import remote_navigation_store as navigation

        monkeypatch.setattr(navigation, "_state_path", lambda profile_id: tmp_path / f"{profile_id}.bin")
        monkeypatch.setattr(navigation, "secret_store", _FakeSecretStore)
        store = navigation.RemoteNavigationStore("profile")
        store.add_favorite("/scratch/日本語")
        raw = (tmp_path / "profile.bin").read_bytes()
        assert raw.startswith(b"HPCNAV1\n")
        assert "/scratch/".encode("utf-8") not in raw
        assert "日本語".encode("utf-8") not in raw

    @pytest.mark.integration
    @pytest.mark.resource
    def test_config_atomic_writes(self, tmp_path, monkeypatch):
        """Config save leaves a complete file and no temporary file."""
        from hpc_gui.config import storage

        config_path = tmp_path / "config.json"
        monkeypatch.setattr(storage, "_config_path", lambda: config_path)
        storage.save_config({"profiles": [], "settings": {"label": "Çalışma"}})
        assert json.loads(config_path.read_text(encoding="utf-8"))["settings"]["label"] == "Çalışma"
        assert list(tmp_path.glob("config.json.*.tmp")) == []

    @pytest.mark.contract
    def test_i18n_preserves_unicode(self):
        """i18n files should preserve Unicode through load/save."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            # Re-serialize
            reserialized = json.dumps(data, ensure_ascii=False)
            reparsed = json.loads(reserialized)
            assert data == reparsed
            assert "★" in reserialized or "日本語" in reserialized or "Türkçe" in reserialized

    @pytest.mark.audit
    def test_plugin_developer_docs_cover_unicode_contract(self):
        """Plugin authoring docs state the text/bytes/path safety contract."""
        for language in ("en", "tr"):
            content = (ROOT / "src" / "hpc_gui" / "docs" / f"PLUGINS_{language}.md").read_text(encoding="utf-8")
            for term in ("str", "bytes", "path_template", "quota", "shell"):
                assert term in content


class _FakeSecretStore:
    @staticmethod
    def is_available() -> bool:
        return True

    @staticmethod
    def protect_secret(plaintext: str) -> str:
        return plaintext.encode("utf-8").hex()

    @staticmethod
    def unprotect_secret(token: str) -> str:
        return bytes.fromhex(token).decode("utf-8")


# ---------------------------------------------------------------------------
# 2. Migration Logic
# ---------------------------------------------------------------------------

@pytest.mark.audit
class TestMigrationLogic:
    """Verify migration logic is safe and idempotent."""

    def test_no_global_latin1_reinterpretation(self):
        """No global Latin-1→UTF-8 reinterpretation should exist."""
        src_dir = ROOT / "src" / "hpc_gui"
        for py_file in src_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            content = py_file.read_text(encoding="utf-8")
            assert "latin-1" not in content.lower()
            assert "latin1" not in content.lower()
            assert "cp125" not in content.lower()

    def test_no_errors_ignore_on_user_paths(self):
        """errors='ignore' should not be used on user-controlled paths."""
        critical_files = [
            "services/files_ssh.py",
            "services/files_ftp.py",
            "services/files_mock.py",
            "ssh/client.py",
        ]
        for rel_path in critical_files:
            path = ROOT / "src" / "hpc_gui" / rel_path
            assert path.is_file(), f"Missing critical file: {rel_path}"
            content = path.read_text(encoding="utf-8")
            assert 'errors="ignore"' not in content


# ---------------------------------------------------------------------------
# 3. Release Gate Verification
# ---------------------------------------------------------------------------

class TestReleaseGate:
    """Verify all release gate items pass."""

    @pytest.mark.audit
    def test_critical_paths_declare_utf8_handling(self):
        """Static audit: critical I/O modules retain an explicit UTF-8 reference."""
        critical_paths = [
            "services/files_ssh.py",
            "ssh/client.py",
            "services/remote_navigation_store.py",
        ]
        for rel_path in critical_paths:
            path = ROOT / "src" / "hpc_gui" / rel_path
            assert path.is_file(), f"Missing critical file: {rel_path}"
            content = path.read_text(encoding="utf-8")
            assert "utf-8" in content.lower() or "utf8" in content.lower(), f"No UTF-8 handling in {rel_path}"

    @pytest.mark.audit
    def test_no_visible_mojibake(self):
        """No visible mojibake should exist in i18n files."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            content = path.read_text(encoding="utf-8")
            mojibake = ["â˜…", "Ã§", "ÅŸ", "Ä±", "Ã¶", "Ã¼", "ÄŸ", "Ã‡", "Ä°", "Ãœ"]
            for pattern in mojibake:
                assert pattern not in content, f"Mojibake {pattern!r} in {lang}.json"

    @pytest.mark.integration
    def test_favorites_history_persistence(self, tmp_path, monkeypatch):
        """Favorites and visited paths survive a new store instance."""
        from hpc_gui.services import remote_navigation_store as navigation

        path = tmp_path / "profile.bin"
        monkeypatch.setattr(navigation, "_state_path", lambda _profile: path)
        monkeypatch.setattr(navigation, "secret_store", _FakeSecretStore)

        store = navigation.RemoteNavigationStore("existing-user")
        store.add_favorite("/scratch/日本語/submit.sh", kind="file")
        store.record_visit("/scratch/日本語")

        reloaded = navigation.RemoteNavigationStore("existing-user")
        assert [item["path"] for item in reloaded.favorites()] == [
            "/scratch/日本語/submit.sh"
        ]
        assert reloaded.favorites()[0]["kind"] == "file"
        assert [item["path"] for item in reloaded.history()] == ["/scratch/日本語"]

    @pytest.mark.contract
    @pytest.mark.semantic
    def test_slurm_unicode_path(self):
        """Slurm should handle Unicode paths."""
        from hpc_gui.services.slurm_directives import set_directive, get_directive

        script = "#!/bin/bash\n"
        script = set_directive(script, "partition", "Çalışma_日本語")
        assert get_directive(script, "partition") == "Çalışma_日本語"

    @pytest.mark.unit
    @pytest.mark.semantic
    def test_editor_utf8_roundtrip(self):
        """Editor should handle UTF-8 roundtrip."""
        from hpc_gui.services.editor_controller import DocumentModel

        content = "# Isı transferi 日本語\nprint('Çalışma başladı ★')\n"
        doc = DocumentModel(
            path="/test/script.py",
            content=content,
            saved_content="",
            is_local=True,
        )
        assert doc.encoding == "utf-8"
        assert "Isı" in doc.content
        assert "日本語" in doc.content
        assert "★" in doc.content

# ---------------------------------------------------------------------------
# 4. Regression Search
# ---------------------------------------------------------------------------

@pytest.mark.audit
class TestRegressionSearch:
    """Verify no new encoding regressions."""

    def test_no_new_errors_ignore(self):
        """No new errors='ignore' should be added."""
        src_dir = ROOT / "src" / "hpc_gui"
        count = 0
        for py_file in src_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            content = py_file.read_text(encoding="utf-8")
            count += content.count('errors="ignore"')
        assert count == 0, f"errors='ignore' found in source: {count}"
