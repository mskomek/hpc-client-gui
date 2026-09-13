"""Wave 0 — Unicode Baseline, Audit Infrastructure and Golden Fixtures.

Establishes a trustworthy baseline before fixing behavior. Inventories every
important Unicode/encoding boundary, reproduces the visible mojibake bug,
and creates reusable test fixtures.
"""
from __future__ import annotations
import pytest

import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Golden Fixtures — Reusable Unicode test data
# ---------------------------------------------------------------------------

# Turkish characters
TURKISH_DIRS = [
    "İşler_Çağrı_Ölçüm",
    "Isı_İstanbul_Şehir",
    "Üniversite_Kümesi",
]
TURKISH_FILES = [
    "ısı_ölçümü_İstanbul.txt",
    "şğüöçıİ.dat",
    "Çalışma_Sonucu.txt",
    "O'Brien_Çalışma.txt",
]

# Japanese characters
JAPANESE_DIRS = [
    "研究_ジョブ",
    "計算_結果",
    "日本語_ディレクトリ",
]
JAPANESE_FILES = [
    "日本語_計算結果.txt",
    "ジョブ結果.slurm",
    "研究_スクリプト.sh",
]

# Mixed scripts
MIXED_DIRS = [
    "Türkçe_日本語",
]
MIXED_FILES = [
    "iş_日本語_δ.txt",
    "Çalışma_Sonucu_日本語.txt",
]

# Symbol/special fixtures
SYMBOL_FILES = [
    "★_Favorites.txt",
    "ΔPressure_ölçüm.txt",
    "🚀_job.txt",
]

# Turkish I/i casing variants
TURKISH_CASING = [
    "I_upper.txt",
    "İ_upper.txt",
    "ı_lower.txt",
    "i_lower.txt",
]

# NFC/NFD normalization variants
NFC_PATH = pathlib.PurePosixPath("café.txt")  # NFC: é = U+00E9
NFD_PATH = pathlib.PurePosixPath(unicodedata.normalize("NFD", "café.txt"))  # NFD: e + combining acute

# Mojibake reference
MOJIBAKE_STAR = "â˜…"
CORRECT_STAR = "★"


# ---------------------------------------------------------------------------
# Helper: Normalize path for cross-platform comparison
# ---------------------------------------------------------------------------

def _norm(p: str) -> str:
    """NFC-normalize a path string for comparison."""
    return unicodedata.normalize("NFC", p)


# ---------------------------------------------------------------------------
# 1. Repository Baseline
# ---------------------------------------------------------------------------

@pytest.mark.audit
class TestRepositoryBaseline:
    """Verify repository state is real and current."""

    def test_src_directory_exists(self):
        src = ROOT / "src" / "hpc_gui"
        assert src.is_dir(), f"Source directory not found: {src}"

    def test_pyproject_exists(self):
        pyproject = ROOT / "pyproject.toml"
        assert pyproject.is_file(), "pyproject.toml not found"

    def test_qt_is_default_runtime(self):
        runtime_file = ROOT / "src" / "hpc_gui" / "runtime.py"
        assert runtime_file.is_file(), "runtime.py not found"
        content = runtime_file.read_text(encoding="utf-8")
        assert 'DEFAULT_GUI_RUNTIME = "qt"' in content, (
            "Qt is no longer the default GUI runtime"
        )

    def test_pyside6_in_dependencies(self):
        pyproject = ROOT / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert "PySide6" in content, "PySide6 not in dependencies"

    def test_i18n_files_exist(self):
        i18n_dir = ROOT / "src" / "hpc_gui" / "i18n"
        assert i18n_dir.is_dir(), "i18n directory not found"
        en = i18n_dir / "en.json"
        tr = i18n_dir / "tr.json"
        assert en.is_file(), "en.json not found"
        assert tr.is_file(), "tr.json not found"


# ---------------------------------------------------------------------------
# 2. Mojibake Reproduction
# ---------------------------------------------------------------------------

