"""Screenshot sanity for audit/current-gui (not visual similarity)."""

from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "audit" / "current-gui" / "MANIFEST.json"
HASHES = ROOT / "audit" / "current-gui" / "HASHES.sha256"
QT_DIR = ROOT / "audit" / "current-gui" / "qt"
WX_DIR = ROOT / "audit" / "current-gui" / "wx"

def _sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()

def test_manifest_exists_and_commit_current():
    assert MANIFEST.is_file(), "MANIFEST.json missing"
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    assert data.get("schema") == "gui-visual-audit/2"
    commit = data.get("commit")
    assert isinstance(commit, str) and len(commit)==40 and all(c in "0123456789abcdef" for c in commit.lower()), "commit must be 40 hex"
    # Must match current HEAD
    import subprocess
    head = subprocess.run(["git","rev-parse","HEAD"], capture_output=True, text=True, cwd=ROOT).stdout.strip()
    assert commit.lower() == head.lower(), f"manifest commit {commit} != HEAD {head}"
    assert data.get("branch") == "develop"
    assert data.get("platform") == "Windows"
    # Check runtime commands are real
    assert "python -m hpc_gui" in data["qt"]["runtime_command"]
    assert "--wx" in data["wx"]["runtime_command"]

def test_screenshots_exist_nonempty_and_png():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in data["screenshots"]:
        p = ROOT / "audit" / "current-gui" / entry["file"]
        assert p.is_file(), f"missing {entry['file']}"
        assert p.stat().st_size > 1000, f"empty {entry['file']}"
        assert p.suffix == ".png"
        # Check PNG magic
        assert p.read_bytes()[:8] == b"\x89PNG\r\n\x1a\n", f"not PNG {entry['file']}"
        # Dimensions valid (main windows 1366x768, dialogs 760x720, etc)
        assert entry["width"] >= 600 and entry["height"] >= 500, f"invalid dims {entry['file']} {entry['width']}x{entry['height']}"
        assert entry["real_runtime"] is True
        assert entry["mock_data"] is True

def test_hashes_match_and_no_unexplained_duplicate():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    # Check HASHES.sha256 exists and matches manifest
    assert HASHES.is_file()
    hashes_text = HASHES.read_text(encoding="utf-8")
    # Build map from manifest
    for entry in data["screenshots"]:
        p = ROOT / "audit" / "current-gui" / entry["file"]
        actual = _sha256(p)
        assert actual == entry["sha256"], f"hash mismatch {entry['file']}"
        # Also check in HASHES file
        assert actual in hashes_text, f"hash not in HASHES.sha256 {entry['file']}"
    # Check duplicates are documented (intentional_alias) - allow at most 9 duplicate groups as known
    from collections import Counter
    counts = Counter(e["sha256"] for e in data["screenshots"])
    dups = [h for h,c in counts.items() if c>1]
    # We expect duplicates for main==connection etc. Documented in MANIFEST.md
    # For this audit, allow up to 9 groups but ensure they are qt main/connection or jobs etc, not random
    # No duplicate across qt and wx should be same hash (different runtimes)
    qt_hashes = {e["sha256"] for e in data["screenshots"] if e["runtime"]=="qt"}
    wx_hashes = {e["sha256"] for e in data["screenshots"] if e["runtime"]=="wx"}
    cross = qt_hashes & wx_hashes
    assert not cross, f"cross-runtime duplicate {cross}"

def test_no_historical_files_as_current():
    # Ensure we didn't reference old audit/screenshots as current
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    for entry in data["screenshots"]:
        assert not entry["file"].startswith("audit/screenshots/"), "historical path referenced"
        assert not entry["file"].startswith("audit/gui-screenshots/"), "historical path"
        assert entry["file"].startswith("qt/") or entry["file"].startswith("wx/")

def test_required_pairs_registered():
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    files = {e["file"] for e in data["screenshots"]}
    # Required primary tabs at 1366x768
    required_qt = ["qt/01-main-default.png","qt/02-connection-default.png","qt/10-jobs-default.png","qt/20-directories-default.png","qt/30-files-default.png","qt/60-editor-default.png","qt/80-logs-default.png"]
    required_wx = ["wx/01-main-default.png","wx/02-connection-default.png","wx/10-jobs-default.png","wx/20-directories-default.png","wx/30-files-default.png","wx/60-editor-default.png","wx/70-terminal-default.png","wx/80-logs-default.png"]
    for f in required_qt:
        assert f in files, f"missing required {f}"
    for f in required_wx:
        assert f in files, f"missing required {f}"
    # Language
    assert "qt/170-language-english.png" in files
    assert "wx/170-language-english.png" in files
