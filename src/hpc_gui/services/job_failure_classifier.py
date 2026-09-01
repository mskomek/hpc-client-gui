from __future__ import annotations

from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class FailureExplanation:
    category: str
    possible_cause: str
    scheduler_reported: str
    next_step: str

    def as_lines(self) -> list[str]:
        return [f"Possible cause: {self.possible_cause}", f"Scheduler reported: {self.scheduler_reported}", f"Next step: {self.next_step}"]


_CASES = (
    ("oom", ("OUT_OF_MEMORY", "OOM", "OUT OF MEMORY"), "Memory limit was reached.", "Review MaxRSS and raise --mem only if the workload requires it."),
    ("timeout", ("TIMEOUT", "TIME LIMIT"), "The time limit was reached.", "Review elapsed time and adjust --time only after checking the workload."),
    ("node_fail", ("NODE_FAIL", "NODE FAILURE"), "The allocated node reported a failure.", "Retry after checking the scheduler/node report; do not assume the script is faulty."),
    ("preempted", ("PREEMPTED", "PREEMPT"), "The scheduler preempted the job.", "Check partition/QOS policy and resubmit when policy permits."),
    ("cancelled", ("CANCELLED", "CANCELED"), "The job was cancelled.", "Confirm who or what cancelled it before resubmitting."),
    ("boot_fail", ("BOOT_FAIL", "BOOT FAILURE"), "The allocated node failed during boot.", "Retry or contact the cluster administrator if it repeats."),
    ("deadline", ("DEADLINE",), "The job missed its scheduler deadline.", "Check the deadline and dependency timing before resubmitting."),
)


def _value(job, name: str) -> str:
    value = getattr(job, name, "")
    return "" if value is None else str(value).strip()


def _scheduler_text(job) -> str:
    values = (_value(job, "state"), _value(job, "reason"), _value(job, "failure_reason"))
    return "; ".join(value for value in values if value) or "No scheduler reason was reported."


def explain_job_failure(job, translate: Callable[[str, str], str] | None = None) -> FailureExplanation | None:
    state = _scheduler_text(job).upper()
    for category, markers, cause, next_step in _CASES:
        if any(marker in state for marker in markers):
            return FailureExplanation(category, _text(translate, f"failure.{category}.cause", cause), _text(translate, "failure.scheduler_reported", _scheduler_text(job)), _text(translate, f"failure.{category}.next_step", next_step))
    exit_code = _value(job, "exit_code")
    if exit_code and not exit_code.startswith("0"):
        return FailureExplanation("nonzero_exit", _text(translate, "failure.nonzero_exit.cause", "The job exited with a non-zero status."), _text(translate, "failure.scheduler_reported", _scheduler_text(job)), _text(translate, "failure.nonzero_exit.next_step", "Inspect the job output and script exit path before resubmitting."))
    return None


def _text(translate: Callable[[str, str], str] | None, key: str, fallback: str) -> str:
    return translate(key, fallback) if translate is not None else fallback
