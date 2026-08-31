from __future__ import annotations

from dataclasses import dataclass

ALLOWED_REMOTE_VARIABLES = frozenset({"HOME", "SCRATCH", "WORK", "PROJECT"})
_REMOTE_COMMANDS = {name: f"printf '%s\\n' \"${name}\"" for name in ALLOWED_REMOTE_VARIABLES}
MAX_PATH_OUTPUT = 4096


@dataclass(frozen=True)
class RemotePathResult:
    state: str
    path: str = ""
    reason: str = ""


class ProviderPathResolver:
    def __init__(self, ssh, *, timeout_s: float = 10.0) -> None:
        self._ssh = ssh
        self._timeout_s = timeout_s
        self._cache: dict[str, RemotePathResult] = {}

    def resolve(self, variable: str) -> RemotePathResult:
        if variable not in ALLOWED_REMOTE_VARIABLES:
            return RemotePathResult("invalid", reason="variable is not allow-listed")
        if variable in self._cache:
            return self._cache[variable]
        try:
            code, output, _ = self._ssh.run(_REMOTE_COMMANDS[variable], timeout_s=self._timeout_s)
        except Exception as exc:
            result = RemotePathResult("unavailable", reason=str(exc))
        else:
            value = output.strip()
            if code != 0 or not value:
                result = RemotePathResult("unavailable", reason="remote variable unavailable")
            elif len(value) > MAX_PATH_OUTPUT or "\n" in value or "\r" in value or not value.startswith("/"):
                result = RemotePathResult("invalid", reason="remote value is not one absolute path")
            else:
                result = RemotePathResult("resolved", path=value)
        self._cache[variable] = result
        return result

    def invalidate(self) -> None:
        self._cache.clear()
