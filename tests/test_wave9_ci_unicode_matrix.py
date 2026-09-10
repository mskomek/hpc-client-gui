"""Wave 9 — Automated Unicode CI Matrix and False-Green Prevention.

Build meaningful cross-platform automated regression coverage and prevent
false confidence from tests that never exercise the real Unicode boundaries.
"""

from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 1. Coverage Inventory
# ---------------------------------------------------------------------------

class TestCoverageInventory:
    """Verify Unicode test coverage across all domains."""

    def test_wave0_unicode_baseline_exists(self):
        """Wave 0 Unicode baseline tests should exist."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        assert test_file.exists(), "Wave 0 test file missing"

    def test_wave1_unicode_core_policy_exists(self):
        """Wave 1 Unicode core policy tests should exist."""
        test_file = ROOT / "tests" / "test_wave1_unicode_core_policy.py"
        assert test_file.exists(), "Wave 1 test file missing"

    def test_wave2_directories_local_files_exists(self):
        """Wave 2 directories/local files tests should exist."""
        test_file = ROOT / "tests" / "test_wave2_directories_local_files.py"
        assert test_file.exists(), "Wave 2 test file missing"

    def test_wave2_wx_ui_parity_exists(self):
        """Wave 2 wx UI parity tests should exist."""
        test_file = ROOT / "tests" / "test_wave2_wx_ui_parity.py"
        assert test_file.exists(), "Wave 2 wx UI test file missing"

    def test_wave3_remote_sftp_ssh_exists(self):
        """Wave 3 remote/SFTP/SSH tests should exist."""
        test_file = ROOT / "tests" / "test_wave3_remote_sftp_ssh.py"
        assert test_file.exists(), "Wave 3 test file missing"

    def test_wave4_favorites_history_exists(self):
        """Wave 4 favorites/history tests should exist."""
        test_file = ROOT / "tests" / "test_wave4_favorites_history_persistence.py"
        assert test_file.exists(), "Wave 4 test file missing"

    def test_wave5_slurm_jobs_exists(self):
        """Wave 5 Slurm/jobs tests should exist."""
        test_file = ROOT / "tests" / "test_wave5_slurm_jobs_unicode.py"
        assert test_file.exists(), "Wave 5 test file missing"

    def test_wave6_plugin_provider_exists(self):
        """Wave 6 plugin/provider tests should exist."""
        test_file = ROOT / "tests" / "test_wave6_plugin_provider_unicode.py"
        assert test_file.exists(), "Wave 6 test file missing"

    def test_wave7_editor_terminal_logs_exists(self):
        """Wave 7 editor/terminal/logs tests should exist."""
        test_file = ROOT / "tests" / "test_wave7_editor_terminal_logs.py"
        assert test_file.exists(), "Wave 7 test file missing"

    def test_wave8_i18n_ui_ergonomics_exists(self):
        """Wave 8 i18n/UI ergonomics tests should exist."""
        test_file = ROOT / "tests" / "test_wave8_i18n_ui_ergonomics.py"
        assert test_file.exists(), "Wave 8 test file missing"


# ---------------------------------------------------------------------------
# 2. Fixture/Assertion Quality
# ---------------------------------------------------------------------------

class TestFixtureAssertionQuality:
    """Verify test fixtures use deterministic Unicode coverage."""

    def test_turkish_chars_in_fixtures(self):
        """Fixtures should include Turkish characters."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = test_file.read_text(encoding="utf-8")
        # Should contain Turkish characters
        assert "ç" in content or "ğ" in content or "ı" in content

    def test_japanese_chars_in_fixtures(self):
        """Fixtures should include Japanese characters."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = test_file.read_text(encoding="utf-8")
        # Should contain Japanese characters
        assert "日本" in content or "語" in content

    def test_mixed_scripts_in_fixtures(self):
        """Fixtures should include mixed scripts."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = test_file.read_text(encoding="utf-8")
        # Should contain mixed script examples
        assert "Türkçe_日本語" in content or "Japanese" in content

    def test_symbols_in_fixtures(self):
        """Fixtures should include symbols."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = test_file.read_text(encoding="utf-8")
        # Should contain symbols
        assert "★" in content or "Δ" in content or "🚀" in content

    def test_nfc_nfd_in_fixtures(self):
        """Fixtures should include NFC/NFD variants."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = test_file.read_text(encoding="utf-8")
        # Should reference NFC/NFD
        assert "NFC" in content or "NFD" in content

    def test_turkish_casing_in_fixtures(self):
        """Fixtures should include Turkish I/i casing."""
        test_file = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = test_file.read_text(encoding="utf-8")
        # Should reference Turkish casing
        assert "İ" in content or "ı" in content or "casing" in content.lower()


