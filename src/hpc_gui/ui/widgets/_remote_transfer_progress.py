"""Remote transfer-progress leaf for the file-manager remote panel.

Owns ``RemoteTransferProgressMixin``: the transfer queue view
(``_queue_set`` / ``_queue_progress`` / ``_queue_clear``), the audit journal
(``_journal_transfer``), and diagnostic batch-state persistence
(``_persist_batch_state``). The progress view mirrors the runner's plan before
execution and drains as worker progress arrives; the journal appends
redacted operation events for diagnostics; persistence writes the remaining
steps of an interrupted batch as a logs-only artifact (it never auto-resumes).
``shutdown()`` in ``_remote_transfer_exec`` calls persistence as one ordered
step of its verbatim lifecycle sequence, reached via ``self``.

Imports Qt and lower-level core only — never the local panel, FTP widget,
controllers, or another branch's private implementation. Shared plan
vocabulary (``_PlannedOp``) is imported from the sibling ``_remote_mutations``
module: same remote-panel branch, one-directional edge, no cycle.
"""

from __future__ import annotations

import os
from typing import List

from hpc_gui.ui.widgets._remote_mutations import _PlannedOp


class RemoteTransferProgressMixin:
    """Transfer progress/diagnostics ownership (mixed into ``RemoteDirPanel``)."""

    def _queue_set(self, plan: List[_PlannedOp]) -> None:
        self.queue_list.clear()  # type: ignore[attr-defined]
        for op in plan:
            name = os.path.basename((op.dst or op.src).rstrip("/"))
            label = f"{op.op}: {name}"
            self.queue_list.addItem(label)  # type: ignore[attr-defined]
        self.queue_current.setText("-")  # type: ignore[attr-defined]
        self.queue_group.setVisible(True)  # type: ignore[attr-defined]

    def _queue_progress(self, step: int, label: str) -> None:
        self.queue_current.setText(label)  # type: ignore[attr-defined]
        # Worker emits progress *before* executing the step, so we remove the
        # previous item when step advances.
        if step > 1 and self.queue_list.count() > 0:  # type: ignore[attr-defined]
            self.queue_list.takeItem(0)  # type: ignore[attr-defined]

    def _queue_clear(self) -> None:
        self.queue_current.setText("-")  # type: ignore[attr-defined]
        self.queue_list.clear()  # type: ignore[attr-defined]
        self.queue_group.setVisible(False)  # type: ignore[attr-defined]

    def _journal_transfer(self, event: str, **fields) -> None:
        """Append transfer operation events for diagnostics/audit."""
        try:
            import json
            import os
            from datetime import datetime

            from hpc_gui.core.paths import app_data_dir
            from hpc_gui.core.log_redaction import redact_text

            p = app_data_dir() / "transfer_journal.jsonl"
            p.parent.mkdir(parents=True, exist_ok=True)
            payload = {"ts": datetime.now().isoformat(timespec="seconds"), "event": event}
            payload.update(fields or {})
            with p.open("a", encoding="utf-8") as f:
                f.write(redact_text(json.dumps(payload, ensure_ascii=False)) + "\n")
            if os.name == "posix":
                p.chmod(0o600)
        except Exception:
            pass

    def _persist_batch_state(self, remaining: List[_PlannedOp], *, title: str) -> None:
        """Write remaining batch operations to ~/.truba_slurm_gui/last_batch.json.

        This is *logs-only* / diagnostics; it does not auto-resume.
        """
        try:
            import json
            import os
            import time

            from hpc_gui.core.paths import app_data_dir

            out_path = app_data_dir() / "last_batch.json"
            out_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "ts": int(time.time()),
                "title": title,
                "remaining": [
                    {
                        "op": op.op,
                        "src": op.src,
                        "dst": op.dst,
                        "recursive": bool(op.recursive),
                    }
                    for op in remaining
                ],
            }
            out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            if os.name == "posix":
                out_path.chmod(0o600)
        except Exception:
            pass


__all__ = [
    "RemoteTransferProgressMixin",
]