class TestMojibakeReproduction:
    """Reproduce the known ★ Favorites mojibake bug."""

    @pytest.mark.contract
    def test_mojibake_is_corrupted_star(self):
        """Demonstrate the corruption chain: ★ → UTF-8 bytes → Windows-1252 decode → re-encode.

        The mojibake 'â˜…' in the JSON file is the result of:
        1. Original character: ★ (U+2605)
        2. UTF-8 encode: b'\\xe2\\x98\\x85'
        3. Windows-1252 decode: 'â˜…' (â=\\xe2, ˜=\\x98, …=\\x85)
        4. UTF-8 encode back to file: the mojibake string
        """
        correct = CORRECT_STAR
        utf8_bytes = correct.encode("utf-8")
        # Windows-1252 (cp1252) is the likely intermediary encoding
        mojibake = utf8_bytes.decode("cp1252", errors="replace")
        assert mojibake == MOJIBAKE_STAR, (
            f"Mojibake reconstruction failed: {mojibake!r}"
        )

    @pytest.mark.contract
    def test_star_roundtrip(self):
        """★ should survive UTF-8 encode/decode roundtrip."""
        star = CORRECT_STAR
        encoded = star.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == star

    @pytest.mark.contract
    def test_turkish_chars_roundtrip(self):
        """Turkish characters should survive UTF-8 roundtrip."""
        chars = "çğıöşüİÇĞİÖŞÜ"
        assert chars.encode("utf-8").decode("utf-8") == chars

    @pytest.mark.contract
    def test_japanese_chars_roundtrip(self):
        """Japanese characters should survive UTF-8 roundtrip."""
        chars = "日本語研究計算"
        assert chars.encode("utf-8").decode("utf-8") == chars


# ---------------------------------------------------------------------------
# 3. Golden Fixtures — Path Validity
# ---------------------------------------------------------------------------

class TestGoldenFixtures:
    """Verify golden fixtures are well-formed and reusable."""

    @pytest.mark.contract
    def test_turkish_dirs_valid(self):
        for d in TURKISH_DIRS:
            assert isinstance(d, str) and len(d) > 0
            # Must be valid NFC
            assert unicodedata.normalize("NFC", d) == d

    @pytest.mark.contract
    def test_turkish_files_valid(self):
        for f in TURKISH_FILES:
            assert isinstance(f, str) and len(f) > 0
            assert unicodedata.normalize("NFC", f) == f

    @pytest.mark.contract
    def test_japanese_dirs_valid(self):
        for d in JAPANESE_DIRS:
            assert isinstance(d, str) and len(d) > 0
            assert unicodedata.normalize("NFC", d) == d

    @pytest.mark.contract
    def test_japanese_files_valid(self):
        for f in JAPANESE_FILES:
            assert isinstance(f, str) and len(f) > 0
            assert unicodedata.normalize("NFC", f) == f

    @pytest.mark.contract
    def test_mixed_dirs_valid(self):
        for d in MIXED_DIRS:
            assert isinstance(d, str) and len(d) > 0
            assert unicodedata.normalize("NFC", d) == d

    @pytest.mark.contract
    def test_mixed_files_valid(self):
        for f in MIXED_FILES:
            assert isinstance(f, str) and len(f) > 0
            assert unicodedata.normalize("NFC", f) == f

    @pytest.mark.contract
    def test_symbol_files_valid(self):
        for f in SYMBOL_FILES:
            assert isinstance(f, str) and len(f) > 0

    @pytest.mark.contract
    def test_turkish_casing_valid(self):
        for f in TURKISH_CASING:
            assert isinstance(f, str) and len(f) > 0

    @pytest.mark.contract
    def test_nfc_nfd_distinct(self):
        """NFC and NFD forms of 'café' should be distinct byte sequences."""
        nfc = unicodedata.normalize("NFC", "café")
        nfd = unicodedata.normalize("NFD", "café")
        assert nfc != nfd, "NFC and NFD should differ for café"
        assert nfc.encode("utf-8") != nfd.encode("utf-8")

    @pytest.mark.contract
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


# ---------------------------------------------------------------------------
# 4. Golden Fixtures — Filesystem Operations
# ---------------------------------------------------------------------------

