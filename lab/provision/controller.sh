#!/usr/bin/env bash
set -Eeuo pipefail
trap 'rc=$?; echo "controller provisioning failed at line $LINENO: $BASH_COMMAND (exit $rc)" >&2; exit $rc' ERR


: "${SLURM_COMPUTE_CPUS:?set SLURM_COMPUTE_CPUS in the provisioning environment}"
: "${SLURM_COMPUTE_REAL_MEMORY:?set SLURM_COMPUTE_REAL_MEMORY in the provisioning environment}"
: "${SLURM_COMPUTE_NODES:?set SLURM_COMPUTE_NODES in the provisioning environment}"
: "${SLURM_CONTROLLER_HOST:?set SLURM_CONTROLLER_HOST in the provisioning environment}"
LAB_NFS_CIDR="${LAB_NFS_CIDR:-192.168.250.0/24}"
SLURM_CLUSTER_NAME="${SLURM_CLUSTER_NAME:-local-real}"


export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openssh-server openssh-client munge slurm-wlm slurmctld slurmdbd mariadb-server nfs-kernel-server openssl


id hpctest >/dev/null 2>&1 || useradd --create-home --shell /bin/bash hpctest
install -d -m 0755 /srv/hpc/{home,scratch,project}
install -d -m 0700 -o hpctest -g hpctest /srv/hpc/home/hpctest /srv/hpc/scratch/hpctest /srv/hpc/project/hpctest
install -d -m 0700 -o hpctest -g hpctest /srv/hpc/home/hpctest/.ssh


key_tmp=$(mktemp)
{
  for key_file in /home/hpctest/.ssh/authorized_keys /srv/hpc/home/hpctest/.ssh/authorized_keys; do
    if [ -s "$key_file" ]; then
      cat "$key_file"
    fi
  done
} | awk 'NF && !seen[$0]++' >"$key_tmp"
if [ ! -s "$key_tmp" ]; then
  echo 'No hpctest authorized_keys found during controller provisioning.' >&2
  rm -f "$key_tmp"
  exit 1
fi
install -o hpctest -g hpctest -m 0600 "$key_tmp" /srv/hpc/home/hpctest/.ssh/authorized_keys
rm -f "$key_tmp"
chown -R hpctest:hpctest /srv/hpc/home/hpctest /srv/hpc/scratch/hpctest /srv/hpc/project/hpctest
chmod 0700 /srv/hpc/home/hpctest/.ssh
chmod 0600 /srv/hpc/home/hpctest/.ssh/authorized_keys


install -d -m 0700 -o hpctest -g hpctest /home/hpctest
sed -i '\#^/srv/hpc/home/hpctest /home/hpctest none bind #d' /etc/fstab
printf '/srv/hpc/home/hpctest /home/hpctest none bind 0 0\n' >>/etc/fstab
if mountpoint -q /home/hpctest; then
  [ "$(stat -c '%d:%i' /home/hpctest)" = "$(stat -c '%d:%i' /srv/hpc/home/hpctest)" ] || {
    echo '/home/hpctest is mounted but is not the expected shared-home bind mount.' >&2
    exit 1
  }
else
  mount --bind /srv/hpc/home/hpctest /home/hpctest
fi


printf '/srv/hpc/home  %s(rw,sync,no_subtree_check,no_root_squash)\n/srv/hpc/scratch %s(rw,sync,no_subtree_check,no_root_squash)\n/srv/hpc/project %s(rw,sync,no_subtree_check,no_root_squash)\n' \
  "$LAB_NFS_CIDR" "$LAB_NFS_CIDR" "$LAB_NFS_CIDR" >/etc/exports
systemctl enable --now ssh mariadb nfs-server
exportfs -rav


if [ ! -s /etc/munge/munge.key ]; then
  install -d -m 0700 -o munge -g munge /etc/munge
  runuser -u munge -- /usr/sbin/mungekey --create
fi
chown munge:munge /etc/munge/munge.key
chmod 0400 /etc/munge/munge.key
systemctl enable munge >/dev/null
systemctl restart munge
munge -n | unmunge >/dev/null


install -d /etc/slurm
db_password_file=/etc/slurm/local-real-db-password
if [ ! -s "$db_password_file" ]; then
  umask 077
  openssl rand -hex 32 >"$db_password_file"
fi
chown root:root "$db_password_file"
chmod 0600 "$db_password_file"
SLURM_DB_PASSWORD=$(cat "$db_password_file")


