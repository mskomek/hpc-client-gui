from pathlib import Path


ROOT = Path(__file__).parents[1]
UP = (ROOT / "lab/lab-up.ps1").read_text(encoding="utf-8-sig")
COMMON = (ROOT / "lab/lab-common.ps1").read_text(encoding="utf-8-sig")
CONFIG = (ROOT / "lab/config.json").read_text(encoding="utf-8")
CONTROLLER = (ROOT / "lab/provision/controller.sh").read_text(encoding="utf-8")
COMPUTE = (ROOT / "lab/provision/compute.sh").read_text(encoding="utf-8")
LAB_TEST = (ROOT / "lab/lab-test.ps1").read_text(encoding="utf-8-sig")
STATUS = (ROOT / "lab/lab-status.ps1").read_text(encoding="utf-8-sig")
RESET = (ROOT / "lab/lab-reset.ps1").read_text(encoding="utf-8-sig")
FAULT = (ROOT / "lab/lab-fault.ps1").read_text(encoding="utf-8-sig")


def test_local_real_provisioning_order_and_single_sources():
    assert "openssh-client sftp" not in CONTROLLER
    assert CONFIG.count('"cpus": 2') == 3
    assert "Set-VMProcessor" in UP
    assert "CPUs=$SLURM_COMPUTE_CPUS" in CONTROLLER
    assert "RealMemory=$SLURM_COMPUTE_REAL_MEMORY" in CONTROLLER
    assert "SLURM_COMPUTE_CPUS=$($computeCpus[0])" in UP
    assert "SLURM_COMPUTE_REAL_MEMORY=$slurmRealMemory" in UP
    assert "SLURM_COMPUTE_NODES=$computeNodeList" in UP
    assert "SLURM_CONTROLLER_HOST=$($controller.name)" in UP
    assert "cat >/etc/slurm/slurm.conf <<EOF" in CONTROLLER
    assert "cat >/etc/slurm/slurm.conf <<'EOF'" not in CONTROLLER
    assert "Resize-VHD -Path $disk -SizeBytes $diskBytes" in UP
    assert "Get-VHD -Path $disk" in UP
    assert "Get-FileHash -Algorithm SHA256 $image" in UP
    assert "$baseVhdx.source.sha256" in UP
    assert "seed.sha256" in UP
    assert "Cloud-init seed drift detected" in UP
    assert "systemctl enable --now ssh mariadb nfs-server" in CONTROLLER
    assert CONTROLLER.index("systemctl enable --now ssh mariadb nfs-server") < CONTROLLER.index("exportfs -rav")
    assert "systemctl restart munge" in CONTROLLER
    assert "create-munge-key" not in CONTROLLER
    assert "runuser -u munge -- /usr/sbin/mungekey --create" in CONTROLLER
    assert "chown slurm:slurm /etc/slurm/slurmdbd.conf" in CONTROLLER
    assert "systemctl restart slurmdbd" in CONTROLLER
    assert "systemctl restart slurmctld" in CONTROLLER
    assert "sacctmgr -i add cluster" in CONTROLLER
    assert "sacctmgr -i add account local Cluster=" in CONTROLLER
    assert "sacctmgr -i add user hpctest" in CONTROLLER
    assert "systemctl enable --now slurmd" not in COMPUTE
    assert "sudo systemctl restart munge" in UP
    assert "sudo systemctl restart slurmd" in UP
    assert "Slurm compute nodes did not become IDLE" in UP
    assert "Set-VMFirmware" in UP
    assert "MicrosoftUEFICertificateAuthority" in UP
    assert "Set-VMMemory" in UP
    assert "-DynamicMemoryEnabled $false" in UP
    assert "Connect-VMNetworkAdapter" in UP
    assert "SwitchName -eq [string]$Config.switch" in UP
    assert "StaticMacAddress" in UP
    assert "macaddress:" in UP
    assert "cloud-init status --wait" in UP
    assert "Remote provisioning failed" in UP


