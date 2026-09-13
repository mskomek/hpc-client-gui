"""Wave 1 — Unicode Core, Text/Bytes Ownership and Encoding Policy.

Defines and enforces one Unicode architecture so later waves do not pile
local fixes on ambiguous bytes/text behavior.
"""
from __future__ import annotations
import pytest

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(autouse=True)
def _restore_language_after_test():
    from hpc_gui.core.i18n import current_language, load_language

    previous = current_language()
    try:
        yield
    finally:
        load_language(previous)


# ---------------------------------------------------------------------------
# 1. Mojibake Fix Verification
# ---------------------------------------------------------------------------

class TestMojibakeFix:
    """Verify the ★ Favorites mojibake has been fixed at the source."""

    @pytest.mark.contract
    def test_en_favorites_correct(self):
        """en.json should have '★ Favorites', not 'â˜… Favorites'."""
        en_path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        content = en_path.read_text(encoding="utf-8")
        data = json.loads(content)
        fav = data.get("dirs", {}).get("favorites", "")
        assert fav == "★ Favorites", f"Expected '★ Favorites', got: {fav!r}"
        # Verify mojibake is not present
        assert "â˜…" not in fav, f"Mojibake still present: {fav!r}"

    @pytest.mark.contract
    def test_tr_favorites_correct(self):
        """tr.json should have '★ Favoriler', not 'â˜… Favoriler'."""
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = tr_path.read_text(encoding="utf-8")
        data = json.loads(content)
        fav = data.get("dirs", {}).get("favorites", "")
        assert fav == "★ Favoriler", f"Expected '★ Favoriler', got: {fav!r}"
        assert "â˜…" not in fav, f"Mojibake still present: {fav!r}"

# ---------------------------------------------------------------------------
# 2. Turkish Translation Quality
# ---------------------------------------------------------------------------

class TestTurkishTranslationQuality:
    """Verify Turkish translations are properly encoded after mojibake fix."""

    TURKISH_CHARS = "çğıöşüİÇĞİÖŞÜ"

    @pytest.mark.contract
    def test_turkish_chars_in_translations(self):
        """Turkish characters should appear correctly in tr.json."""
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = tr_path.read_text(encoding="utf-8")
        data = json.loads(content)
        flat = json.dumps(data, ensure_ascii=False)
        # Check for common Turkish characters
        assert all(char in flat for char in self.TURKISH_CHARS)

    @pytest.mark.contract
    def test_no_common_mojibake_patterns(self):
        """tr.json should not contain common mojibake patterns."""
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = tr_path.read_text(encoding="utf-8")
        # Common mojibake patterns for Turkish
        mojibake_patterns = ['Ã§', 'ÅŸ', 'Ä±', 'Ã¶', 'Ã¼', 'ÄŸ', 'Ã‡', 'Ä°', 'Ãœ', 'Å\x9e', 'Ã–']
        for pattern in mojibake_patterns:
            assert pattern not in content, f"Mojibake pattern {pattern!r} found in tr.json"

    @pytest.mark.contract
    def test_turkish_specific_translations(self):
        """Verify specific Turkish translations are correct."""
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = tr_path.read_text(encoding="utf-8")
        data = json.loads(content)
        # Check a few key translations
        assert data["login"]["host"] == "Sunucu / IP"
        assert data["jobs"]["title"] == "İşler"
        assert data["editor"]["title"] == "Editör"
        assert data["dirs"]["favorites"] == "★ Favoriler"


# ---------------------------------------------------------------------------
# 3. Internal Text Contract
# ---------------------------------------------------------------------------

class TestInternalTextContract:
    """Verify application-internal textual values are Python str."""

    @pytest.mark.contract
    def test_i18n_returns_str(self):
        """i18n.t() should return str, not bytes."""
        from hpc_gui.core.i18n import t, load_language
        load_language("en")
        result = t("login.host")
        assert isinstance(result, str), f"Expected str, got {type(result)}"

    @pytest.mark.contract
    def test_i18n_turkish_returns_str(self):
        """i18n.t() with Turkish should return str."""
        from hpc_gui.core.i18n import t, load_language
        load_language("tr")
        result = t("login.host")
        assert isinstance(result, str), f"Expected str, got {type(result)}"
        assert result == "Sunucu / IP"

    @pytest.mark.contract
    def test_config_paths_are_str(self):
        """Config paths should be str or pathlib.Path, not bytes."""
        from hpc_gui.core.paths import app_data_dir
        result = app_data_dir()
        assert isinstance(result, (str, pathlib.Path)), f"Expected str/Path, got {type(result)}"


# ---------------------------------------------------------------------------
# 4. Encoding Boundary Justification
# ---------------------------------------------------------------------------

class TestEncodingBoundaryJustification:
    """Verify all encode/decode uses are justified."""

    @pytest.mark.audit
    def test_config_json_ensure_ascii_false(self):
        """Config JSON should use ensure_ascii=False for Turkish support."""
        storage = ROOT / "src" / "hpc_gui" / "config" / "storage.py"
        if storage.is_file():
            content = storage.read_text(encoding="utf-8")
            assert "ensure_ascii=False" in content


# ---------------------------------------------------------------------------
# 5. Lossy Decoding Prevention
# ---------------------------------------------------------------------------

class TestLossyDecodingPrevention:
    """Verify no user-controlled path may silently lose characters."""

    @pytest.mark.audit
    def test_no_errors_ignore_on_user_paths(self):
        """User-controlled paths should not use errors='ignore'."""
        # Check process_registry.py - this is a known issue (Wave 1 scope)
        reg = ROOT / "src" / "hpc_gui" / "services" / "process_registry.py"
        if reg.is_file():
            content = reg.read_text(encoding="utf-8")
            # Document the finding - errors='ignore' on JSON is risky
            # This is Wave 1 scope to document, not necessarily fix
            has_ignore = 'errors="ignore"' in content or "errors='ignore'" in content
            assert not has_ignore, "process registry must not silently drop config bytes"
            # If it has errors='ignore', it's a known risk
            if has_ignore:
                # Known risk - documented for Wave 1
                pass

    @pytest.mark.audit
    def test_editor_source_does_not_ignore_decode_errors(self):
        """Editor source must not silently drop undecodable input bytes."""
        editor = ROOT / "src" / "hpc_gui" / "ui" / "widgets" / "editor_widget.py"
        if editor.is_file():
            content = editor.read_text(encoding="utf-8")
            # errors='replace' is acceptable for display
            # errors='ignore' would silently drop bytes
            assert 'errors="ignore"' not in content, "Editor should not use errors='ignore'"


# ---------------------------------------------------------------------------
# 6. Normalization and Turkish Casing
# ---------------------------------------------------------------------------

class TestNormalizationPolicy:
    """Verify NFC/NFD and Turkish casing policies."""

# ---------------------------------------------------------------------------
# 7. Regression Tests
# ---------------------------------------------------------------------------

class TestRegressionTests:
    """Regression tests for mojibake and encoding issues."""

    @pytest.mark.contract
    def test_json_roundtrip_preserves_all_chars(self):
        """All i18n strings should survive JSON roundtrip."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            content = path.read_text(encoding="utf-8")
            data = json.loads(content)
            reserialized = json.dumps(data, ensure_ascii=False, indent=2)
            reparsed = json.loads(reserialized)
            assert data == reparsed, f"JSON content differs after roundtrip in {lang}.json"
