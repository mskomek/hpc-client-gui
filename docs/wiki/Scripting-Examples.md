# Scripting Examples

> Türkçe: [[Scripting-Examples-TR]]

Recipes for non-interactive use. Two rules run through all of them:

1. **Never put a secret on a command line.** Command lines are visible to other
   local processes and are recorded in shell history. Prefer key-based
   authentication; when a password is unavoidable, feed it through
   `--password-stdin` from a source that is not echoed.
2. **Branch on the exit code**, not on message text. See
   [[CLI Exit Codes|CLI-Exit-Codes]].

Before any of this works, "Allow external CLI access to remote commands" must
be enabled in Settings — see [[CLI Overview|CLI-Overview]].

## Check that the environment is sane

```bash
hpc-client-gui doctor environment || exit $?
hpc-client-gui --profile mycluster doctor connection || exit $?
```

## List and fetch results

```bash
hpc-client-gui --profile mycluster --format json files ls /scratch/$USER/results
hpc-client-gui --profile mycluster files download \
  /scratch/$USER/results/out.csv ./out.csv --verify
```

`--verify` compares SHA-256 after the transfer.

## Upload inputs, resuming an interrupted transfer

```bash
hpc-client-gui --profile mycluster files upload \
  ./inputs /scratch/$USER/inputs --recursive --if-exists resume
```

## Submit a job — **mutating, requires `--yes`**

```bash
hpc-client-gui --profile mycluster jobs submit /scratch/$USER/job.sh --yes
```

Without `--yes` the command refuses and exits `2`.

## Poll a job until it leaves the queue

```bash
job_id=$1
while hpc-client-gui --profile mycluster --format json jobs status "$job_id" \
      | grep -q '"RUNNING"\|"PENDING"'; do
  sleep 60
done
```

Adjust the state test to your site's `scontrol` output; Slurm output varies
with site customization.

## Cancel a job — **mutating, requires `--yes`**

```bash
hpc-client-gui --profile mycluster jobs cancel "$job_id" --yes
```

## Delete remote files — **destructive, requires `--yes`**

```bash
hpc-client-gui --profile mycluster files rm /scratch/$USER/tmp --recursive --yes
```

## Run a single remote command

```bash
hpc-client-gui --profile mycluster sh -- sinfo -o "%P %a %l %D %t"
```

The `--` separator is required so the remote command's own options are not
consumed by this interface.

## Password input without exposure

When key-based authentication is not possible, read the password from a
process that never writes it to disk or to a command line:

```bash
# The password is typed into the pipe, not stored anywhere.
read -rs pw && printf '%s' "$pw" \
  | hpc-client-gui --profile mycluster --password-stdin --no-saved-password files ls /home
unset pw
```

`--no-saved-password` ignores a profile's stored protected secret and requires
`--password-stdin`, which is useful in CI-like contexts where you want the
stored secret deliberately bypassed.

Do not hardcode a password in a script, an environment variable, or a
repository. See [[Security Model|Security-Model]].

## Harden against unknown hosts

```bash
hpc-client-gui --profile mycluster --strict-host-key jobs list
```

`--strict-host-key` rejects unknown host keys instead of prompting, which is
the right default for unattended automation.

## See also

[[CLI Command Reference|CLI-Command-Reference]] ·
[[CLI Output Contract|CLI-Output-Contract]] ·
[[Job Script Templates|Job-Script-Templates]]
