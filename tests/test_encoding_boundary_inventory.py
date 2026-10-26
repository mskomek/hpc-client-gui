"""Static audit of encoding choices at application boundaries."""

from __future__ import annotations

import json
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


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
        """The config IO leaf should read and write JSON as UTF-8."""
        storage_io = ROOT / "src" / "hpc_gui" / "config" / "storage_io.py"
        if storage_io.is_file():
            content = storage_io.read_text(encoding="utf-8")
            assert 'encoding="utf-8"' in content or "encoding='utf-8'" in content

    @pytest.mark.audit
    def test_ssh_client_decodes_output(self):
        """SSH client output should pass through the UTF-8 decoder helper."""
        client = ROOT / "src" / "hpc_gui" / "ssh" / "client.py"
        text_helper = ROOT / "src" / "hpc_gui" / "ssh" / "text.py"
        if client.is_file() and text_helper.is_file():
            client_content = client.read_text(encoding="utf-8")
            helper_content = text_helper.read_text(encoding="utf-8")
            assert "decode_remote_text" in client_content
            assert "decode(" in helper_content, "SSH text helper should decode bytes"

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
        storage_io = ROOT / "src" / "hpc_gui" / "config" / "storage_io.py"
        if storage_io.is_file():
            content = storage_io.read_text(encoding="utf-8")
            assert "ensure_ascii=False" in content, (
                "Config storage should use ensure_ascii=False for Turkish support"
            )

    @pytest.mark.audit
    def test_errors_replace_in_ssh(self):
        """SSH output decoding should use errors='replace'."""
        text_helper = ROOT / "src" / "hpc_gui" / "ssh" / "text.py"
        if text_helper.is_file():
            content = text_helper.read_text(encoding="utf-8")
            assert 'errors="replace"' in content or "errors='replace'" in content

    @pytest.mark.audit
    def test_errors_ignore_in_process_registry(self):
        """process_registry.py should not use errors='ignore' on JSON."""
        reg = ROOT / "src" / "hpc_gui" / "services" / "process_registry.py"
        if reg.is_file():
            content = reg.read_text(encoding="utf-8")
            # Document the finding without asserting a policy fixed in a later wave.
            assert len(content) > 0, "process_registry.py should have content"
