#!/bin/bash
# Bring up the local HPC lab: munge -> mariadb -> slurmdbd -> slurmctld ->
# slurmd -> sshd (foreground). Each step waits for the previous one so a slow
# host does not produce a half-started cluster that looks healthy.
set -euo pipefail

log() { echo "[lab] $*"; }

wait_for() {
    local what="$1" tries="$2"; shift 2
    local i
    for ((i = 1; i <= tries; i++)); do
        if "$@" >/dev/null 2>&1; then
            log "$what ready"
            return 0
        fi
        sleep 1
    done
    log "ERROR: $what did not become ready in ${tries}s"
    return 1
}

# --- munge ------------------------------------------------------------------
if [[ ! -s /etc/munge/munge.key ]]; then
    log "creating munge key"
    dd if=/dev/urandom of=/etc/munge/munge.key bs=1024 count=1 status=none
fi
chown munge:munge /etc/munge/munge.key
chmod 400 /etc/munge/munge.key
install -d -o munge -g munge -m 0755 /run/munge /var/log/munge /var/lib/munge
log "starting munged"
runuser -u munge -- /usr/sbin/munged --force
wait_for munge 15 munge -n

# --- mariadb ----------------------------------------------------------------
install -d -o mysql -g mysql /run/mysqld
if [[ ! -d /var/lib/mysql/mysql ]]; then
    log "initialising mariadb"
    mariadb-install-db --user=mysql --datadir=/var/lib/mysql >/dev/null
fi
log "starting mariadb"
runuser -u mysql -- /usr/sbin/mariadbd --datadir=/var/lib/mysql --skip-networking=0 \
    --bind-address=127.0.0.1 >/var/log/mariadb.log 2>&1 &
wait_for mariadb 60 mariadb -u root -e 'SELECT 1'

log "ensuring accounting database"
mariadb -u root <<'SQL'
CREATE DATABASE IF NOT EXISTS slurm_acct_db;
CREATE USER IF NOT EXISTS 'slurm'@'localhost' IDENTIFIED BY 'slurmlabpass';
GRANT ALL ON slurm_acct_db.* TO 'slurm'@'localhost';
FLUSH PRIVILEGES;
SQL

# --- slurmdbd ---------------------------------------------------------------
log "starting slurmdbd"
/usr/sbin/slurmdbd
wait_for slurmdbd 60 sacctmgr -i show cluster

log "registering cluster"
sacctmgr -i add cluster hpclab >/dev/null 2>&1 || true
sacctmgr -i add account labusers Description="local lab" >/dev/null 2>&1 || true
sacctmgr -i add user hpctest account=labusers >/dev/null 2>&1 || true

# --- slurmctld / slurmd -----------------------------------------------------
log "starting slurmctld"
/usr/sbin/slurmctld
wait_for slurmctld 60 scontrol ping

log "starting slurmd"
/usr/sbin/slurmd
wait_for slurmd 60 scontrol show node hpclab

# A node that registered after slurmctld started stays DOWN until resumed.
# Do this before asserting readiness, and never let a transient state kill
# the container -- the healthcheck is what gates "usable".
scontrol update NodeName=hpclab State=RESUME Reason=startup >/dev/null 2>&1 || true
if ! wait_for "node idle" 60 bash -c "sinfo -h -o '%T' | grep -q idle"; then
    log "WARNING: node is not idle yet; current state:"
    sinfo || true
    scontrol show node hpclab | head -20 || true
fi

sinfo || true
log "cluster up; starting sshd on port 22"

# --- sshd (foreground, PID 1 child) ----------------------------------------
# /run is a tmpfs mount, so the privilege-separation directory baked into the
# image is gone by the time we get here. Recreate it every boot.
install -d -m 0755 /run/sshd
ssh-keygen -A
exec /usr/sbin/sshd -D -e
