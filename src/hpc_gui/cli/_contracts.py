"""Stable command-line names shared by parser and command handlers."""

CLI_VERSION = "1.5.9"

ROOT_ALIASES = {
    "put": ("files", "upload"), "get": ("files", "download"),
    "ls": ("files", "ls"), "stat": ("files", "stat"),
    "checksum": ("files", "checksum"), "mkdir": ("files", "mkdir"),
    "cp": ("files", "cp"), "mv": ("files", "mv"), "rm": ("files", "rm"),
    "squeue": ("jobs", "list"), "scontrol": ("jobs", "status"),
    "sacct": ("jobs", "accounting"), "lssrv": ("jobs", "lssrv"),
    "sbatch": ("jobs", "submit"), "scancel": ("jobs", "cancel"),
}