cat >/etc/slurm/slurm.conf <<EOF2
ClusterName=$SLURM_CLUSTER_NAME
SlurmctldHost=$SLURM_CONTROLLER_HOST
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
AccountingStorageHost=$SLURM_CONTROLLER_HOST
NodeName=$SLURM_COMPUTE_NODES CPUs=$SLURM_COMPUTE_CPUS RealMemory=$SLURM_COMPUTE_REAL_MEMORY State=UNKNOWN
PartitionName=debug Nodes=$SLURM_COMPUTE_NODES Default=YES MaxTime=INFINITE State=UP
EOF2
install -d -o slurm -g slurm /var/lib/slurm/slurmctld /var/lib/slurm/slurmd /var/log/slurm


cat >/etc/slurm/slurmdbd.conf <<EOF2
AuthType=auth/munge
DbdHost=$SLURM_CONTROLLER_HOST
SlurmUser=slurm
StorageType=accounting_storage/mysql
StorageHost=localhost
StorageUser=slurm
StorageLoc=slurm_acct_db
StoragePass=$SLURM_DB_PASSWORD
LogFile=/var/log/slurm/slurmdbd.log
EOF2
chown slurm:slurm /etc/slurm/slurmdbd.conf
chmod 600 /etc/slurm/slurmdbd.conf


mysql <<SQL
CREATE DATABASE IF NOT EXISTS slurm_acct_db;
CREATE USER IF NOT EXISTS 'slurm'@'localhost' IDENTIFIED BY '$SLURM_DB_PASSWORD';
ALTER USER 'slurm'@'localhost' IDENTIFIED BY '$SLURM_DB_PASSWORD';
GRANT ALL ON slurm_acct_db.* TO 'slurm'@'localhost';
FLUSH PRIVILEGES;
SQL
unset SLURM_DB_PASSWORD
chown -R slurm:slurm /var/log/slurm /var/lib/slurm


systemctl enable slurmdbd >/dev/null
systemctl restart slurmdbd
for _ in $(seq 1 30); do
  if systemctl is-active --quiet slurmdbd && sacctmgr -nP show cluster >/dev/null 2>&1; then
    break
  fi
  sleep 1
done
systemctl is-active --quiet slurmdbd
sacctmgr -nP show cluster >/dev/null


cluster_exists() {
  sacctmgr -nP show cluster format=Cluster |
    awk -F'|' -v cluster="$SLURM_CLUSTER_NAME" '$1 == cluster { found=1 } END { exit(found ? 0 : 1) }'
}
account_exists() {
  sacctmgr -nP show assoc where Cluster="$SLURM_CLUSTER_NAME" Account=local format=Cluster,Account |
    awk -F'|' -v cluster="$SLURM_CLUSTER_NAME" '$1 == cluster && $2 == "local" { found=1 } END { exit(found ? 0 : 1) }'
}
user_assoc_exists() {
  sacctmgr -nP show assoc where Cluster="$SLURM_CLUSTER_NAME" Account=local User=hpctest format=Cluster,Account,User |
    awk -F'|' -v cluster="$SLURM_CLUSTER_NAME" '$1 == cluster && $2 == "local" && $3 == "hpctest" { found=1 } END { exit(found ? 0 : 1) }'
}
ensure_postcondition() {
  local label="$1"
  local check_fn="$2"
  shift 2
  if "$check_fn"; then
    return 0
  fi
  local output rc
  set +e
  output=$("$@" 2>&1)
  rc=$?
  set -e
  if "$check_fn"; then
    [ -z "$output" ] || printf '%s\n' "$output"
    return 0
  fi
  printf '%s provisioning failed (exit %s).\n%s\n' "$label" "$rc" "$output" >&2
  return "$rc"
}


ensure_postcondition "Slurm cluster association" cluster_exists   sacctmgr -i add cluster "$SLURM_CLUSTER_NAME"
ensure_postcondition "Slurm account association" account_exists   sacctmgr -i add account local Cluster="$SLURM_CLUSTER_NAME" Description=LOCAL_REAL Organization=local
ensure_postcondition "Slurm user association" user_assoc_exists   sacctmgr -i add user hpctest Account=local Cluster="$SLURM_CLUSTER_NAME" DefaultAccount=local


sacctmgr -i modify user where Name=hpctest Cluster="$SLURM_CLUSTER_NAME" Account=local set DefaultAccount=local >/dev/null


systemctl enable slurmctld >/dev/null
systemctl restart slurmctld
for _ in $(seq 1 30); do
  if systemctl is-active --quiet slurmctld && scontrol ping 2>/dev/null | grep -q 'UP'; then
    break
  fi
  sleep 1
done
systemctl is-active --quiet slurmctld
scontrol ping