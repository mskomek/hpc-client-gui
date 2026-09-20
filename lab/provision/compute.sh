#!/usr/bin/env bash
set -euo pipefail
: "${HPCTEST_UID:?set HPCTEST_UID in the provisioning environment}"
: "${HPCTEST_GID:?set HPCTEST_GID in the provisioning environment}"
: "${SLURM_UID:?set SLURM_UID in the provisioning environment}"
: "${SLURM_GID:?set SLURM_GID in the provisioning environment}"
export DEBIAN_FRONTEND=noninteractive
apt-get update
apt-get install -y openssh-server openssh-client munge slurmd nfs-common
id hpctest >/dev/null 2>&1 || useradd --create-home --shell /bin/bash hpctest
ensure_group_id() {
  local group=$1 gid=$2 owner
  owner=$(getent group "$gid" | cut -d: -f1 || true)
  [ -z "$owner" ] || [ "$owner" = "$group" ] || { echo "GID $gid belongs to $owner" >&2; exit 1; }
  [ "$(getent group "$group" | cut -d: -f3)" = "$gid" ] || groupmod -g "$gid" "$group"
}
ensure_user_id() {
  local user=$1 uid=$2 owner
  owner=$(getent passwd "$uid" | cut -d: -f1 || true)
  [ -z "$owner" ] || [ "$owner" = "$user" ] || { echo "UID $uid belongs to $owner" >&2; exit 1; }
  [ "$(id -u "$user")" = "$uid" ] || usermod -u "$uid" "$user"
}
ensure_group_id hpctest "$HPCTEST_GID"
ensure_user_id hpctest "$HPCTEST_UID"
ensure_group_id slurm "$SLURM_GID"
ensure_user_id slurm "$SLURM_UID"
grep -q '^login-control01 ' /etc/hosts || cat >>/etc/hosts <<'EOF'
192.168.250.11 login-control01
192.168.250.12 compute01
192.168.250.13 compute02
EOF
install -d /srv/hpc/home /srv/hpc/scratch /srv/hpc/project
mountpoint -q /srv/hpc/home || mount -t nfs4 login-control01:/srv/hpc/home /srv/hpc/home
mountpoint -q /srv/hpc/scratch || mount -t nfs4 login-control01:/srv/hpc/scratch /srv/hpc/scratch
mountpoint -q /srv/hpc/project || mount -t nfs4 login-control01:/srv/hpc/project /srv/hpc/project
install -d -m 0700 -o hpctest -g hpctest /srv/hpc/home/hpctest /srv/hpc/scratch/hpctest /srv/hpc/project/hpctest
install -d -m 0700 -o hpctest -g hpctest /srv/hpc/home/hpctest/.ssh
key_tmp=$(mktemp)
for key_file in /home/hpctest/.ssh/authorized_keys /srv/hpc/home/hpctest/.ssh/authorized_keys; do
  [ -f "$key_file" ] && cat "$key_file"
done | awk 'NF && !seen[$0]++' >"$key_tmp"
install -o hpctest -g hpctest -m 0600 "$key_tmp" /srv/hpc/home/hpctest/.ssh/authorized_keys
rm -f "$key_tmp"
chown hpctest:hpctest /srv/hpc/home/hpctest
usermod -d /srv/hpc/home/hpctest hpctest
chown hpctest:hpctest /srv/hpc/home/hpctest/.ssh /srv/hpc/home/hpctest/.ssh/authorized_keys
chmod 0700 /srv/hpc/home/hpctest/.ssh
chmod 0600 /srv/hpc/home/hpctest/.ssh/authorized_keys
sed -i '\#^login-control01:/srv/hpc/.* nfs4 #d' /etc/fstab
for old_mount in /home /scratch /project; do
  mountpoint -q "$old_mount" && umount "$old_mount"
done
cat >>/etc/fstab <<'EOF'
login-control01:/srv/hpc/home /srv/hpc/home nfs4 _netdev,auto 0 0
login-control01:/srv/hpc/scratch /srv/hpc/scratch nfs4 _netdev,auto 0 0
login-control01:/srv/hpc/project /srv/hpc/project nfs4 _netdev,auto 0 0
EOF
systemctl enable --now ssh
install -d /var/lib/slurm/slurmd
chown -R slurm:slurm /var/lib/slurm
