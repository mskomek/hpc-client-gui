#!/usr/bin/env bash
# Read-only Slurm/SSH environment probe for compatibility validation.
#
# Run this ON THE CLUSTER LOGIN NODE with your own account. It only prints or
# reads: no sbatch, no scancel, no scontrol update, no file writes/deletes,
# no job submission.
#
# Usage:
#   bash slurm_readonly_probe.sh > capture.txt
#   REDACT=1 bash slurm_readonly_probe.sh > capture_sanitized.txt
#
# With REDACT=1 your username and short hostname are replaced in every output
# line before it is printed.

set -u

if [ "${REDACT:-0}" = "1" ]; then
    _USER_TOKEN="$(whoami 2>/dev/null || printf '%s' "${USER:-user}")"
    _HOST_TOKEN="$(hostname -s 2>/dev/null || hostname)"
    mask() {
        sed -e "s#${_USER_TOKEN}#[redacted-user]#g" \
            -e "s#${_HOST_TOKEN}#[redacted-host]#g"
    }
else
    mask() { cat; }
fi

section() {
    printf '\n=== %s ===\n' "$1" | mask
}

run() {
    printf '$ %s\n' "$*"
    out="$(eval "$@" 2>&1)"
    status=$?
    if [ $status -ne 0 ] && [ -z "$out" ]; then
        out="[not found or failed (exit=$status)]"
    fi
    printf '%s\n' "$out" | mask
}

section "host"
run "uname -s"
if [ "${REDACT:-0}" = "1" ]; then
    printf '$ whoami\n[redacted-user]\n'
else
    run "whoami"
fi

section "scheduler binaries"
for tool in squeue sbatch sacct scancel scontrol; do
    run "command -v ${tool}"
done

section "versions"
run "squeue --version"
run "sacct --version"
run "scontrol --version"

section "read-only scheduler views (own account)"
run 'squeue -u "$USER" -h -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"'
run 'sacct -u "$USER" --format=JobID,JobName,State,Elapsed,MaxRSS,AllocTRES -n -P'

section "done"
printf 'Nothing state-changing was executed by this script.\n' | mask
