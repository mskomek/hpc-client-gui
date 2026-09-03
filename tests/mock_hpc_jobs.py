from __future__ import annotations

from threading import Event, Lock, get_ident


class MockHPCJobs:
    """Deterministic Slurm/files boundary for local Jobs stress tests."""

    def __init__(self, count=3):
        self._lock = Lock()
        self.jobs = {str(index): {"id": str(index), "state": "RUNNING"} for index in range(1, count + 1)}
        self.stdout = {job_id: "line 1" for job_id in self.jobs}
        self.stderr = {job_id: "" for job_id in self.jobs}
        self.missing = set()
        self.read_gate: Event | None = None
        self.list_calls = 0
        self.read_calls: list[str] = []
        self.cancel_calls: list[str] = []
        self.active_reads = 0
        self.peak_reads = 0
        self.worker_threads: set[int] = set()

    def list_jobs(self):
        with self._lock:
            self.list_calls += 1
            return [dict(job) for job in self.jobs.values()]

    def read_output(self, job_id):
        job_id = str(job_id)
        with self._lock:
            self.read_calls.append(job_id)
            self.active_reads += 1
            self.peak_reads = max(self.peak_reads, self.active_reads)
            self.worker_threads.add(get_ident())
        try:
            if self.read_gate is not None:
                self.read_gate.wait(2)
            if job_id in self.missing:
                raise FileNotFoundError(job_id)
            with self._lock:
                return {"stdout": self.stdout[job_id], "stderr": self.stderr[job_id]}
        finally:
            with self._lock:
                self.active_reads -= 1

    def cancel(self, job_id):
        job_id = str(job_id)
        with self._lock:
            self.cancel_calls.append(job_id)
            self.jobs[job_id]["state"] = "CANCELLED"

    def append(self, job_id, line, *, stream="stdout"):
        target = self.stdout if stream == "stdout" else self.stderr
        with self._lock:
            target[str(job_id)] += f"\n{line}"

    def transition(self, job_id, state):
        with self._lock:
            self.jobs[str(job_id)]["state"] = state

    def set_output(self, job_id, text, *, stream="stdout"):
        target = self.stdout if stream == "stdout" else self.stderr
        with self._lock:
            target[str(job_id)] = str(text)
