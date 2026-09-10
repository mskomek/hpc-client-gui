"""Wave 4 — Favorites, History, Settings and Unicode Persistence."""
from __future__ import annotations

import json
import pathlib
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


@pytest.fixture(autouse=True)
def _clear_store_cache():
    from hpc_gui.services import remote_navigation_store as rns
    rns._INSTANCES.clear()
    yield
    rns._INSTANCES.clear()


def _make_store(profile, tmp_path, monkeypatch):
    from hpc_gui.services import remote_navigation_store as rns
    monkeypatch.setattr(rns, "_state_path", lambda pid: tmp_path / f"{pid}.bin")
    return rns.RemoteNavigationStore(profile)


# ---- 1. Favorites Rendering ----

class TestFavoritesRendering:
    def test_en_favorites_label(self):
        data = json.loads((ROOT / "src/hpc_gui/i18n/en.json").read_text(encoding="utf-8"))
        assert data["dirs"]["favorites"] == "★ Favorites"
        assert "â˜…" not in data["dirs"]["favorites"]

    def test_tr_favorites_label(self):
        data = json.loads((ROOT / "src/hpc_gui/i18n/tr.json").read_text(encoding="utf-8"))
        assert data["dirs"]["favorites"] == "★ Favoriler"
        assert "â˜…" not in data["dirs"]["favorites"]

    def test_favorites_survives_roundtrip(self):
        for lang in ("en", "tr"):
            data = json.loads((ROOT / f"src/hpc_gui/i18n/{lang}.json").read_text(encoding="utf-8"))
            re = json.dumps(data, ensure_ascii=False)
            assert "★" in re
            assert "â˜…" not in re


# ---- 2. Navigation Store Favorites ----

class TestFavorites:
    def test_survive_reload(self, tmp_path, monkeypatch):
        s = _make_store("a", tmp_path, monkeypatch)
        for p in ("/scratch/Çalışmalar", "/scratch/日本語", "/scratch/Türkçe_日本語", "/work/★"):
            s.toggle_favorite(p, kind="directory")
        assert len(s.favorites()) == 4
        s._save()
        s2 = _make_store("a", tmp_path, monkeypatch)
        assert len(s2.favorites()) == 4
        assert {f["path"] for f in s2.favorites()} == {"/scratch/Çalışmalar", "/scratch/日本語", "/scratch/Türkçe_日本語", "/work/★"}

    def test_duplicate_ignored(self, tmp_path, monkeypatch):
        """toggle_favorite toggles: add then remove."""
        s = _make_store("b", tmp_path, monkeypatch)
        s.toggle_favorite("/work/test", kind="directory")
        assert len(s.favorites()) == 1
        s.toggle_favorite("/work/test", kind="directory")
        # toggle removes existing
        assert len(s.favorites()) == 0

    def test_toggle_removes(self, tmp_path, monkeypatch):
        s = _make_store("c", tmp_path, monkeypatch)
        s.toggle_favorite("/work/test", kind="directory")
        assert len(s.favorites()) == 1
        s.toggle_favorite("/work/test", kind="directory")
        assert len(s.favorites()) == 0


# ---- 3. History ----

class TestHistory:
    def test_record_visit(self, tmp_path, monkeypatch):
        s = _make_store("h1", tmp_path, monkeypatch)
        for p in ("/work/dir1", "/work/dir2", "/work/dir3"):
            s.record_visit(p)
        h = s.history()
        assert len(h) == 3
        assert [e["path"] for e in h] == ["/work/dir3", "/work/dir2", "/work/dir1"]

    def test_deduplication(self, tmp_path, monkeypatch):
        s = _make_store("h2", tmp_path, monkeypatch)
        s.record_visit("/work/dir1")
        s.record_visit("/work/dir2")
        s.record_visit("/work/dir1")
        h = s.history()
        assert len(h) == 2
        assert h[0]["path"] == "/work/dir1"

    def test_max_cap(self, tmp_path, monkeypatch):
        from hpc_gui.services.remote_navigation_store import MAX_HISTORY
        s = _make_store("h3", tmp_path, monkeypatch)
        for i in range(MAX_HISTORY + 10):
            s.record_visit(f"/work/dir{i}")
        assert len(s.history()) <= MAX_HISTORY

    def test_clear(self, tmp_path, monkeypatch):
        s = _make_store("h4", tmp_path, monkeypatch)
        s.record_visit("/work/dir1")
        s.record_visit("/work/dir2")
        assert len(s.history()) == 2
        s.clear_history()
        assert len(s.history()) == 0

    def test_unicode_paths(self, tmp_path, monkeypatch):
        s = _make_store("h5", tmp_path, monkeypatch)
        for p in ("/scratch/Çalışmalar", "/scratch/日本語", "/scratch/Türkçe_日本語"):
            s.record_visit(p)
        assert [h["path"] for h in s.history()] == ["/scratch/Türkçe_日本語", "/scratch/日本語", "/scratch/Çalışmalar"]


