"""Pure presentation helpers shared by the remote directory views.

These functions must stay Qt-free so they can be unit tested headless.
"""

from __future__ import annotations

import datetime
import re

from hpc_gui.core.i18n import t
from hpc_gui.services.files_base import RemoteEntry


def fmt_size(n: int) -> str:
    try:
        n = int(n)
    except Exception:
        return ""
    units = ["B", "KB", "MB", "GB", "TB"]
    v = float(n)
    i = 0
    while v >= 1024 and i < len(units) - 1:
        v /= 1024.0
        i += 1
    return f"{v:.1f} {units[i]}" if i else f"{int(v)} {units[i]}"


def fmt_mtime(ts: int) -> str:
    if not ts:
        return ""
    try:
        return datetime.datetime.fromtimestamp(int(ts)).strftime("%d-%m-%y %H:%M")
    except Exception:
        return ""


def file_type(name: str, is_dir: bool) -> str:
    if is_dir:
        folder = t("dirs.type_folder")
        return folder if folder != "[dirs.type_folder]" else "Klasör"
    lower = name.lower()
    if lower.endswith(".iso"):
        return "Disc Image File"
    if lower.endswith((".zip", ".rar", ".7z")):
        return "WinRAR ZIP archive"
    if lower.endswith((".tgz", ".tar.gz", ".tar")):
        return "TAR archive"
    if "." in name:
        return name.split(".")[-1].upper() + " File"
    return "File"


def category(entry: RemoteEntry) -> str:
    if entry.is_dir:
        return "folders"
    lower = entry.name.lower()
    if lower.endswith(".iso"):
        return "iso"
    if lower.endswith((".zip", ".rar", ".7z", ".tgz", ".tar.gz", ".tar")):
        return "archives"
    if lower.endswith(".sh"):
        return "shell"
    if lower.endswith((".slurm", ".sbatch")):
        return "slurm"
    return "other"


def natural_sort_key(value: str) -> tuple:
    return tuple(
        (1, int(part)) if part.isdigit() else (0, part.casefold())
        for part in re.split(r"(\d+)", value or "")
        if part
    )
