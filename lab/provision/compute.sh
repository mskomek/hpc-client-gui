#!/usr/bin/env bash
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openssh-server openssh-client munge slurmd nfs-common
id hpctest >/dev/null 2>&1 || useradd --create-home --shell /bin/bash hpctest
install -d -o hpctest -g hpctest /home/hpctest
grep -q '^login-control01 ' /etc/hosts || cat >>/etc/hosts <<'EOF'
192.168.250.11 login-control01
192.168.250.12 compute01
192.168.250.13 compute02
EOF
install -d /home /scratch /project
mountpoint -q /home || mount -t nfs4 login-control01:/srv/hpc/home /home
mountpoint -q /scratch || mount -t nfs4 login-control01:/srv/hpc/scratch /scratch
mountpoint -q /project || mount -t nfs4 login-control01:/srv/hpc/project /project
grep -q 'login-control01:/srv/hpc/home' /etc/fstab || cat >>/etc/fstab <<'EOF'
login-control01:/srv/hpc/home /home nfs4 _netdev,auto 0 0
login-control01:/srv/hpc/scratch /scratch nfs4 _netdev,auto 0 0
login-control01:/srv/hpc/project /project nfs4 _netdev,auto 0 0
EOF
systemctl enable --now ssh
install -d /var/lib/slurm/slurmd
chown -R slurm:slurm /var/lib/slurm