# ---- 4. Serialization ----

class TestSerialization:
    def test_unicode_roundtrip(self, tmp_path, monkeypatch):
        s = _make_store("s1", tmp_path, monkeypatch)
        for p in ("/scratch/Çalışmalar", "/scratch/日本語", "/scratch/Türkçe_日本語"):
            s.toggle_favorite(p, kind="directory")
        s._save()
        s2 = _make_store("s1", tmp_path, monkeypatch)
        assert {f["path"] for f in s2.favorites()} == {"/scratch/Çalışmalar", "/scratch/日本語", "/scratch/Türkçe_日本語"}

    def test_atomic_write(self, tmp_path, monkeypatch):
        s = _make_store("s2", tmp_path, monkeypatch)
        s.toggle_favorite("/work/test", kind="directory")
        s._save()
        state_files = list(tmp_path.glob("*.bin"))
        assert len(state_files) == 1
        assert len(list(tmp_path.glob("*.tmp"))) == 0


# ---- 5. Profile Isolation ----

class TestProfileIsolation:
    def test_separate_favorites(self, tmp_path, monkeypatch):
        s1 = _make_store("p1", tmp_path, monkeypatch)
        s2 = _make_store("p2", tmp_path, monkeypatch)
        s1.toggle_favorite("/work/profile1", kind="directory")
        s2.toggle_favorite("/work/profile2", kind="directory")
        s1._save()
        s2._save()
        r1 = _make_store("p1", tmp_path, monkeypatch)
        r2 = _make_store("p2", tmp_path, monkeypatch)
        assert r1.favorites()[0]["path"] == "/work/profile1"
        assert r2.favorites()[0]["path"] == "/work/profile2"


# ---- 6. Encryption ----

class TestEncryption:
    def test_raw_not_readable(self, tmp_path, monkeypatch):
        s = _make_store("e1", tmp_path, monkeypatch)
        s.toggle_favorite("/secret/日本語", kind="directory")
        s._save()
        raw = (tmp_path / "e1.bin").read_bytes()
        assert b"/secret/" not in raw
        assert "日本語".encode("utf-8") not in raw

    def test_tampered_empty(self, tmp_path, monkeypatch):
        s = _make_store("e2", tmp_path, monkeypatch)
        s.toggle_favorite("/work/test", kind="directory")
        s._save()
        (tmp_path / "e2.bin").write_bytes(b"tampered" * 100)
        s2 = _make_store("e2", tmp_path, monkeypatch)
        assert len(s2.favorites()) == 0
        assert len(s2.history()) == 0


# ---- 7. Delete Profile ----

class TestDelete:
    def test_removes_file(self, tmp_path, monkeypatch):
        from hpc_gui.services import remote_navigation_store as rns
        monkeypatch.setattr(rns, "_state_path", lambda pid: tmp_path / f"{pid}.bin")
        s = rns.RemoteNavigationStore("d1")
        s.toggle_favorite("/work/test", kind="directory")
        s._save()
        state_files = list(tmp_path.glob("*.bin"))
        assert len(state_files) == 1
        rns.delete_profile_navigation("d1")
        assert not state_files[0].exists()


# ---- 8. Integration ----

class TestIntegration:
    def test_full_workflow(self, tmp_path, monkeypatch):
        s = _make_store("f1", tmp_path, monkeypatch)
        favs = [("/scratch/Çalışmalar", "directory"), ("/scratch/日本語", "directory"), ("/scratch/Türkçe_日本語/file.txt", "file")]
        for p, k in favs:
            s.toggle_favorite(p, kind=k)
        assert len(s.favorites()) == 3
        for p in ("/scratch/Çalışmalar", "/scratch/日本語", "/scratch/Türkçe_日本語"):
            s.record_visit(p)
        assert len(s.history()) == 3
        s._save()
        s2 = _make_store("f1", tmp_path, monkeypatch)
        assert len(s2.favorites()) == 3
        assert len(s2.history()) == 3
        s2.toggle_favorite("/scratch/Çalışmalar", kind="directory")
        assert len(s2.favorites()) == 2
        s2._save()
        s3 = _make_store("f1", tmp_path, monkeypatch)
        assert len(s3.favorites()) == 2
        assert "/scratch/Çalışmalar" not in {f["path"] for f in s3.favorites()}