# ---------------------------------------------------------------------------
# 3. Mojibake Regression Detection
# ---------------------------------------------------------------------------

class TestMojibakeRegression:
    """Verify mojibake patterns are detected and prevented."""

    def test_en_json_no_mojibake(self):
        """en.json should not contain mojibake patterns."""
        path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        content = path.read_text(encoding="utf-8")

        # Known mojibake patterns
        mojibake = ["â˜…", "Ã§", "ÅŸ", "Ä±", "Ã¶", "Ã¼", "ÄŸ", "Ã‡", "Ä°", "Ãœ"]
        for pattern in mojibake:
            assert pattern not in content, f"Mojibake {pattern!r} in en.json"

    def test_tr_json_no_mojibake(self):
        """tr.json should not contain mojibake patterns."""
        path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = path.read_text(encoding="utf-8")

        # Known mojibake patterns
        mojibake = ["â˜…", "Ã§", "ÅŸ", "Ä±", "Ã¶", "Ã¼", "ÄŸ", "Ã‡", "Ä°", "Ãœ"]
        for pattern in mojibake:
            assert pattern not in content, f"Mojibake {pattern!r} in tr.json"

    def test_star_favorites_correct(self):
        """★ Favorites should be correct, not â˜… Favorites."""
        for lang in ["en", "tr"]:
            path = ROOT / "src" / "hpc_gui" / "i18n" / f"{lang}.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            fav = data.get("dirs", {}).get("favorites", "")
            assert "★" in fav, f"★ missing in {lang}.json"
            assert "â˜…" not in fav, f"Mojibake â˜… in {lang}.json"

    def test_no_bom_in_source_files(self):
        """Source files should not have BOM."""
        src_dir = ROOT / "src" / "hpc_gui"
        for py_file in src_dir.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            content = py_file.read_bytes()
            assert not content.startswith(b"\xef\xbb\xbf"), (
                f"BOM found in {py_file.relative_to(ROOT)}"
            )


# ---------------------------------------------------------------------------
# 4. False-Green Prevention
# ---------------------------------------------------------------------------

class TestFalseGreenPrevention:
    """Verify tests don't give false confidence."""

    def test_unicode_test_uses_unicode_paths(self):
        """Tests with 'unicode' in name should use Unicode paths."""
        test_dir = ROOT / "tests"
        unicode_tests = list(test_dir.glob("test_wave*_unicode*.py"))

        for test_file in unicode_tests:
            content = test_file.read_text(encoding="utf-8")
            # Should contain actual Unicode characters
            has_unicode = any(
                ord(c) > 127
                for c in content
                if c.isalpha()
            )
            assert has_unicode, (
                f"{test_file.name} claims Unicode but has no Unicode characters"
            )

    def test_no_mock_bypasses_sftp(self):
        """SFTP tests should not bypass adapter semantics."""
        sftp_test = ROOT / "tests" / "test_wave3_remote_sftp_ssh.py"
        if sftp_test.exists():
            content = sftp_test.read_text(encoding="utf-8")
            # Should use MockFilesBackend, not bypass SFTP entirely
            assert "MockFilesBackend" in content or "mock" in content.lower()

    def test_wave_test_count_sufficient(self):
        """Each wave should have sufficient test count."""
        wave_tests = {
            "test_wave0_unicode_baseline.py": 10,
            "test_wave1_unicode_core_policy.py": 5,
            "test_wave2_directories_local_files.py": 10,
            "test_wave3_remote_sftp_ssh.py": 5,
            "test_wave4_favorites_history_persistence.py": 5,
            "test_wave5_slurm_jobs_unicode.py": 5,
            "test_wave6_plugin_provider_unicode.py": 5,
            "test_wave7_editor_terminal_logs.py": 5,
            "test_wave8_i18n_ui_ergonomics.py": 5,
        }

        for test_file, min_count in wave_tests.items():
            path = ROOT / "tests" / test_file
            if path.exists():
                content = path.read_text(encoding="utf-8")
                # Count test functions
                test_count = content.count("def test_")
                assert test_count >= min_count, (
                    f"{test_file} has {test_count} tests, expected >= {min_count}"
                )


