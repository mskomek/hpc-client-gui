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

class TestRiskClassification:
    """Document and verify risk classification of findings."""

    @pytest.mark.contract
    @pytest.mark.semantic
    @pytest.mark.regression
    def test_p0_mojibake_documented(self):
        """The mojibake bug was P0 — now fixed at the source."""
        en_path = ROOT / "src" / "hpc_gui" / "i18n" / "en.json"
        content = en_path.read_text(encoding="utf-8")
        data = json.loads(content)
        fav = data.get("dirs", {}).get("favorites", "")
        # P0: Was visible mojibake, now fixed
        assert fav == "★ Favorites", "Mojibake should be fixed"

    @pytest.mark.audit
    def test_p0_ssh_decode_risks_documented(self):
        """SSH decode with errors='replace' is P0 — data loss boundary."""
        client = ROOT / "src" / "hpc_gui" / "ssh" / "client.py"
        if client.is_file():
            content = client.read_text(encoding="utf-8")
            # Document the finding
            assert "decode(" in content
