#!/usr/bin/env bash
set -Eeuo pipefail
trap 'rc=$?; echo "compute provisioning failed at line $LINENO: $BASH_COMMAND (exit $rc)" >&2; exit $rc' ERR


: "${HPCTEST_UID:?set HPCTEST_UID in the provisioning environment}"
: "${HPCTEST_GID:?set HPCTEST_GID in the provisioning environment}"
: "${SLURM_UID:?set SLURM_UID in the provisioning environment}"
: "${SLURM_GID:?set SLURM_GID in the provisioning environment}"
: "${LAB_CONTROLLER_HOST:?set LAB_CONTROLLER_HOST in the provisioning environment}"


export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openssh-server openssh-client munge slurmd nfs-common
id hpctest >/dev/null 2>&1 || useradd --create-home --shell /bin/bash hpctest


# hpctest owns the active provisioning SSH session, so never usermod it in-place.
# Fresh lab VMs are expected to receive the same cloud-init UID/GID; fail clearly
# instead of mutating a logged-in account.
if [ "$(id -u hpctest)" != "$HPCTEST_UID" ] || [ "$(id -g hpctest)" != "$HPCTEST_GID" ]; then
  echo "hpctest identity mismatch: local=$(id -u hpctest):$(id -g hpctest) expected=$HPCTEST_UID:$HPCTEST_GID" >&2
  exit 1
fi


# slurmd must not be running while the package-created slurm identity is aligned.
systemctl stop slurmd >/dev/null 2>&1 || true
align_slurm_identity() {
  local current_uid current_gid owner
  current_uid=$(id -u slurm)
  current_gid=$(id -g slurm)
  if [ "$current_gid" != "$SLURM_GID" ]; then
    owner=$(getent group "$SLURM_GID" | cut -d: -f1 || true)
    [ -z "$owner" ] || [ "$owner" = slurm ] || { echo "GID $SLURM_GID belongs to $owner" >&2; exit 1; }
    groupmod -g "$SLURM_GID" slurm
    usermod -g "$SLURM_GID" slurm
  fi
  if [ "$current_uid" != "$SLURM_UID" ]; then
    owner=$(getent passwd "$SLURM_UID" | cut -d: -f1 || true)
    [ -z "$owner" ] || [ "$owner" = slurm ] || { echo "UID $SLURM_UID belongs to $owner" >&2; exit 1; }
    usermod -u "$SLURM_UID" slurm
  fi
}
align_slurm_identity


getent hosts "$LAB_CONTROLLER_HOST" >/dev/null || { echo "Controller hostname is not resolvable: $LAB_CONTROLLER_HOST" >&2; exit 1; }


install -d /srv/hpc/home /srv/hpc/scratch /srv/hpc/project
ensure_nfs_mount() {
  local target="$1"
  local export_path="$2"
  local expected="$LAB_CONTROLLER_HOST:$export_path"
  if mountpoint -q "$target"; then
    local actual
    actual=$(findmnt -rn -o SOURCE --target "$target" || true)
    [ "$actual" = "$expected" ] || { echo "Unexpected NFS source for $target: $actual (expected $expected)" >&2; exit 1; }
  else
    mount -t nfs4 "$expected" "$target"
  fi
}
ensure_nfs_mount /srv/hpc/home /srv/hpc/home
ensure_nfs_mount /srv/hpc/scratch /srv/hpc/scratch
ensure_nfs_mount /srv/hpc/project /srv/hpc/project
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
  echo 'No hpctest authorized_keys found during compute provisioning.' >&2
  rm -f "$key_tmp"
  exit 1
fi
install -o hpctest -g hpctest -m 0600 "$key_tmp" /srv/hpc/home/hpctest/.ssh/authorized_keys
rm -f "$key_tmp"
chown -R hpctest:hpctest /srv/hpc/home/hpctest /srv/hpc/scratch/hpctest /srv/hpc/project/hpctest
chmod 0700 /srv/hpc/home/hpctest/.ssh
chmod 0600 /srv/hpc/home/hpctest/.ssh/authorized_keys


# Keep HOME=/home/hpctest while backing it with the shared NFS home tree.
install -d -m 0700 -o hpctest -g hpctest /home/hpctest
sed -i '\#^/srv/hpc/home/hpctest /home/hpctest none bind #d' /etc/fstab
sed -i "\#^$LAB_CONTROLLER_HOST:/srv/hpc/.* nfs4 #d" /etc/fstab
cat >>/etc/fstab <<EOF2
$LAB_CONTROLLER_HOST:/srv/hpc/home /srv/hpc/home nfs4 _netdev,auto 0 0
$LAB_CONTROLLER_HOST:/srv/hpc/scratch /srv/hpc/scratch nfs4 _netdev,auto 0 0
$LAB_CONTROLLER_HOST:/srv/hpc/project /srv/hpc/project nfs4 _netdev,auto 0 0
/srv/hpc/home/hpctest /home/hpctest none bind 0 0
EOF2
if mountpoint -q /home/hpctest; then
  [ "$(stat -c '%d:%i' /home/hpctest)" = "$(stat -c '%d:%i' /srv/hpc/home/hpctest)" ] || {
    echo '/home/hpctest is mounted but is not the expected shared-home bind mount.' >&2
    exit 1
  }
else
  mount --bind /srv/hpc/home/hpctest /home/hpctest
fi


systemctl enable --now ssh
# The package may have started munged with a node-local key. Keep it stopped until
# lab-up installs the controller key, then restart it there.
systemctl stop munge >/dev/null 2>&1 || true
install -d /var/lib/slurm/slurmd /var/log/slurm
chown -R slurm:slurm /var/lib/slurm /var/log/slurm