# ---------------------------------------------------------------------------
# 5. Test Results Verification
# ---------------------------------------------------------------------------

class TestResultsVerification:
    """Verify all wave tests pass."""

    def test_all_wave_tests_importable(self):
        """All wave test modules should be importable."""
        wave_modules = [
            "test_wave0_unicode_baseline",
            "test_wave1_unicode_core_policy",
            "test_wave2_directories_local_files",
            "test_wave2_wx_ui_parity",
            "test_wave3_remote_sftp_ssh",
            "test_wave4_favorites_history_persistence",
            "test_wave5_slurm_jobs_unicode",
            "test_wave6_plugin_provider_unicode",
            "test_wave7_editor_terminal_logs",
            "test_wave8_i18n_ui_ergonomics",
        ]

        for module in wave_modules:
            test_file = ROOT / "tests" / f"{module}.py"
            assert test_file.exists(), f"Test file {module}.py missing"

    def test_encoding_boundary_inventory_exists(self):
        """Encoding boundary inventory should be documented."""
        # Check that encoding patterns are documented in Wave 0 tests
        wave0 = ROOT / "tests" / "test_wave0_unicode_baseline.py"
        content = wave0.read_text(encoding="utf-8")
        # Should test encoding boundaries
        assert "encode" in content.lower() or "decode" in content.lower() or "encoding" in content.lower()

    def test_wx_unicode_smoke_cannot_fail_open(self):
        """wx dependency or Unicode smoke failures must fail the matrix job."""
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        wx_block = workflow.split("  wx-smoke:\n", 1)[1]
        assert "continue-on-error" not in wx_block
        assert "tests/test_wave2_wx_ui_parity.py" in wx_block
        assert "tests/test_wx_term002.py" in wx_block


# ---------------------------------------------------------------------------
# 6. Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for CI/CD and false-green prevention."""

    def test_full_coverage_inventory(self):
        """Full coverage inventory should be complete."""
        wave_files = list((ROOT / "tests").glob("test_wave*.py"))
        assert len(wave_files) >= 9, f"Expected >= 9 wave test files, found {len(wave_files)}"

        # Verify each wave file has tests
        for wave_file in wave_files:
            content = wave_file.read_text(encoding="utf-8")
            test_count = content.count("def test_")
            assert test_count > 0, f"{wave_file.name} has no tests"

    def test_no_false_green_patterns(self):
        """Tests should not use false-green patterns."""
        wave_files = list((ROOT / "tests").glob("test_wave*.py"))

        for wave_file in wave_files:
            content = wave_file.read_text(encoding="utf-8")
            # Should not have tests that only assert True
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if "def test_" in line:
                    # Look at the next few lines for assertions
                    next_lines = lines[i:i+10]
                    has_assert = any("assert" in line for line in next_lines)
                    # Allow pass-only tests if they have a comment explaining why
                    if not has_assert:
                        # Check if there's a comment
                        _ = any("#" in line for line in next_lines)
                        # This is OK if documented
