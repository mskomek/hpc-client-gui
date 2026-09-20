#!/usr/bin/env bash
set -euo pipefail
: "${SLURM_DB_PASSWORD:?set SLURM_DB_PASSWORD in the provisioning environment}"
: "${SLURM_COMPUTE_CPUS:?set SLURM_COMPUTE_CPUS in the provisioning environment}"

export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openssh-server openssh-client munge slurm-wlm slurmctld slurmdbd mariadb-server nfs-kernel-server

id hpctest >/dev/null 2>&1 || useradd --create-home --shell /bin/bash hpctest
install -d -m 0755 /srv/hpc/{home,scratch,project}
install -d -m 0700 -o hpctest -g hpctest /srv/hpc/home/hpctest
chown -R hpctest:hpctest /srv/hpc/home/hpctest
usermod -d /srv/hpc/home/hpctest hpctest
printf '/srv/hpc/home  *(rw,sync,no_subtree_check,no_root_squash)\n/srv/hpc/scratch *(rw,sync,no_subtree_check,no_root_squash)\n/srv/hpc/project *(rw,sync,no_subtree_check,no_root_squash)\n' >/etc/exports
exportfs -rav
systemctl enable --now ssh mariadb nfs-server

if [ ! -s /etc/munge/munge.key ]; then
  create-munge-key || /usr/sbin/mungekey
  chown munge:munge /etc/munge/munge.key
  chmod 0400 /etc/munge/munge.key
fi
systemctl restart munge

cat >/etc/slurm/slurm.conf <<'EOF'
ClusterName=local-real
SlurmctldHost=login-control01
SlurmUser=slurm
AuthType=auth/munge
StateSaveLocation=/var/lib/slurm/slurmctld
SlurmdSpoolDir=/var/lib/slurm/slurmd
SlurmctldPort=6817
SlurmdPort=6818
ProctrackType=proctrack/linuxproc
TaskPlugin=task/none
SelectType=select/cons_tres
SelectTypeParameters=CR_Core
SchedulerType=sched/backfill
AccountingStorageType=accounting_storage/slurmdbd
AccountingStorageHost=login-control01
NodeName=compute[01-02] CPUs=$SLURM_COMPUTE_CPUS RealMemory=1800 State=UNKNOWN
PartitionName=debug Nodes=compute[01-02] Default=YES MaxTime=INFINITE State=UP
EOF
mkdir -p /var/lib/slurm/slurmctld /var/lib/slurm/slurmd
chown -R slurm:slurm /var/lib/slurm

cat >/etc/slurm/slurmdbd.conf <<EOF
AuthType=auth/munge
DbdHost=login-control01
SlurmUser=slurm
StorageType=accounting_storage/mysql
StorageHost=localhost
StorageUser=slurm
StorageLoc=slurm_acct_db
StoragePass=$SLURM_DB_PASSWORD
LogFile=/var/log/slurm/slurmdbd.log
PidFile=/run/slurmdbd.pid
EOF
chmod 600 /etc/slurm/slurmdbd.conf
mysql <<SQL
CREATE DATABASE IF NOT EXISTS slurm_acct_db;
CREATE USER IF NOT EXISTS 'slurm'@'localhost' IDENTIFIED BY '$SLURM_DB_PASSWORD';
ALTER USER 'slurm'@'localhost' IDENTIFIED BY '$SLURM_DB_PASSWORD';
GRANT ALL ON slurm_acct_db.* TO 'slurm'@'localhost';
FLUSH PRIVILEGES;
SQL
unset SLURM_DB_PASSWORD
install -d -o slurm -g slurm /var/log/slurm
systemctl enable --now slurmdbd
systemctl enable --now slurmctld
scontrol update NodeName=compute01 State=RESUME || true
scontrol update NodeName=compute02 State=RESUME || true
