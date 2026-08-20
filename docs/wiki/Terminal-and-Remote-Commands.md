# Terminal and Remote Commands

> Türkçe: [[Terminal-and-Remote-Commands-TR]]

Two ways to run things remotely: a one-off command, or an interactive
terminal.

## One-off commands

The connection view has a **Command** field — type a command and press Enter,
or use **Run**. Output appears in the console; errors are reported with the
message from the remote side, and `STDERR` is shown separately from standard
output so a failure is not buried in normal output.

This is the quickest way to check what the application's parsed views are
based on:

```text
squeue -u $USER
sinfo -o "%P %a %l %D %t"
```

## The interactive terminal

The embedded terminal is a real terminal emulator with a main and an alternate
screen buffer — so full-screen programs such as an editor or `htop` behave
correctly — and a scrollback buffer. Its size can be set explicitly:

```bash
hpc-client-gui --profile mycluster terminal --cols 120 --rows 40
```

Shell scripts in the file manager can be sent straight here with **Run in
terminal**, or **Run all in terminal** for a selection. The editor's
**Save + Run** does the same for the file being edited. Completion and failure
are both reported.

## Command history

Commands you run are kept in a history under `~/.truba_slurm_gui/history.jsonl`
so they can be recalled later.

History deliberately **skips commands that look like they contain a secret**.
The filter is conservative by design: when in doubt it does not persist the
command. That is the right trade — a missing history entry costs you retyping,
while a persisted one puts a credential in a file on disk.

This is also why you should not paste a password into a remote command. Use
key-based authentication, or `--password-stdin` for scripted use. See
[[Scripting Examples|Scripting-Examples]] and
[[Security Model|Security-Model]].

## From the command line

```bash
# One remote command; -- separates it from this interface's own options
hpc-client-gui --profile mycluster sh -- sacct -j 123456 --format=JobID,State,Elapsed

# A remote script with arguments
hpc-client-gui --profile mycluster run /scratch/$USER/analyze.sh input.csv

# An interactive prompt for this interface itself
hpc-client-gui --profile mycluster interactive
```

`sh` runs a single remote command; `run` runs a remote script; `interactive`
opens a prompt for this application's own commands rather than a remote shell.
See [[CLI Guide|CLI-Guide]].

## If the session drops

A dropped session is reported with its reason and an offer to reconnect —
press `r` or answer Yes. See
[[Connecting and Profiles|Connecting-and-Profiles]].

## See also

[[Script Editor|Script-Editor]] · [[X11 Forwarding|X11-Forwarding]] · [[Slurm Help Library|Slurm-Help-Library]]
