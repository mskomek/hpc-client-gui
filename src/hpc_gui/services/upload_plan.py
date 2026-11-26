"""GUI-independent upload planning and preflight summaries."""
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path, PurePosixPath

from hpc_gui.config.storage import coerce_profile_transfer_parallelism
from hpc_gui.services.transfer_controller import TransferItem


@dataclass(frozen=True)
class UploadPlanSummary:
    files: int
    folders: int
    steps: int
    parallel: int
    visible: tuple[TransferItem, ...]
    hidden: int


def transfer_limits(files, profile) -> tuple[int, int]:
    configured = coerce_profile_transfer_parallelism(
        (profile or {}).get("transfer_parallelism", 1)
    )
    effective = configured if bool(getattr(files, "supports_parallel_transfers", False)) else 1
    return configured, effective


def summarize_upload_plan(items, parallel_limit: int, *, max_rows: int = 200) -> UploadPlanSummary:
    items = tuple(items)
    return UploadPlanSummary(
        files=sum(item.op == "upload" for item in items),
        folders=sum(item.op == "mkdir_remote" for item in items),
        steps=len(items),
        parallel=parallel_limit,
        visible=items[:max_rows],
        hidden=max(0, len(items) - max_rows),
    )


def build_upload_plan(paths, destination: str) -> list[TransferItem]:
    """Expand local directories without any remote calls or mutations."""
    items = []
    seen = set()
    remote_dir = PurePosixPath(destination)

    def raise_walk_error(error):
        raise error

    for path in paths:
        source = Path(os.path.abspath(os.fspath(path)))
        if source in seen:
            continue
        seen.add(source)
        if not source.name:
            raise ValueError("Cannot upload a filesystem root")
        remote_base = remote_dir / source.name
        if not source.is_dir():
            if not source.is_file():
                raise FileNotFoundError(str(source))
            items.append(TransferItem("upload", str(source), str(remote_base), cached_size=source.stat().st_size))
            continue
        items.append(TransferItem("mkdir_remote", "", str(remote_base)))
        for root, directories, filenames in os.walk(source, onerror=raise_walk_error):
            directories.sort()
            filenames.sort()
            remote_root = remote_base / Path(root).relative_to(source).as_posix()
            for directory in directories:
                items.append(TransferItem("mkdir_remote", "", str(remote_root / directory)))
            for filename in filenames:
                local_file = Path(root) / filename
                if not local_file.is_file():
                    raise FileNotFoundError(str(local_file))
                items.append(TransferItem("upload", str(local_file), str(remote_root / filename),
                                          cached_size=local_file.stat().st_size))
    return items
