"""Safe, side-effect-free quota eligibility gate."""

from __future__ import annotations

from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
import re
from typing import Any, Callable, Iterable

KNOWN_QUOTA_SCOPES = frozenset({"user", "group", "project", "unknown"})
_PLACEHOLDER_RE = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
KNOWN_PLACEHOLDERS = frozenset({"user", "subject", "path", "path_q"})


@dataclass(frozen=True)
class QuotaResult:
    state: str
    used_bytes: int | None = None
    soft_limit_bytes: int | None = None
    hard_limit_bytes: int | None = None
    scope: str = "unknown"
    pool_id: str | None = None
    error: str | None = None
    used_files: int | None = None
    soft_limit_files: int | None = None
    hard_limit_files: int | None = None
    storage_id: str | None = None
    path: str | None = None


@dataclass(frozen=True)
class QuotaBackend:
    backend_id: str
    build_command: Callable[[dict[str, Any]], str]
    parse: Callable[[str], QuotaResult]


class QuotaBackendRegistry:
    """Allow-list of safe adapters; production is empty until documented."""
    def __init__(self, backends: Iterable[QuotaBackend] = ()) -> None:
        self._backends = {backend.backend_id: backend for backend in backends}

    @property
    def ids(self) -> frozenset[str]:
        return frozenset(self._backends)

    def get(self, backend_id: str) -> QuotaBackend | None:
        return self._backends.get(backend_id)


def build_production_quota_backend_registry() -> QuotaBackendRegistry:
    """Return only application-reviewed production backends."""
    from hpc_gui.services.nersc_quota import build_nersc_quota_command, parse_nersc_showquota_json

    from hpc_gui.services.lumi_quota import build_lumi_quota_command, parse_lumi_quota
    from hpc_gui.services.cineca_quota import build_cineca_cinquota_command, parse_cineca_cinquota
    from hpc_gui.services.pawsey_quota import build_pawsey_account_balance_command, parse_pawsey_account_balance

    return QuotaBackendRegistry([
        QuotaBackend("nersc-showquota-json", build_nersc_quota_command, parse_nersc_showquota_json),
        QuotaBackend("lumi-quota", build_lumi_quota_command, parse_lumi_quota),
        QuotaBackend("cineca-cinquota", build_cineca_cinquota_command, parse_cineca_cinquota),
        QuotaBackend("pawsey-account-balance", build_pawsey_account_balance_command, parse_pawsey_account_balance),
    ])


def format_quota_result(result: QuotaResult) -> str:
    def amount(used: int | None, limit: int | None, suffix: str) -> str | None:
        if used is None:
            return None
        return f"{used} / {limit} {suffix}" if limit is not None else f"{used} {suffix}"

    values = [amount(result.used_bytes, result.soft_limit_bytes, "bytes"),
              amount(result.used_files, result.soft_limit_files, "files")]
    return " · ".join(value for value in values if value) or ""


class QuotaMonitor:
    """Bounded, coalescing runtime; no remote work occurs before quota_gate."""
    def __init__(self, registry: QuotaBackendRegistry, transport: Callable[[str, float, int], str], *, max_output: int = 65536) -> None:
        self.registry, self.transport, self.max_output = registry, transport, max_output
        self._executor = ThreadPoolExecutor(max_workers=2)
        self._pending: dict[tuple[str, str, str, str], Future[QuotaResult]] = {}
        self._generation: dict[tuple[str, str, str, str], int] = {}

    def refresh(self, source: dict[str, Any], *, connection_id: str, provider_id: str,
                subject: str, connected: bool = True) -> Future[QuotaResult] | None:
        state = quota_gate(source, backend_ids=self.registry.ids, connected=connected,
                           subject_available=bool(subject))
        if state != "eligible":
            return None
        command_template = str(source.get("command_template") or "")
        if any(item not in KNOWN_PLACEHOLDERS for item in _PLACEHOLDER_RE.findall(command_template)):
            return None
        backend = self.registry.get(str(source.get("backend_id")))
        key = (connection_id, provider_id, str(source.get("id", "")), subject)
        if key in self._pending and not self._pending[key].done():
            return self._pending[key]
        generation = self._generation.get(key, 0)
        timeout = min(max(float(source.get("timeout_seconds") or 30), 0.1), 60.0)
        command = backend.build_command(source) if backend else ""
        def run() -> QuotaResult:
            try:
                output = self.transport(command, timeout, self.max_output)
                if self._generation.get(key, 0) != generation:
                    return QuotaResult("stale")
                return backend.parse(output) if backend else QuotaResult("unsupported")
            except TimeoutError:
                return QuotaResult("error", error="timeout")
            except Exception as exc:  # transport/parser isolation
                return QuotaResult("error", error=type(exc).__name__)
        future = self._executor.submit(run)
        self._pending[key] = future
        future.add_done_callback(lambda _: self._pending.pop(key, None))
        return future

    def invalidate(self, *, connection_id: str, provider_id: str, source_id: str, subject: str) -> None:
        key = (connection_id, provider_id, source_id, subject)
        self._generation[key] = self._generation.get(key, 0) + 1
        future = self._pending.pop(key, None)
        if future:
            future.cancel()

    def close(self) -> None:
        self._executor.shutdown(wait=False, cancel_futures=True)


def quota_gate(
    source: dict[str, Any] | None,
    *,
    backend_ids: Iterable[str] = (),
    consented: bool | None = None,
    connected: bool = False,
    subject_available: bool = True,
) -> str:
    """Return quota state without creating timers, transports, or processes."""
    if not isinstance(source, dict) or not str(source.get("command_template") or "").strip():
        return "not_configured"
    if source.get("enabled") is not True:
        return "disabled"
    scope = str(source.get("scope") or "").strip()
    if scope and scope not in KNOWN_QUOTA_SCOPES:
        return "invalid_configuration"
    backend_id = str(source.get("backend_id") or "").strip()
    if not backend_id or backend_id not in set(backend_ids) or not subject_available:
        return "incomplete/unsupported"
    if "\n" in str(source["command_template"]) or "\r" in str(source["command_template"]):
        return "invalid_configuration"
    if consented is None:
        consented = source.get("consent") is True
    if not consented:
        return "ready_not_enabled"
    return "eligible" if connected else "ready_not_enabled"


def quota_state_for_profile(
    profile: dict[str, Any] | None,
    *,
    backend_ids: Iterable[str] = (),
    connected: bool = False,
) -> str:
    """Evaluate the first stored provider quota source without side effects."""
    template = profile.get("provider_template") if isinstance(profile, dict) else None
    sources = template.get("quota_sources") if isinstance(template, dict) else None
    source = sources[0] if isinstance(sources, list) and sources and isinstance(sources[0], dict) else None
    return quota_gate(source, backend_ids=backend_ids, connected=connected)
