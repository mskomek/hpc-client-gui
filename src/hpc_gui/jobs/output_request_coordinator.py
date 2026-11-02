"""Generation and in-flight coordination for asynchronous output reads."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass
class OutputRequestBindings:
    state: dict[str, Any]
    selected_job_store: Any
    lock: Any
    session_generation: Callable[[], Any] | None


class OutputRequestCoordinator:
    """Bind every output response to selection, provider, and session epochs."""

    def __init__(self, bindings: OutputRequestBindings) -> None:
        self.bindings = bindings

    def owner(self, job_id: str) -> tuple[Any, ...]:
        bindings = self.bindings
        return (
            str(job_id),
            bindings.state["selected_generation"],
            bindings.selected_job_store.generation,
            bindings.state["provider_generation"],
            bindings.session_generation() if callable(bindings.session_generation) else None,
        )

    def is_current(self, owner: tuple[Any, ...]) -> bool:
        bindings = self.bindings
        job_id, selected_generation, store_generation, provider_generation, session_generation = owner
        state = bindings.state
        return (
            not state["closed"]
            and state["selected_job"] == job_id
            and state["selected_generation"] == selected_generation
            and bindings.selected_job_store.generation == store_generation
            and state["provider_generation"] == provider_generation
            and (
                not callable(bindings.session_generation)
                or bindings.session_generation() == session_generation
            )
        )

    def begin(self, owner: tuple[Any, ...], force: bool):
        bindings = self.bindings
        state = bindings.state
        with bindings.lock:
            if state["closed"]:
                return None
            active = state["outputs_active_generations"]
            if owner in active:
                pending = state["outputs_pending_generations"]
                pending[owner] = pending.get(owner, False) or force
                return None
            active.add(owner)
            state["outputs_requests"] = len(active)
            state["outputs_in_flight"] = True
            state["outputs_request_id"] += 1
            state["outputs_generation"] += 1
            return state["outputs_request_id"], state["outputs_generation"]

    def finish(self, owner: tuple[Any, ...]) -> tuple[bool, bool | None]:
        bindings = self.bindings
        state = bindings.state
        with bindings.lock:
            state["outputs_active_generations"].discard(owner)
            state["outputs_requests"] = len(state["outputs_active_generations"])
            state["outputs_in_flight"] = bool(state["outputs_active_generations"])
            pending_force = state["outputs_pending_generations"].pop(owner, None)
            owner_current = self.is_current(owner)
        return owner_current, pending_force