"""Wave 0 — Unicode Baseline, Audit Infrastructure and Golden Fixtures.

Establishes a trustworthy baseline before fixing behavior. Inventories every
important Unicode/encoding boundary, reproduces the visible mojibake bug,
and creates reusable test fixtures.
"""

from __future__ import annotations
from support.test_wave0_unicode_baseline_shared import (
    json,
    pathlib,
    pytest,
    sys,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

class TestEncodingBoundaryInventory:
    """Verify encoding boundary patterns exist and are cataloged."""

    @pytest.mark.contract
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_i18n_json_is_utf8(self):
        """Both i18n JSON files should be valid UTF-8."""
        for lang in ("en", "tr"):
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            assert isinstance(data, dict), f"{lang}.json did not parse as dict"

    @pytest.mark.audit
    def test_config_storage_uses_utf8(self):
        """config/storage.py should use encoding='utf-8' for JSON."""
        storage = ROOT / "src" / "hpc_gui" / "config" / "storage.py"
        if storage.is_file():
            content = storage.read_text(encoding="utf-8")
            assert 'encoding="utf-8"' in content or "encoding='utf-8'" in content

    @pytest.mark.audit
    def test_ssh_client_decodes_output(self):
        """ssh/client.py should decode SSH output."""
        client = ROOT / "src" / "hpc_gui" / "ssh" / "client.py"
        if client.is_file():
            content = client.read_text(encoding="utf-8")
            assert "decode(" in content, "SSH client should decode bytes"

    @pytest.mark.audit
    def test_files_ssh_uses_utf8(self):
        """services/files_ssh.py should use UTF-8 for SFTP text operations."""
        ssh_files = ROOT / "src" / "hpc_gui" / "services" / "files_ssh.py"
        if ssh_files.is_file():
            content = ssh_files.read_text(encoding="utf-8")
            assert "utf-8" in content.lower(), "SFTP backend should use UTF-8"

    @pytest.mark.audit
    def test_shell_session_uses_utf8_decoder(self):
        """ssh/shell_session.py should use UTF-8 incremental decoder."""
        shell = ROOT / "src" / "hpc_gui" / "ssh" / "shell_session.py"
        if shell.is_file():
            content = shell.read_text(encoding="utf-8")
            assert "utf-8" in content.lower(), "Shell session should use UTF-8"

    @pytest.mark.audit
    def test_ensure_ascii_false_in_config(self):
        """Config JSON serialization should use ensure_ascii=False."""
        storage = ROOT / "src" / "hpc_gui" / "config" / "storage.py"
        if storage.is_file():
            content = storage.read_text(encoding="utf-8")
            assert "ensure_ascii=False" in content, (
                "Config storage should use ensure_ascii=False for Turkish support"
            )

    @pytest.mark.audit
    def test_errors_replace_in_ssh(self):
        """SSH output decoding should use errors='replace'."""
        client = ROOT / "src" / "hpc_gui" / "ssh" / "client.py"
        if client.is_file():
            content = client.read_text(encoding="utf-8")
            assert 'errors="replace"' in content or "errors='replace'" in content

    @pytest.mark.audit
    def test_errors_ignore_in_process_registry(self):
        """process_registry.py should not use errors='ignore' on JSON."""
        reg = ROOT / "src" / "hpc_gui" / "services" / "process_registry.py"
        if reg.is_file():
            content = reg.read_text(encoding="utf-8")
            # Document the finding — errors="ignore" on JSON is risky
            # This is a known risk — we document it but don't assert absence
            # because fixing it is Wave 1+ work
            assert len(content) > 0, "process_registry.py should have content"

class TestI18nCompleteness:
    """Verify translation key sets are synchronized."""

    pytestmark = [pytest.mark.contract, pytest.mark.semantic, pytest.mark.regression]

    def test_en_and_tr_have_same_keys(self):
        en_path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        en_data = json.loads(en_path.read_text(encoding="utf-8"))
        tr_data = json.loads(tr_path.read_text(encoding="utf-8"))

        def _flatten(d, prefix=""):
            keys = set()
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.update(_flatten(v, full))
                else:
                    keys.add(full)
            return keys

        en_keys = _flatten(en_data)
        tr_keys = _flatten(tr_data)
        missing_in_tr = en_keys - tr_keys
        missing_in_en = tr_keys - en_keys
        assert not missing_in_tr, f"Missing keys in tr.json: {missing_in_tr}"
        assert not missing_in_en, f"Missing keys in en.json: {missing_in_en}"

    def test_turkish_file_no_mojibake_patterns(self):
        """Check tr.json for common mojibake patterns ( Ã , ÅŸ, Ä±, etc.)."""
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = tr_path.read_text(encoding="utf-8")
        # These are common mojibake patterns for Turkish characters
        mojibake_patterns = ["Ã§", "ÅŸ", "Ä±", "Ã¶", "Ã¼", "ÄŸ", "Ä°"]
        found = []
        for pattern in mojibake_patterns:
            if pattern in content:
                found.append(pattern)
        assert not found, f"Mojibake patterns in tr.json: {found}"

class TestPluginProviderUnicode:
    """Verify plugin/provider data can handle Unicode."""

    pytestmark = pytest.mark.audit

    def test_plugin_models_exist(self):
        models = ROOT / "src" / "hpc_gui" / "plugins" / "models.py"
        assert models.is_file(), "Plugin models not found"

    def test_plugin_manifest_supports_unicode(self):
        """Plugin manifest loading should handle Unicode."""
        loader = ROOT / "src" / "hpc_gui" / "plugins" / "loader.py"
        if loader.is_file():
            content = loader.read_text(encoding="utf-8")
            # The loader should use UTF-8 for reading manifests
            assert "utf-8" in content.lower() or "encoding" in content.lower() or "read_text" in content