def test_local_real_shared_identity_and_mounts():
    assert "usermod -d /srv/hpc/home/hpctest hpctest" not in CONTROLLER
    assert "usermod -d /srv/hpc/home/hpctest hpctest" not in COMPUTE
    assert "mount --bind /srv/hpc/home/hpctest /home/hpctest" in CONTROLLER
    assert "mount --bind /srv/hpc/home/hpctest /home/hpctest" in COMPUTE
    assert "/srv/hpc/home/hpctest /home/hpctest none bind" in CONTROLLER
    assert "/srv/hpc/home/hpctest /home/hpctest none bind" in COMPUTE
    assert "hpctest identity mismatch" in COMPUTE
    assert "usermod -u \"$HPCTEST_UID\" hpctest" not in COMPUTE
    assert "LAB_CONTROLLER_HOST" in COMPUTE
    assert 'login-control01:/srv/hpc/home' not in COMPUTE
    assert "HPCTEST_UID" in COMPUTE and "SLURM_UID" in COMPUTE
    assert "/srv/hpc/scratch/hpctest" in CONTROLLER
    assert "/srv/hpc/project/hpctest" in CONTROLLER
    assert "/srv/hpc/scratch/hpctest" in COMPUTE
    assert "/srv/hpc/project/hpctest" in COMPUTE
    assert "path_template='/srv/hpc/project/{user}'" in UP
    assert 'test "$HOME" = /home/hpctest' in LAB_TEST
    assert 'mountpoint -q "$HOME"' in LAB_TEST
    assert "-ef /srv/hpc/home/hpctest/.ssh/authorized_keys" in LAB_TEST


def test_local_real_runtime_harness_is_deterministic():
    assert "Get-ControllerNode" in COMMON
    assert "Get-ComputeNodes" in COMMON
    assert "ConnectTimeout=5" in COMMON
    assert "ServerAliveInterval=5" in COMMON
    assert "ToBase64String($commandBytes)" in COMMON
    assert "base64 -d | bash -s" in COMMON
    assert "([string]$stdout).TrimEnd()" in COMMON
    assert "id -u hpctest; id -g hpctest; id -u slurm; id -g slurm" in UP
    assert "ssh_pty_ok" in LAB_TEST
    assert "$taskCount = $computeNodes.Count" in LAB_TEST
    assert "sftp @sftpOptions -q -b $sftpBatch" in LAB_TEST
    assert "sftp_stderr" in LAB_TEST
    assert "srun --nodes={0} --ntasks={0} --ntasks-per-node=1" in LAB_TEST
    assert "srun_nodes_ok" in LAB_TEST
    assert "sinfo_nodes_ok" in LAB_TEST
    assert "shared_home_job_ok" in LAB_TEST
    assert "canonical_paths_same" in LAB_TEST
    assert "identity_same" in LAB_TEST
    assert "storage_same" in LAB_TEST
    assert "LOCAL_REAL_STORAGE" in LAB_TEST
    assert "if (-not $pass) { exit 3 }" in LAB_TEST
    assert "exit 0" in LAB_TEST
    assert "slurm=[pscustomobject]" in STATUS
    assert "if (-not $statusOk) { exit 3 }" in STATUS


def test_local_real_fault_recovery_is_role_aware_and_resettable():
    assert "systemd-run --quiet --unit=$unit --on-active=${RecoveryDelaySeconds}s /bin/systemctl start ssh" in FAULT
    assert "Get-ControllerNode" in FAULT
    assert "Get-ComputeNodes" in FAULT
    assert "Test-NetConnection $target.ip -Port $Config.ssh.port" in FAULT
    assert "Restart-VM -Name $target.name -Force" in FAULT
    assert "NodeName=$Node State=RESUME" in FAULT
    assert "Start-VM -Name $node.name" in RESET
    assert "Test-NetConnection $node.ip -Port $Config.ssh.port" in RESET
    assert "Restart-VM -Name $node.name -Force" in RESET
    assert "systemctl restart munge mariadb nfs-server slurmdbd slurmctld ssh" in RESET
    assert "systemctl restart munge slurmd ssh" in RESET
