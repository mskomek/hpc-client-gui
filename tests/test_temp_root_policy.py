import tempfile
from pathlib import Path


def test_pytest_and_os_temp_paths_use_project_tmp(tmp_path):
    root = Path(__file__).resolve().parents[1]
    temp_root = (root / ".tmp").resolve()
    assert Path(tempfile.gettempdir()).resolve().is_relative_to(temp_root)
    assert tmp_path.resolve().is_relative_to(temp_root)
