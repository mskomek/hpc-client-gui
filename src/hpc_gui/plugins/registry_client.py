"""Official plugin registry endpoints, size limits, and fetch logic.

Endpoints live here and only here; the rest of the application must not
hardcode registry URLs. Normal UI never exposes arbitrary registry sources
in Plugin API v1.

All functions are synchronous and UI-independent: callers (Plugin Manager,
Wave 05+) are responsible for running them off the GUI thread.
"""

from __future__ import annotations

import hashlib
import json
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlsplit

from packaging.version import InvalidVersion, Version

from hpc_gui import __version__
from hpc_gui.plugins.compatibility import is_app_compatible
from hpc_gui.plugins.storage import plugins_root
from hpc_gui.plugins.validator import validate_registry_dict

OFFICIAL_REGISTRY_URL = (
    "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/registry.json"
)
OFFICIAL_RAW_BASE = (
    "https://raw.githubusercontent.com/mskomek/hpc-client-gui-plugins/main/"
)

# Response/resource limits (bytes / counts). Kept deliberately small for v1.
REGISTRY_MAX_BYTES = 1 * 1024 * 1024
MANIFEST_MAX_BYTES = 256 * 1024
FILE_MAX_BYTES = 5 * 1024 * 1024
PLUGIN_VERSION_MAX_BYTES = 25 * 1024 * 1024
PLUGIN_MAX_FILE_COUNT = 256

FetchFn = Callable[[str, int], bytes]

DEFAULT_TIMEOUT_SECONDS = 30.0

# After redirects the final response must still come from an official host
# over HTTPS. Redirects to any other host (even https://) are refused.
ALLOWED_FINAL_HOSTS = frozenset({"raw.githubusercontent.com"})


class RegistryError(RuntimeError):
    """Raised when the official registry cannot be fetched or trusted."""


def _final_url_is_allowed(final_url: object) -> bool:
    if not isinstance(final_url, str):
        return True  # fetchers without redirect introspection; scheme checked by caller
    parts = urlsplit(final_url)
    if parts.scheme != "https":
        return False
    return (parts.hostname or "").lower() in ALLOWED_FINAL_HOSTS


def default_fetcher(url: str, max_bytes: int) -> bytes:
    """Fetch ``url`` over HTTPS with a hard response-size cap."""
    request = urllib.request.Request(
        url,
        headers={"User-Agent": f"HPC-Client-GUI/{__version__}"},
    )
    with urllib.request.urlopen(request, timeout=DEFAULT_TIMEOUT_SECONDS) as response:
        final_url = getattr(response, "geturl", lambda: url)()
        if not _final_url_is_allowed(final_url):
            raise RegistryError(
                "Refusing insecure HTTP redirect or unexpected final host."
            )
        payload = response.read(max_bytes + 1)
    if len(payload) > max_bytes:
        raise RegistryError(f"Response from {url} exceeds the size limit.")
    return payload


@dataclass(frozen=True)
class RegistryFetchResult:
    registry: dict[str, Any]
    source: str  # "network" | "cache"
    fetched_at: str


def parse_registry(payload: bytes) -> dict[str, Any]:
    """Parse and validate raw registry bytes; raises RegistryError."""
    try:
        registry = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RegistryError(f"Registry is not valid UTF-8 JSON: {exc}") from exc
    problems = validate_registry_dict(registry)
    if problems:
        raise RegistryError("Invalid registry: " + "; ".join(problems))
    return registry


def _cache_paths(root: str | Path | None) -> tuple[Path, Path]:
    base = Path(plugins_root(root)) / "cache"
    return base / "registry.json", base / "metadata.json"


def read_cached_registry(root: str | Path | None = None) -> dict[str, Any] | None:
    """Return the last-known-good cached registry, if present and valid."""
    cache_path, _ = _cache_paths(root)
    try:
        payload = cache_path.read_bytes()
    except OSError:
        return None
    try:
        return parse_registry(payload)
    except RegistryError:
        return None


