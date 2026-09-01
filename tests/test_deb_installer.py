from pathlib import Path
import os

import pytest

from hpc_gui.services.deb_installer import (
    build_packagekit_command,
    probe_packagekit,
    stage_verified_deb,
)


def test_packagekit_probe_distinguishes_local_install_support():
    class Result:
        returncode = 1
        stdout = ""
        stderr = "A filename to install is required"

    assert probe_packagekit(lambda *args, **kwargs: Result()).local_install

    class Unsupported:
        returncode = 1
        stdout = ""
        stderr = "Command 'install-local' is not supported"

    assert not probe_packagekit(lambda *args, **kwargs: Unsupported()).local_install


def test_stage_is_private_and_rejects_symlink(tmp_path: Path):
    source = tmp_path / "update.deb"
    source.write_bytes(b"deb")
    staged = stage_verified_deb(source, tmp_path / "updates")
    assert staged.read_bytes() == b"deb"
    if os.name == "posix":
        assert staged.stat().st_mode & 0o777 == 0o600
    assert build_packagekit_command(staged) == ["pkcon", "install-local", str(staged.resolve())]

    link = tmp_path / "link.deb"
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows test host")
    with pytest.raises(ValueError):
        build_packagekit_command(link)
