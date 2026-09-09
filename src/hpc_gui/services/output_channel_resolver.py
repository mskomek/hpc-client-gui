"""Framework-neutral dynamic output channel models and resolver.

Replaces the fixed two-slot output model with 0..N dynamic channels.
Every automatic channel has a stable ID.  Array-index identity is never
used as a public API.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
import re
from typing import Any, Mapping, Sequence

from hpc_gui.services.slurm_script_parser import parse_output_error


# ---------------------------------------------------------------------------
# Provider channel definition (declarative)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OutputChannelDefinition:
    """Declarative description of an automatic provider output stream.

    Providers declare which semantic output channels exist.  The application
    resolves the actual remote paths at runtime.
    """

    id: str
    role: str  # stdout | stderr | custom
    label_en: str
    label_tr: str = ""
    resolver: str = ""  # e.g. "slurm.stdout", "slurm.stderr"
    relative_path: str = ""
    order: int = 0


# ---------------------------------------------------------------------------
# Resolved output channel (runtime)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedOutputChannel:
    """A channel definition bound to one selected job with a concrete path."""

    id: str
    role: str
    label: str
    path: str
    source: str  # runtime | script | default
    roles: tuple[str, ...] = ()  # for dedup: (stdout, stderr) when same file
    definition: OutputChannelDefinition | None = None


# ---------------------------------------------------------------------------
# Tracked output (UI follower item)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrackedOutput:
    """A single tracked output item in the follower engine."""

    tracking_id: str
    channel_id: str | None
    label: str
    path: str
    origin: str  # automatic | manual
    job_id: str = ""


# ---------------------------------------------------------------------------
# Resolver whitelist
# ---------------------------------------------------------------------------

_RESOLVER_IDS = frozenset({"slurm.stdout", "slurm.stderr", "workdir.relative"})


# ---------------------------------------------------------------------------
# Output resolver
# ---------------------------------------------------------------------------

class OutputResolver:
    """Central application-owned resolver for output channel paths.

    Resolution order for each role:
    1. Runtime scontrol metadata (StdOut/StdErr)
    2. Script/provenance SBATCH directives
    3. Slurm defaults (slurm-%j.out / slurm-%j.err)

    Deduplication: if stdout and stderr resolve to the same physical file,
    a single combined channel is created.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()

    def resolve(
        self,
        definitions: Sequence[OutputChannelDefinition],
        *,
        job_id: str = "",
        workdir: str = "",
        scontrol_stdout: str = "",
        scontrol_stderr: str = "",
        script_text: str = "",
        script_remote_path: str = "",
        job_name: str = "",
        language: str = "en",
    ) -> list[ResolvedOutputChannel]:
        """Resolve all declared channels to concrete paths."""
        with self._lock:
            resolved: list[ResolvedOutputChannel] = []
            seen_paths: dict[str, ResolvedOutputChannel] = {}

            for defn in sorted(definitions, key=lambda d: (d.order, d.id)):
                path, source = self._resolve_one(
                    defn,
                    job_id=job_id,
                    workdir=workdir,
                    scontrol_stdout=scontrol_stdout,
                    scontrol_stderr=scontrol_stderr,
                    script_text=script_text,
                    script_remote_path=script_remote_path,
                    job_name=job_name,
                )
                if not path:
                    continue

                # Deduplication: same physical file -> combine roles
                if path in seen_paths:
                    existing = seen_paths[path]
                    combined_roles = tuple(
                        dict.fromkeys(existing.roles + (defn.role,))
                    )
                    combined_label = existing.label
                    if defn.role not in existing.roles:
                        combined_label = f"{existing.label} + {defn.label_tr if language == 'tr' and defn.label_tr else defn.label_en}"
                    deduped = ResolvedOutputChannel(
                        id=existing.id,
                        role=existing.role,
                        label=combined_label,
                        path=path,
                        source=source,
                        roles=combined_roles,
                        definition=existing.definition,
                    )
                    resolved = [d if d is not existing else deduped for d in resolved]
                    seen_paths[path] = deduped
                    continue

                label = defn.label_tr if language == "tr" and defn.label_tr else defn.label_en
                channel = ResolvedOutputChannel(
                    id=defn.id,
                    role=defn.role,
                    label=label,
                    path=path,
                    source=source,
                    roles=(defn.role,),
                    definition=defn,
                )
                resolved.append(channel)
                seen_paths[path] = channel

            return resolved

    def resolve_legacy(
        self,
        *,
        job_id: str = "",
        workdir: str = "",
        scontrol_stdout: str = "",
        scontrol_stderr: str = "",
        script_text: str = "",
        script_remote_path: str = "",
        job_name: str = "",
        language: str = "en",
    ) -> list[ResolvedOutputChannel]:
        """Resolve using generic Slurm stdout/stderr semantics (no provider definitions)."""
        stdout_defn = OutputChannelDefinition(
            id="stdout", role="stdout", label_en="Standard Output",
            label_tr="Standart \u00c7\u0131kt\u0131",
            resolver="slurm.stdout", order=0,
        )
        stderr_defn = OutputChannelDefinition(
            id="stderr", role="stderr", label_en="Standard Error",
            label_tr="Standart Hata",
            resolver="slurm.stderr", order=1,
        )
        return self.resolve(
            [stdout_defn, stderr_defn],
            job_id=job_id,
            workdir=workdir,
            scontrol_stdout=scontrol_stdout,
            scontrol_stderr=scontrol_stderr,
            script_text=script_text,
            script_remote_path=script_remote_path,
            job_name=job_name,
            language=language,
        )

    def _resolve_one(
        self,
        defn: OutputChannelDefinition,
        *,
        job_id: str = "",
        workdir: str = "",
        scontrol_stdout: str = "",
        scontrol_stderr: str = "",
        script_text: str = "",
        script_remote_path: str = "",
        job_name: str = "",
    ) -> tuple[str, str]:
        """Resolve one channel definition to (path, source)."""
        if defn.resolver not in _RESOLVER_IDS:
            return ("", "")

        if defn.resolver == "slurm.stdout":
            return self._resolve_slurm_stdout(
                job_id=job_id,
                workdir=workdir,
                scontrol_path=scontrol_stdout,
                script_text=script_text,
                script_remote_path=script_remote_path,
                job_name=job_name,
            )
        elif defn.resolver == "slurm.stderr":
            return self._resolve_slurm_stderr(
                job_id=job_id,
                workdir=workdir,
                scontrol_path=scontrol_stderr,
                scontrol_stdout=scontrol_stdout,
                script_text=script_text,
                script_remote_path=script_remote_path,
                job_name=job_name,
            )
        elif defn.resolver == "workdir.relative":
            if defn.relative_path and workdir:
                import posixpath
                relative = _apply_placeholders_with_name(defn.relative_path, job_id, job_name)
                if relative.startswith("/") or any(part == ".." for part in relative.split("/")):
                    return ("", "")
                root = posixpath.normpath(workdir)
                resolved = posixpath.normpath(posixpath.join(root, relative))
                if posixpath.commonpath((root, resolved)) != root:
                    return ("", "")
                return (resolved, "definition")
        return ("", "")

    def _resolve_slurm_stdout(
        self,
        *,
        job_id: str,
        workdir: str,
        scontrol_path: str,
        script_text: str,
        script_remote_path: str,
        job_name: str,
    ) -> tuple[str, str]:
        """Resolve Slurm stdout: scontrol -> script -> default."""
        # 1. Runtime scontrol
        if scontrol_path:
            return (scontrol_path, "runtime")
        # 2. Script SBATCH directives
        if script_text:
            out, _ = parse_output_error(script_text)
            if out:
                from hpc_gui.services.slurm_script_parser import _resolve_from_dir
                base = workdir or (script_remote_path.rsplit("/", 1)[0] if script_remote_path else ".")
                return (_resolve_from_dir(base, out, job_id, job_name), "script")
        # 3. Slurm default
        default = f"slurm-{job_id}.out" if job_id else "slurm.out"
        if workdir:
            import posixpath
            return (posixpath.join(workdir, default), "default")
        return (default, "default")

    def _resolve_slurm_stderr(
        self,
        *,
        job_id: str,
        workdir: str,
        scontrol_path: str,
        scontrol_stdout: str,
        script_text: str,
        script_remote_path: str,
        job_name: str,
    ) -> tuple[str, str]:
        """Resolve Slurm stderr: scontrol -> script -> follows stdout."""
        # 1. Runtime scontrol
        if scontrol_path:
            return (scontrol_path, "runtime")
        # 2. Script SBATCH directives
        if script_text:
            _, err = parse_output_error(script_text)
            if err:
                from hpc_gui.services.slurm_script_parser import _resolve_from_dir
                base = workdir or (script_remote_path.rsplit("/", 1)[0] if script_remote_path else ".")
                return (_resolve_from_dir(base, err, job_id, job_name), "script")
        # 3. If no explicit stderr, it follows stdout in generic Slurm
        if scontrol_stdout:
            return (scontrol_stdout, "default")
        # Also check script stdout for fallback
        if script_text:
            out, _ = parse_output_error(script_text)
            if out:
                from hpc_gui.services.slurm_script_parser import _resolve_from_dir
                base = workdir or (script_remote_path.rsplit("/", 1)[0] if script_remote_path else ".")
                return (_resolve_from_dir(base, out, job_id, job_name), "default")
        # 4. Default: stderr follows stdout
        default = f"slurm-{job_id}.out" if job_id else "slurm.out"
        if workdir:
            import posixpath
            return (posixpath.join(workdir, default), "default")
        return (default, "default")


