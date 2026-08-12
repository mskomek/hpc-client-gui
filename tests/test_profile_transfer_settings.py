from truba_gui.config.models import SSHConfig
from truba_gui.config.storage import coerce_profile_ssh_timeout, coerce_profile_transfer_parallelism


def test_profile_transfer_settings_are_bounded() -> None:
    assert coerce_profile_transfer_parallelism(99) == 10
    assert coerce_profile_transfer_parallelism(0) == 1
    assert coerce_profile_ssh_timeout(900) == 600
    assert coerce_profile_ssh_timeout(0) is None
    assert coerce_profile_ssh_timeout("bad") is None


def test_ssh_config_keeps_profile_overrides() -> None:
    cfg = SSHConfig(transfer_parallelism=4, ssh_timeout=12.5)
    assert cfg.transfer_parallelism == 4
    assert cfg.ssh_timeout == 12.5