class TestGoldenFixturesFilesystem:
    """Verify golden fixture names survive filesystem create/read/delete."""

    @pytest.mark.contract
    def test_turkish_file_create_and_read(self, tmp_path):
        for name in TURKISH_FILES:
            p = tmp_path / name
            p.write_text("test content", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "test content"

    @pytest.mark.contract
    def test_japanese_file_create_and_read(self, tmp_path):
        for name in JAPANESE_FILES:
            p = tmp_path / name
            p.write_text("テスト内容", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "テスト内容"

    @pytest.mark.contract
    def test_mixed_file_create_and_read(self, tmp_path):
        for name in MIXED_FILES:
            p = tmp_path / name
            p.write_text("mixed content 日本語", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "mixed content 日本語"

    @pytest.mark.contract
    def test_symbol_file_create_and_read(self, tmp_path):
        for name in SYMBOL_FILES:
            p = tmp_path / name
            p.write_text("symbol content", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "symbol content"

    @pytest.mark.contract
    def test_turkish_casing_file_create_and_read(self, tmp_path):
        for name in TURKISH_CASING:
            p = tmp_path / name
            p.write_text("casing test", encoding="utf-8")
            assert p.exists()
            assert p.read_text(encoding="utf-8") == "casing test"

    @pytest.mark.contract
    def test_nfc_nfd_file_create_and_read(self, tmp_path):
        nfc_name = unicodedata.normalize("NFC", "café.txt")
        nfd_name = unicodedata.normalize("NFD", "café.txt")
        p_nfc = tmp_path / nfc_name
        p_nfd = tmp_path / nfd_name
        p_nfc.write_text("NFC content", encoding="utf-8")
        p_nfd.write_text("NFD content", encoding="utf-8")
        assert p_nfc.read_text(encoding="utf-8") == "NFC content"
        assert p_nfd.read_text(encoding="utf-8") == "NFD content"

    @pytest.mark.contract
    def test_star_file_create_and_read(self, tmp_path):
        p = tmp_path / "★ Favorites.txt"
        p.write_text("star content", encoding="utf-8")
        assert p.exists()
        assert p.read_text(encoding="utf-8") == "star content"


# ---------------------------------------------------------------------------
# 5. Encoding Boundary Inventory
# ---------------------------------------------------------------------------

class TestEncodingBoundaryInventory:
    """Verify encoding boundary patterns exist and are cataloged."""

    @pytest.mark.contract
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
    def test_files_ssh_uses_utf8(self):
        """services/files_ssh.py should use UTF-8 for SFTP text operations."""
        ssh_files = ROOT / "src" / "hpc_gui" / "services" / "files_ssh.py"
        if ssh_files.is_file():
            content = ssh_files.read_text(encoding="utf-8")
            assert 'data.decode("utf-8")' in content
            assert 'text.encode("utf-8")' in content

    @pytest.mark.audit
    def test_shell_session_uses_utf8_decoder(self):
        """ssh/shell_session.py should use UTF-8 incremental decoder."""
        shell = ROOT / "src" / "hpc_gui" / "ssh" / "shell_session.py"
        if shell.is_file():
            content = shell.read_text(encoding="utf-8")
            assert 'codecs.getincrementaldecoder("utf-8")("replace")' in content

    @pytest.mark.audit
    def test_errors_replace_in_ssh(self):
        """SSH output decoding should use errors='replace'."""
        client = ROOT / "src" / "hpc_gui" / "ssh" / "client.py"
        if client.is_file():
            content = client.read_text(encoding="utf-8")
            assert 'errors="replace"' in content or "errors='replace'" in content


# ---------------------------------------------------------------------------
# 6. i18n Translation Completeness
# ---------------------------------------------------------------------------

class TestI18nCompleteness:
    """Verify translation key sets are synchronized."""

    @pytest.mark.contract
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


# ---------------------------------------------------------------------------
# 7. Plugin/Provider Unicode Contract
# ---------------------------------------------------------------------------

class TestPluginProviderUnicode:
    """Verify plugin/provider data can handle Unicode."""

    @pytest.mark.audit
    def test_plugin_manifest_supports_unicode(self):
        """Plugin manifest loading should handle Unicode."""
        loader = ROOT / "src" / "hpc_gui" / "plugins" / "loader.py"
        assert loader.is_file(), "Plugin loader not found"
        content = loader.read_text(encoding="utf-8")
        assert 'path.open("r", encoding="utf-8")' in content


# ---------------------------------------------------------------------------
# 8. Risk Classification Summary
# ---------------------------------------------------------------------------

class TestRiskClassification:
    """Document and verify risk classification of findings."""
