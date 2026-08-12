from pathlib import Path
from unittest.mock import patch

from truba_gui.services.safe_download import download_atomic


class Response:
    headers = {"Content-Length": "6"}
    def __enter__(self): return self
    def __exit__(self, *args): pass
    def read(self, size):
        if hasattr(self, "done"): return b""
        self.done = True
        return b"abcdef"


def test_download_publishes_atomically(tmp_path: Path):
    target = tmp_path / "tool.exe"
    with patch("urllib.request.urlopen", return_value=Response()):
        assert download_atomic("https://example.invalid/tool.exe", target)
    assert target.read_bytes() == b"abcdef"
    assert not target.with_suffix(".exe.part").exists()


def test_download_failure_leaves_existing_target_and_cleans_partial(tmp_path: Path):
    target = tmp_path / "tool.exe"
    target.write_bytes(b"old")
    class Broken(Response):
        def read(self, size):
            if hasattr(self, "done"): raise OSError("network")
            self.done = True
            return b"new"
    with patch("urllib.request.urlopen", return_value=Broken()):
        try: download_atomic("https://example.invalid/tool.exe", target)
        except OSError: pass
    assert target.read_bytes() == b"old"
    assert not target.with_suffix(".exe.part").exists()