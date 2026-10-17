"""Wave 0 — Unicode Baseline, Audit Infrastructure and Golden Fixtures.

Establishes a trustworthy baseline before fixing behavior. Inventories every
important Unicode/encoding boundary, reproduces the visible mojibake bug,
and creates reusable test fixtures.
"""

from __future__ import annotations
from support.test_wave0_unicode_baseline_shared import (
    CORRECT_STAR,
    JAPANESE_DIRS,
    JAPANESE_FILES,
    MIXED_DIRS,
    MIXED_FILES,
    SYMBOL_FILES,
    TURKISH_CASING,
    TURKISH_DIRS,
    TURKISH_FILES,
    json,
    pathlib,
    pytest,
    sys,
    unicodedata,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

class TestGoldenFixtures:
    """Verify golden fixtures are well-formed and reusable."""

    pytestmark = [pytest.mark.unit, pytest.mark.semantic]

    def test_turkish_dirs_valid(self):
        for d in TURKISH_DIRS:
            assert isinstance(d, str) and len(d) > 0
            # Must be valid NFC
            assert unicodedata.normalize("NFC", d) == d

    def test_turkish_files_valid(self):
        for f in TURKISH_FILES:
            assert isinstance(f, str) and len(f) > 0
            assert unicodedata.normalize("NFC", f) == f

    def test_japanese_dirs_valid(self):
        for d in JAPANESE_DIRS:
            assert isinstance(d, str) and len(d) > 0
            assert unicodedata.normalize("NFC", d) == d

    def test_japanese_files_valid(self):
        for f in JAPANESE_FILES:
            assert isinstance(f, str) and len(f) > 0
            assert unicodedata.normalize("NFC", f) == f

    def test_mixed_dirs_valid(self):
        for d in MIXED_DIRS:
            assert isinstance(d, str) and len(d) > 0
            assert unicodedata.normalize("NFC", d) == d

    def test_mixed_files_valid(self):
        for f in MIXED_FILES:
            assert isinstance(f, str) and len(f) > 0
            assert unicodedata.normalize("NFC", f) == f

    def test_symbol_files_valid(self):
        for f in SYMBOL_FILES:
            assert isinstance(f, str) and len(f) > 0

    def test_turkish_casing_valid(self):
        for f in TURKISH_CASING:
            assert isinstance(f, str) and len(f) > 0

    @pytest.mark.regression
    def test_nfc_nfd_distinct(self):
        """NFC and NFD forms of 'café' should be distinct byte sequences."""
        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        assert nfc != nfd, "NFC and NFD should differ for café"
        assert nfc.encode("utf-8") != nfd.encode("utf-8")

    @pytest.mark.regression
    def test_all_fixtures_survive_json_roundtrip(self):
        """All fixture strings must survive JSON serialization roundtrip."""
        fixtures = (
            TURKISH_DIRS + TURKISH_FILES +
            JAPANESE_DIRS + JAPANESE_FILES +
            MIXED_DIRS + MIXED_FILES +
            SYMBOL_FILES + TURKISH_CASING +
            [CORRECT_STAR]
        )
        for s in fixtures:
            encoded = json.dumps(s, ensure_ascii=False)
            decoded = json.loads(encoded)
            assert decoded == s, f"JSON roundtrip failed for {s!r}"

class TestGoldenFixturesFilesystem:
    """Verify golden fixture names survive filesystem create/read/delete."""

    pytestmark = [pytest.mark.contract, pytest.mark.semantic, pytest.mark.regression]

    def test_turkish_file_create_and_read(self, tmp_path):
        for name in TURKISH_FILES:
            p = tmp_path / name
            p.write_text("test content", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "test content"

    def test_japanese_file_create_and_read(self, tmp_path):
        for name in JAPANESE_FILES:
            p = tmp_path / name
            p.write_text("テスト内容", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "テスト内容"

    def test_mixed_file_create_and_read(self, tmp_path):
        for name in MIXED_FILES:
            p = tmp_path / name
            p.write_text("mixed content 日本語", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "mixed content 日本語"

    def test_symbol_file_create_and_read(self, tmp_path):
        for name in SYMBOL_FILES:
            p = tmp_path / name
            p.write_text("symbol content", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "symbol content"

    def test_turkish_casing_file_create_and_read(self, tmp_path):
        for name in TURKISH_CASING:
            p = tmp_path / name
            p.write_text("casing test", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "casing test"

    def test_nfc_nfd_file_create_and_read(self, tmp_path):
        nfc_name = unicodedata.normalize("NFC", "café.txt")
        nfd_name = unicodedata.normalize("NFD", "café.txt")
        p_nfc = tmp_path / nfc_name
        p_nfd = tmp_path / nfd_name
        p_nfc.write_text("NFC content", encoding="utf-8")
        p_nfd.write_text("NFD content", encoding="utf-8")
        assert p_nfc.read_text(encoding="utf-8") == "NFC content"
        assert p_nfd.read_text(encoding="utf-8") == "NFD content"

    def test_star_file_create_and_read(self, tmp_path):
        p = tmp_path / "★ Favorites.txt"
        p.write_text("star content", encoding="utf-8")
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "star content"
