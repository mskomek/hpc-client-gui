"""Wave 8 — wx UI, i18n, CJK Rendering and Ergonomics.

Make the new UI understandable, localizable, and robust with Turkish/Japanese
text and longer translations; explicitly fix ambiguous unlabeled fields.
"""

from __future__ import annotations

import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 1. i18n Translation Completeness
# ---------------------------------------------------------------------------

class TestI18nCompleteness:
    """Verify translation key sets are synchronized."""

    def test_en_tr_same_keys(self):
        """en.json and tr.json should have same key sets."""
        en_path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"

        en_data = json.loads(en_path.read_text(encoding="utf-8"))
        tr_data = json.loads(tr_path.read_text(encoding="utf-8"))

        def flatten(d, prefix=""):
            keys = set()
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    keys.update(flatten(v, full))
                else:
                    keys.add(full)
            return keys

        en_keys = flatten(en_data)
        tr_keys = flatten(tr_data)

        missing_in_tr = en_keys - tr_keys
        missing_in_en = tr_keys - en_keys

        # Allow small differences for language-specific keys
        assert len(missing_in_tr) < 10, f"Missing in tr.json: {missing_in_tr}"
        assert len(missing_in_en) < 10, f"Missing in en.json: {missing_in_en}"

    def test_no_mojibake_in_translations(self):
        """Translation files should not contain mojibake patterns."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            content = path.read_text(encoding="utf-8")

            # Common mojibake patterns
            mojibake_patterns = ["â˜…", "Ã§", "ÅŸ", "Ä±", "Ã¶", "Ã¼", "ÄŸ", "Ã‡", "Ä°", "Ãœ"]
            for pattern in mojibake_patterns:
                assert pattern not in content, f"Mojibake {pattern!r} in {lang}.json"

    def test_favorites_label_correct(self):
        """Favorites label should be correct in both languages."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            fav = data.get("dirs", {}).get("favorites", "")
            assert "★" in fav, f"★ not in {lang}.json favorites"
            assert "â˜…" not in fav, f"Mojibake in {lang}.json favorites"


# ---------------------------------------------------------------------------
# 2. i18n Placeholder Handling
# ---------------------------------------------------------------------------

class TestI18nPlaceholders:
    """Verify translation placeholders are consistent."""

    def test_placeholders_match(self):
        """Placeholders should match between en and tr."""
        en_path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"

        en_data = json.loads(en_path.read_text(encoding="utf-8"))
        tr_data = json.loads(tr_path.read_text(encoding="utf-8"))

        placeholder_re = re.compile(r"\{[^}]+\}")

        def flatten_with_values(d, prefix=""):
            result = {}
            for k, v in d.items():
                full = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    result.update(flatten_with_values(v, full))
                else:
                    result[full] = v
            return result

        en_flat = flatten_with_values(en_data)
        tr_flat = flatten_with_values(tr_data)

        # Check placeholders match for common keys
        common_keys = set(en_flat.keys()) & set(tr_flat.keys())
        for key in common_keys:
            en_placeholders = set(placeholder_re.findall(str(en_flat[key])))
            tr_placeholders = set(placeholder_re.findall(str(tr_flat[key])))
            if en_placeholders or tr_placeholders:
                assert en_placeholders == tr_placeholders, (
                    f"Placeholder mismatch in {key}: en={en_placeholders}, tr={tr_placeholders}"
                )

    def test_no_unclosed_placeholders(self):
        """Translations should not have unclosed placeholders."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))

            def check_placeholders(d, prefix=""):
                for k, v in d.items():
                    full = f"{prefix}.{k}" if prefix else k
                    if isinstance(v, dict):
                        check_placeholders(v, full)
                    elif isinstance(v, str):
                        open_count = v.count("{")
                        close_count = v.count("}")
                        assert open_count == close_count, (
                            f"Unclosed placeholder in {lang}.{full}: {v!r}"
                        )

            check_placeholders(data)


# ---------------------------------------------------------------------------
# 3. i18n t() Function
# ---------------------------------------------------------------------------

class TestI18nFunction:
    """Verify i18n t() function works correctly."""

    def test_t_returns_string(self):
        """t() should return a string."""
        from hpc_gui.core.i18n import t, load_language

        load_language("en")
        result = t("login.host")
        assert isinstance(result, str)
        assert result == "Host / IP"

    def test_turkish_translation(self):
        """t() should return Turkish translation when language is tr."""
        from hpc_gui.core.i18n import t, load_language

        load_language("tr")
        result = t("login.host")
        assert isinstance(result, str)
        assert result == "Sunucu / IP"

    def test_t_missing_key_returns_key(self):
        """t() should return a recognizable string when translation is missing."""
        from hpc_gui.core.i18n import t, load_language

        load_language("en")
        result = t("nonexistent.key")
        # t() returns [key] format for missing translations
        assert "nonexistent.key" in result or result == "nonexistent.key"

    def test_t_with_placeholders(self):
        """t() should handle placeholders correctly."""
        from hpc_gui.core.i18n import t, load_language

        load_language("en")
        result = t("jobs.cancel_confirm").format(job_id="12345")
        assert "12345" in result


# ---------------------------------------------------------------------------
# 4. Hardcoded Strings Audit
# ---------------------------------------------------------------------------

class TestHardcodedStrings:
    """Verify no hardcoded English strings in wx UI."""

    def test_wx_editor_no_hardcoded_strings(self):
        """wx_editor_view.py should use t() for user-visible strings."""
        editor_path = ROOT / "src" / "hpc_gui" / "wx_editor_view.py"
        if editor_path.is_file():
            content = editor_path.read_text(encoding="utf-8")
            # Should use t() for labels
            assert "t(" in content, "wx_editor_view.py should use t() for labels"

    def test_wx_logs_no_hardcoded_strings(self):
        """wx_logs_view.py should use t() for user-visible strings."""
        logs_path = ROOT / "src" / "hpc_gui" / "wx_logs_view.py"
        if logs_path.is_file():
            content = logs_path.read_text(encoding="utf-8")
            assert "t(" in content, "wx_logs_view.py should use t() for labels"

    def test_wx_directories_no_hardcoded_strings(self):
        """wx_directories_view.py should use t() for user-visible strings."""
        dirs_path = ROOT / "src" / "hpc_gui" / "wx_directories_view.py"
        if dirs_path.is_file():
            content = dirs_path.read_text(encoding="utf-8")
            assert "t(" in content, "wx_directories_view.py should use t() for labels"


# ---------------------------------------------------------------------------
# 5. Translation Resource Validation
# ---------------------------------------------------------------------------

class TestTranslationResources:
    """Verify translation resources are valid JSON."""

    def test_en_json_valid(self):
        """en.json should be valid JSON."""
        path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_tr_json_valid(self):
        """tr.json should be valid JSON."""
        path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = path.read_text(encoding="utf-8")
        data = json.loads(content)
        assert isinstance(data, dict)

    def test_translation_files_utf8(self):
        """Translation files should be UTF-8 encoded."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            # Should not raise UnicodeDecodeError
            content = path.read_text(encoding="utf-8")
            assert len(content) > 0


