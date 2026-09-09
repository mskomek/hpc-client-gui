from abc import ABC, abstractmethod

class SlurmBackend(ABC):
    @abstractmethod
    def squeue(self, user: str) -> str: ...

    @abstractmethod
    def sbatch(self, script_path: str) -> str: ...

    @abstractmethod
    def scancel(self, job_id: str) -> str: ...

    @abstractmethod
    def sacct(self, user: str) -> str: ...

    def sacct_job(self, job_id: str) -> str:
        """Query accounting for a specific job ID. Default falls back to sacct."""
        return self.sacct("")

    @abstractmethod
    def scontrol_show_job(self, job_id: str) -> str: ...

    @abstractmethod
    def lssrv(self) -> str: ...

    @abstractmethod
    def active_job_ids(self, user: str) -> str: ...

    @abstractmethod
    def job_state(self, job_id: str) -> str: ...