def fetch_registry_with_cache(
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    root: str | Path | None = None,
    fetcher: FetchFn | None = None,
    now: Callable[[], str] | None = None,
) -> RegistryFetchResult:
    """Fetch the official registry; fall back to the last-known-good cache.

    A network failure never corrupts or replaces a good cache. When neither
    network nor cache is available, RegistryError is raised (callers must
    keep the app running).
    """
    fetch = fetcher or (lambda url, limit: default_fetcher(url, limit))
    timestamp = (now or (lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))()

    try:
        payload = fetch(OFFICIAL_REGISTRY_URL, REGISTRY_MAX_BYTES)
        registry = parse_registry(payload)
    except Exception as exc:
        cached = read_cached_registry(root)
        if cached is not None:
            return RegistryFetchResult(registry=cached, source="cache", fetched_at=timestamp)
        raise RegistryError(f"Cannot reach the official plugin registry: {exc}") from exc

    cache_path, metadata_path = _cache_paths(root)
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = cache_path.with_suffix(".json.part")
        temporary.write_bytes(payload)
        temporary.replace(cache_path)
        metadata_path.write_text(
            json.dumps(
                {
                    "fetched_at": timestamp,
                    "source_url": OFFICIAL_REGISTRY_URL,
                    "sha256": hashlib.sha256(payload).hexdigest(),
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
    except OSError:
        # Cache write failures are non-fatal: the network copy is still valid.
        pass

    return RegistryFetchResult(registry=registry, source="network", fetched_at=timestamp)


def find_registry_entry(
    registry: dict[str, Any],
    plugin_id: str,
    version: str | None = None,
    app_version: str | None = None,
) -> dict[str, Any]:
    """Resolve one validated registry entry by id.

    With ``version`` the exactly matching entry is returned. Without a
    version, the highest semantic version wins (PEP 440 ordering via
    ``packaging.version.Version``); registry order never matters. When
    ``app_version`` is supplied, entries whose ``requires_app`` range does
    not admit that release are skipped so a newer incompatible version
    never shadows an older compatible one.
    """
    matches = [
        entry
        for entry in registry.get("plugins", [])
        if isinstance(entry, dict) and entry.get("id") == plugin_id
    ]
    if not matches:
        raise RegistryError(f"Plugin not found in the official registry: {plugin_id}")

    by_version: dict[str, dict[str, Any]] = {}
    for entry in matches:
        raw = entry.get("version")
        if not isinstance(raw, str) or not raw:
            raise RegistryError(f"Registry entry for {plugin_id} has no valid version.")
        if raw in by_version:
            raise RegistryError(
                f"Duplicate registry entries for {plugin_id} {raw}."
            )
        try:
            parsed = Version(raw)
        except InvalidVersion as exc:
            raise RegistryError(
                f"Registry version '{raw}' for {plugin_id} is not a valid "
                f"PEP 440 version."
            ) from exc
        by_version[raw] = (parsed, entry)

    def _compatible(entry: dict[str, Any]) -> bool:
        if app_version is None:
            return True
        return is_app_compatible(str(entry.get("requires_app", "")), app_version)

    if version is not None:
        found = by_version.get(version)
        if found is None:
            raise RegistryError(
                f"Plugin version not found in the official registry: "
                f"{plugin_id} {version}"
            )
        return found[1]

    candidates = [(parsed, entry) for parsed, entry in by_version.values() if _compatible(entry)]
    if not candidates:
        raise RegistryError(
            f"No version of {plugin_id} is compatible with app {app_version}."
        )
    # Stable releases win over prereleases (pip-like policy); a prerelease
    # is only chosen when no stable version is compatible.
    stable = [item for item in candidates if not item[0].is_prerelease]
    pool = stable or candidates
    return max(pool, key=lambda item: item[0])[1]
