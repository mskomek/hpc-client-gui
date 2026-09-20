from pathlib import Path


ROOT = Path(__file__).parents[1]
UP = (ROOT / "lab/lab-up.ps1").read_text(encoding="utf-8")
CONFIG = (ROOT / "lab/config.json").read_text(encoding="utf-8")
CONTROLLER = (ROOT / "lab/provision/controller.sh").read_text(encoding="utf-8")
COMPUTE = (ROOT / "lab/provision/compute.sh").read_text(encoding="utf-8")
LAB_TEST = (ROOT / "lab/lab-test.ps1").read_text(encoding="utf-8")


def test_local_real_provisioning_order_and_single_sources():
    assert "openssh-client sftp" not in CONTROLLER
    assert CONFIG.count('"cpus": 2') == 3
    assert "Set-VMProcessor" in UP
    assert "CPUs=$SLURM_COMPUTE_CPUS" in CONTROLLER
    assert "systemctl enable --now ssh mariadb munge nfs-server" not in CONTROLLER
    assert "systemctl restart munge" in CONTROLLER
    assert CONTROLLER.index("chown munge:munge /etc/munge/munge.key") < CONTROLLER.index("systemctl restart munge")
    assert "cat >/etc/slurm/slurm.conf <<'EOF'" in CONTROLLER
    assert "cat >/etc/slurm/slurmdbd.conf <<EOF" in CONTROLLER
    assert "StoragePass=$SLURM_DB_PASSWORD" in CONTROLLER
    assert "systemctl enable --now slurmd" not in COMPUTE
    assert "systemctl enable --now slurmdbd" in CONTROLLER
    assert "systemctl enable --now slurmctld" in CONTROLLER
    config_copy = UP.index("/etc/slurm/slurm.conf")
    munge_copy = UP.index("/etc/munge/munge.key")
    daemon_start = UP.index("systemctl enable --now munge slurmd")
    assert config_copy < daemon_start
    assert munge_copy < daemon_start
    assert "Set-VMFirmware" in UP
    assert "MicrosoftUEFICertificateAuthority" in UP
    assert "Stop-VM -Name $node.name" in UP
    assert UP.count("'  - name: hpctest'") == 0
    assert UP.count("ssh_authorized_keys:") == 1
    assert "sftp -q -b -" in LAB_TEST
    assert "sftp_content_match" in LAB_TEST
    assert "scontrol show nodes compute[01-02]" in LAB_TEST