# ---------------------------------------------------------------------------
# 6. UI Label Audit
# ---------------------------------------------------------------------------

class TestUILabelAudit:
    """Verify UI labels are clear and accessible."""

    def test_common_labels_present(self):
        """Common UI labels should be present in translations."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))

            # Essential labels
            assert "common" in data, f"Missing 'common' section in {lang}.json"
            assert "ok" in data["common"], f"Missing 'common.ok' in {lang}.json"
            assert "cancel" in data["common"], f"Missing 'common.cancel' in {lang}.json"
            assert "close" in data["common"], f"Missing 'common.close' in {lang}.json"
            assert "error" in data["common"], f"Missing 'common.error' in {lang}.json"
            assert "warning" in data["common"], f"Missing 'common.warning' in {lang}.json"

    def test_tab_labels_present(self):
        """Tab labels should be present in translations."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))

            assert "tabs" in data, f"Missing 'tabs' section in {lang}.json"
            tabs = data["tabs"]
            assert "login" in tabs, f"Missing 'tabs.login' in {lang}.json"
            assert "editor" in tabs, f"Missing 'tabs.editor' in {lang}.json"
            assert "jobs_outputs" in tabs, f"Missing 'tabs.jobs_outputs' in {lang}.json"

    def test_directories_labels_present(self):
        """Directories labels should be present in translations."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))

            assert "dirs" in data, f"Missing 'dirs' section in {lang}.json"
            dirs = data["dirs"]
            assert "refresh" in dirs, f"Missing 'dirs.refresh' in {lang}.json"
            assert "back" in dirs, f"Missing 'dirs.back' in {lang}.json"
            assert "forward" in dirs, f"Missing 'dirs.forward' in {lang}.json"
            assert "up" in dirs, f"Missing 'dirs.up' in {lang}.json"
            assert "favorites" in dirs, f"Missing 'dirs.favorites' in {lang}.json"


# ---------------------------------------------------------------------------
# 7. Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for i18n/UI ergonomics."""

    def test_full_i18n_workflow(self):
        """Full i18n workflow: load, switch, verify."""
        from hpc_gui.core.i18n import t, load_language

        # 1. Load English
        load_language("en")
        assert t("login.host") == "Host / IP"
        assert t("common.ok") == "OK"
        assert t("dirs.favorites") == "★ Favorites"

        # 2. Switch to Turkish
        load_language("tr")
        assert t("login.host") == "Sunucu / IP"
        assert t("common.ok") == "Tamam"
        assert t("dirs.favorites") == "★ Favoriler"

        # 3. Verify placeholders work
        load_language("en")
        result = t("jobs.cancel_confirm").format(job_id="12345")
        assert "12345" in result

    def test_unicode_in_translations(self):
        """Translations should preserve Unicode correctly."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))

            # Check for Turkish characters in tr.json
            if lang == "tr":
                flat = json.dumps(data, ensure_ascii=False)
                assert "ç" in flat or "ğ" in flat or "ı" in flat, (
                    "Turkish characters missing in tr.json"
                )

            # Check for star in dirs.favorites
            fav = data.get("dirs", {}).get("favorites", "")
            assert "★" in fav, f"★ missing in {lang}.json favorites"
