"""Framework-neutral selected-job context for the Jobs & Outputs workspace."""

from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class SelectedJobContext:
    """Immutable snapshot of the currently selected job.

    ``generation`` is a monotonically increasing integer that allows consumers
    to reject stale asynchronous responses.  Every time the selection changes
    the generation must be incremented *before* dispatching any background
    request that depends on the previous selection.
    """

    generation: int
    job_id: str
    name: str = ""
    state: str = ""
    partition: str = ""
    elapsed: str = ""
    nodes: str = ""
    cpus: str = ""
    reason: str = ""
    workdir: str = ""
    stdout_path: str = ""
    stderr_path: str = ""
    raw_scontrol: str = ""
    user: str = ""
    script_path: str = ""
    exit_code: str = ""
    nodelist: str = ""
    failure_reason: str = ""

    # -- derived helpers -----------------------------------------------------

    @property
    def has_selection(self) -> bool:
        return bool(self.job_id)

    @property
    def display_name(self) -> str:
        return self.name or self.job_id


class SelectedJobStore:
    """Thread-safe observable store for the selected-job context.

    Every ``select()`` call publishes a new immutable ``SelectedJobContext``
    and bumps the generation counter.  Consumers can subscribe to changes
    through the registered callbacks.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._generation = 0
        self._context = SelectedJobContext(generation=0, job_id="")
        self._listeners: list[Callable[[SelectedJobContext], None]] = []

    # -- read ----------------------------------------------------------------

    @property
    def generation(self) -> int:
        with self._lock:
            return self._generation

    @property
    def context(self) -> SelectedJobContext:
        with self._lock:
            return self._context

    @property
    def job_id(self) -> str:
        with self._lock:
            return self._context.job_id

    @property
    def workdir(self) -> str:
        with self._lock:
            return self._context.workdir

    # -- mutation ------------------------------------------------------------

    def select(self, **kwargs: Any) -> SelectedJobContext:
        """Publish a new context snapshot and notify listeners.

        Any keyword argument matching a ``SelectedJobContext`` field will be
        applied.  ``generation`` is always incremented automatically – callers
        must *not* pass it.

        When a new ``job_id`` is provided (i.e. the user selected a different
        job), all enrichable metadata fields are **cleared first** so that
        stale data from the previous selection cannot leak into the new one.
        """
        with self._lock:
            self._generation += 1
            new_job_id = str(kwargs.get("job_id", "")).strip()
            previous_job_id = self._context.job_id

            if new_job_id and new_job_id != previous_job_id:
                merged: dict[str, Any] = {
                    "generation": self._generation,
                    "job_id": new_job_id,
                    "name": "",
                    "state": "",
                    "partition": "",
                    "elapsed": "",
                    "nodes": "",
                    "cpus": "",
                    "reason": "",
                    "workdir": "",
                    "stdout_path": "",
                    "stderr_path": "",
                    "raw_scontrol": "",
                    "user": "",
                    "script_path": "",
                    "exit_code": "",
                    "nodelist": "",
                    "failure_reason": "",
                }
            else:
                current = self._context
                merged = {
                    "generation": self._generation,
                    "job_id": current.job_id,
                    "name": current.name,
                    "state": current.state,
                    "partition": current.partition,
                    "elapsed": current.elapsed,
                    "nodes": current.nodes,
                    "cpus": current.cpus,
                    "reason": current.reason,
                    "workdir": current.workdir,
                    "stdout_path": current.stdout_path,
                    "stderr_path": current.stderr_path,
                    "raw_scontrol": current.raw_scontrol,
                    "user": current.user,
                    "script_path": current.script_path,
                    "exit_code": current.exit_code,
                    "nodelist": current.nodelist,
                    "failure_reason": current.failure_reason,
                }
            merged.update(kwargs)
            self._context = SelectedJobContext(**merged)
            ctx = self._context
        self._notify(ctx)
        return ctx

    def update(self, **kwargs: Any) -> SelectedJobContext:
        """Update fields of the current context *without* incrementing
        the generation.  Useful for applying scontrol metadata to an
        already-selected job.
        """
        with self._lock:
            current = self._context
            merged: dict[str, Any] = {
                "generation": current.generation,
                "job_id": current.job_id,
                "name": current.name,
                "state": current.state,
                "partition": current.partition,
                "elapsed": current.elapsed,
                "nodes": current.nodes,
                "cpus": current.cpus,
                "reason": current.reason,
                "workdir": current.workdir,
                "stdout_path": current.stdout_path,
                "stderr_path": current.stderr_path,
                "raw_scontrol": current.raw_scontrol,
                "user": current.user,
                "script_path": current.script_path,
                "exit_code": current.exit_code,
                "nodelist": current.nodelist,
                "failure_reason": current.failure_reason,
            }
            merged.update(kwargs)
            self._context = SelectedJobContext(**merged)
            ctx = self._context
        self._notify(ctx)
        return ctx

    def clear(self) -> None:
        """Clear the selection entirely."""
        self.select(job_id="", name="", state="", workdir="", stdout_path="", stderr_path="", raw_scontrol="")

    # -- subscriptions -------------------------------------------------------

    def subscribe(self, callback: Callable[[SelectedJobContext], None]) -> Callable[[], None]:
        """Register a callback that fires on every context change.

        Returns an *unsubscribe* callable.
        """
        with self._lock:
            self._listeners.append(callback)

        def _unsubscribe() -> None:
            with self._lock:
                try:
                    self._listeners.remove(callback)
                except ValueError:
                    pass

        return _unsubscribe

    # -- internal ------------------------------------------------------------

    def _notify(self, ctx: SelectedJobContext) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for listener in listeners:
            try:
                listener(ctx)
            except Exception:
                pass
