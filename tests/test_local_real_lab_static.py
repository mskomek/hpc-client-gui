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
    assert "SLURM_COMPUTE_CPUS=$($computeCpus[0])" in UP
    assert "cat >/etc/slurm/slurm.conf <<EOF" in CONTROLLER
    assert "cat >/etc/slurm/slurm.conf <<'EOF'" not in CONTROLLER
    assert "Resize-VHD -Path $disk -SizeBytes $diskBytes" in UP
    assert "Get-VHD -Path $disk" in UP
    assert "systemctl enable --now ssh mariadb munge nfs-server" not in CONTROLLER
    assert "systemctl restart munge" in CONTROLLER
    assert "create-munge-key" not in CONTROLLER
    assert "runuser -u munge -- /usr/sbin/mungekey --create" in CONTROLLER
    assert CONTROLLER.index("chown munge:munge /etc/munge/munge.key") < CONTROLLER.index("systemctl restart munge")
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
    assert "munge -n | unmunge'" in LAB_TEST
    assert "grep -q STATUS:0" not in LAB_TEST
    assert "srun --nodes=2 --ntasks=2 --ntasks-per-node=1" in LAB_TEST
    assert "test \"$(wc -l < .local-real-job/result)\" -eq 2" in LAB_TEST
    assert "^compute01 /srv/hpc/home/hpctest/.local-real-job$" in LAB_TEST
    assert "^compute02 /srv/hpc/home/hpctest/.local-real-job$" in LAB_TEST
    assert "canonical_paths_same" in LAB_TEST
    assert "identity_same" in LAB_TEST
    assert "shared_home_job" in LAB_TEST
    assert "ssh_key_login" in LAB_TEST
    assert "ssh_key_login_ok" in LAB_TEST


def test_local_real_shared_identity_and_mounts():
    assert "usermod -d /srv/hpc/home/hpctest hpctest" in CONTROLLER
    assert "usermod -d /srv/hpc/home/hpctest hpctest" in COMPUTE
    assert "login-control01:/srv/hpc/home /srv/hpc/home" in COMPUTE
    assert "login-control01:/srv/hpc/scratch /srv/hpc/scratch" in COMPUTE
    assert "login-control01:/srv/hpc/project /srv/hpc/project" in COMPUTE
    assert "login-control01:/srv/hpc/home /home" not in COMPUTE
    assert "sed -i '\\#^login-control01:/srv/hpc/.* nfs4 #d' /etc/fstab" in COMPUTE
    assert "HPCTEST_UID" in COMPUTE and "SLURM_UID" in COMPUTE


def test_local_real_fault_recovery_is_role_aware_and_resettable():
    fault = (ROOT / "lab/lab-fault.ps1").read_text(encoding="utf-8")
    reset = (ROOT / "lab/lab-reset.ps1").read_text(encoding="utf-8")
    assert "systemd-run --unit=$unit --on-active=${RecoveryDelaySeconds}s /bin/systemctl start ssh" in fault
    assert "Invoke-LabSsh $controller.ip 'sudo systemctl stop ssh'" not in fault
    assert "sudo systemctl start ssh munge slurmdbd slurmctld" in fault
    assert "sudo systemctl start ssh munge slurmd" in fault
    assert "NodeName=$Node State=RESUME" in fault
    assert "NodeName=login-control01" not in fault
    assert "Start-VM -Name $node.name" in reset
    assert "Test-NetConnection $node.ip -Port 22" in reset
    assert "$controllerServices = 'sudo systemctl start ssh munge mariadb nfs-server slurmdbd slurmctld'" in reset
    assert "sudo systemctl start ssh munge slurmd" in reset