# ---------------------------------------------------------------------------
# Placeholder resolution
# ---------------------------------------------------------------------------

def _apply_placeholders(value: str, job_id: str) -> str:
    """Apply Slurm-style placeholders to a path template."""
    if not job_id:
        return value
    master_id, _, array_id = job_id.partition("_")
    value = value.replace("%j", job_id).replace("%J", job_id)
    value = value.replace("%A", master_id)
    if array_id:
        value = value.replace("%a", array_id)
    return value


def _apply_placeholders_with_name(value: str, job_id: str, job_name: str = "") -> str:
    """Apply Slurm-style placeholders including %x (job name)."""
    value = _apply_placeholders(value, job_id)
    if job_name:
        value = value.replace("%x", job_name)
    return value


# ---------------------------------------------------------------------------
# Provider definitions helpers
# ---------------------------------------------------------------------------

def definitions_from_provider(
    job_outputs: Mapping[str, Any] | None,
) -> list[OutputChannelDefinition] | None:
    """Parse a provider's ``job_outputs`` section into channel definitions.

    Returns ``None`` if the field is absent (legacy provider — caller should
    use resolve_legacy()).
    Returns an empty list if ``streams`` is explicitly empty (no channels).
    """
    if job_outputs is None:
        return None  # Legacy: caller should use resolve_legacy()
    if not isinstance(job_outputs, Mapping):
        return []  # Explicit zero channels
    streams = job_outputs.get("streams")
    if not isinstance(streams, list) or not streams:
        return []  # Explicit zero channels
    if len(streams) > 50:
        return []
    result: list[OutputChannelDefinition] = []
    seen: set[str] = set()
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        sid_value = stream.get("id")
        role_value = stream.get("role")
        resolver_value = stream.get("resolver")
        if not all(isinstance(value, str) for value in (sid_value, role_value, resolver_value)):
            continue
        sid = sid_value.strip()
        role = role_value.strip()
        resolver = resolver_value.strip()
        if not sid or not re.fullmatch(r"^[a-z][a-z0-9_-]{0,63}$", sid) or sid in seen or role not in {"stdout", "stderr", "custom"} or resolver not in _RESOLVER_IDS:
            continue
        labels = stream.get("labels") or {}
        if not isinstance(labels, Mapping) or set(labels) - {"en", "tr"} or not isinstance(labels.get("en"), str) or not labels["en"].strip() or len(labels["en"]) > 128:
            continue
        if "tr" in labels and (not isinstance(labels["tr"], str) or not labels["tr"].strip() or len(labels["tr"]) > 128):
            continue
        if "order" not in stream or not isinstance(stream["order"], int) or isinstance(stream["order"], bool) or not 0 <= stream["order"] <= 100000:
            continue
        relative_value = stream.get("relative_path", "")
        if relative_value is not None and not isinstance(relative_value, str):
            continue
        relative_path = (relative_value or "").strip()
        if resolver != "workdir.relative" and relative_path:
            continue
        if resolver == "workdir.relative" and (
            not relative_path
            or relative_path.startswith("/")
            or "\\" in relative_path
            or any(part in {"", ".", ".."} for part in relative_path.split("/"))
        ):
            continue
        try:
            order = stream["order"]
        except (KeyError, TypeError, ValueError):
            continue
        result.append(OutputChannelDefinition(
            id=sid,
            role=role,
            label_en=str(labels.get("en", sid)),
            label_tr=str(labels.get("tr", labels.get("en", sid))),
            resolver=resolver,
            relative_path=relative_path,
            order=order,
        ))
        seen.add(sid)
    return result
