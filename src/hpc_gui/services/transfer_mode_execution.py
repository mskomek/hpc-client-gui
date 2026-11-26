"""Mode-aware execution for the native file queue, independent of GUI toolkit."""
from __future__ import annotations

from pathlib import Path
from hpc_gui.services.transfer_conflict_policy import destination_exists
from hpc_gui.services.transfer_mode import (
    BINARY, CHUNK_SIZE, download_with_mode, is_known_text_path,
    normalize_transfer_mode, resolve_transfer_mode, upload_with_mode,
)


def execute_with_mode(files, item, progress, requested, decision, raw_transfer, *, verify_bytes=None):
    """Stage new files; preserve explicitly approved raw final-file resume.

    Standard SFTP rename cannot replace a destination. An approved overwrite
    uses the existing direct backend contract rather than delete+rename.
    """
    requested = normalize_transfer_mode(requested)
    final_exists = destination_exists(files, item.op, item.dst)
    if final_exists and decision == "resume":
        if item.op == "download" and Path(item.dst).is_symlink():
            raise ValueError("Refusing to resume into a local symlink")
        if item.op == "upload":
            with open(item.src, "rb") as stream:
                effective = resolve_transfer_mode(item.src, requested, stream.read(CHUNK_SIZE))
        else:
            effective = requested
            if requested == "auto" and not is_known_text_path(item.src):
                effective = BINARY
        if effective != BINARY:
            raise ValueError("Resume of an existing final file requires Binary mode")
        raw_transfer(files, item, progress, conflict_decision="resume")
        if verify_bytes is not None:
            local, remote = (item.src, item.dst) if item.op == "upload" else (item.dst, item.src)
            verify_bytes(local, remote)
        return BINARY

    if final_exists and decision != "overwrite":
        raise FileExistsError(item.dst)

    allow_resume = decision != "overwrite"
    if item.op == "upload":
        return upload_with_mode(
            files, item.src, item.dst, requested, progress_cb=progress,
            allow_resume=allow_resume, stage_remote=not final_exists, verify_bytes=verify_bytes,
        )
    if item.op == "download":
        return download_with_mode(
            files, item.src, item.dst, requested, progress_cb=progress,
            allow_resume=allow_resume, verify_bytes=verify_bytes,
        )
    raise ValueError(f"Unsupported transfer mode operation: {item.op}")
