"""Wave 0 — Unicode Baseline, Audit Infrastructure and Golden Fixtures.

Establishes a trustworthy baseline before fixing behavior. Inventories every
important Unicode/encoding boundary, reproduces the visible mojibake bug,
and creates reusable test fixtures.
"""

from __future__ import annotations
from support.test_wave0_unicode_baseline_shared import (
    CORRECT_STAR,
    MOJIBAKE_STAR,
    json,
    pathlib,
    pytest,
    sys,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

class TestRepositoryBaseline:
    """Verify repository state is real and current."""

    @pytest.mark.audit
    def test_src_directory_exists(self):
        src = ROOT / "src" / "hpc_gui"
        assert src.is_dir(), f"Source directory not found: {src}"

    @pytest.mark.audit
    def test_pyproject_exists(self):
        pyproject = ROOT / "pyproject.toml"
        assert pyproject.is_file(), "pyproject.toml not found"

    @pytest.mark.contract
    def test_wx_is_default_runtime(self):
        runtime_file = ROOT / "src" / "hpc_gui" / "runtime.py"
        assert runtime_file.is_file(), "runtime.py not found"
        content = runtime_file.read_text(encoding="utf-8")
        assert 'DEFAULT_GUI_RUNTIME = "wx"' in content, (
            "wx is not the default GUI runtime (V2 production runtime decision)"
        )

    @pytest.mark.contract
    def test_wx_production_dependencies_match_runtime_decision(self):
        # V2 runtime decision (docs/decisions/V2_RUNTIME_DECISION.md,
        # RUNTIME-DEPENDENCY-001): wx is the V2 production runtime, Qt is
        # legacy-only via the unadvertised `legacy-qt` extra and must not be
        # a mandatory production dependency.
        pyproject = ROOT / "pyproject.toml"
        content = pyproject.read_text(encoding="utf-8")
        assert "wxPython" in content, "wxPython not in dependencies"
        assert "legacy-qt" in content, "legacy-qt extra missing"
        assert "PySide6" in content, "PySide6 legacy-qt extra missing"
        mandatory = content.split("[project.optional-dependencies]")[0]
        assert "PySide6" not in mandatory, (
            "PySide6 must not be a mandatory production dependency "
            "(legacy-qt extra only)"
        )
        # requirements.txt is a gate-scanned production dependency file
        # (scripts/qt_removal_gate.py): it must ship the wx runtime, not Qt.
        req_lines = (ROOT / "requirements.txt").read_text(encoding="utf-8").splitlines()
        assert any(line.strip().startswith("wxPython") for line in req_lines), (
            "wxPython not in requirements.txt production dependencies"
        )
        assert not any("PySide6" in line or "shiboken6" in line for line in req_lines), (
            "Qt must not remain in requirements.txt production dependencies "
            "(legacy-qt extra only)"
        )

    @pytest.mark.audit
    def test_i18n_files_exist(self):
        i18n_dir = ROOT / "src" / "hpc_gui" / "i18n"
        assert i18n_dir.is_dir(), "i18n directory not found"
        en = i18n_dir / "en.json"
        tr = i18n_dir / "tr.json"
        assert en.is_file(), "en.json not found"
        assert tr.is_file(), "tr.json not found"

class TestMojibakeReproduction:
    """Reproduce the known ★ Favorites mojibake bug."""

    @pytest.mark.contract
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_en_favorites_mojibake_exists(self):
        """The mojibake 'â˜… Favorites' has been fixed to '★ Favorites'."""
        en_path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        content = en_path.read_text(encoding="utf-8")
        data = json.loads(content)
        fav = data.get("dirs", {}).get("favorites", "")
        assert fav == "★ Favorites", (
            f"Expected '★ Favorites', got: {fav!r}"
        )

    @pytest.mark.contract
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_tr_favorites_mojibake_exists(self):
        """The mojibake 'â˜… Favoriler' has been fixed to '★ Favoriler'."""
        tr_path = ROOT / "src" / "hpc_gui" / "i18n" / "tr.json"
        content = tr_path.read_text(encoding="utf-8")
        data = json.loads(content)
        fav = data.get("dirs", {}).get("favorites", "")
        assert fav == "★ Favoriler", (
            f"Expected '★ Favoriler', got: {fav!r}"
        )

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.regression
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

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_star_roundtrip(self):
        """★ should survive UTF-8 encode/decode roundtrip."""
        star = CORRECT_STAR
        encoded = star.encode("utf-8")
        decoded = encoded.decode("utf-8")
        assert decoded == star

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_turkish_chars_roundtrip(self):
        """Turkish characters should survive UTF-8 roundtrip."""
        chars = "çğıöşüİÇĞİÖŞÜ"
        assert chars.encode("utf-8").decode("utf-8") == chars

    @pytest.mark.unit
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_japanese_chars_roundtrip(self):
        """Japanese characters should survive UTF-8 roundtrip."""
        chars = "日本語研究計算"
        assert chars.encode("utf-8").decode("utf-8") == chars
