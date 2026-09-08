"""Framework-neutral dynamic output channel models and resolver.

Replaces the fixed two-slot output model with 0..N dynamic channels.
Every automatic channel has a stable ID.  Array-index identity is never
used as a public API.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
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
                        combined_label = f"{existing.label} + {defn.label_en}"
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

                label = defn.label_en
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
    ) -> list[ResolvedOutputChannel]:
        """Resolve using generic Slurm stdout/stderr semantics (no provider definitions)."""
        stdout_defn = OutputChannelDefinition(
            id="stdout", role="stdout", label_en="Standard Output",
            resolver="slurm.stdout", order=0,
        )
        stderr_defn = OutputChannelDefinition(
            id="stderr", role="stderr", label_en="Standard Error",
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
            )
        elif defn.resolver == "slurm.stderr":
            return self._resolve_slurm_stderr(
                job_id=job_id,
                workdir=workdir,
                scontrol_path=scontrol_stderr,
                scontrol_stdout=scontrol_stdout,
                script_text=script_text,
                script_remote_path=script_remote_path,
            )
        elif defn.resolver == "workdir.relative":
            if defn.relative_path and workdir:
                import posixpath
                resolved = _apply_placeholders(defn.relative_path, job_id)
                if not resolved.startswith("/"):
                    resolved = posixpath.join(workdir, resolved)
                resolved = posixpath.normpath(resolved)
                if not resolved.startswith(workdir.rstrip("/") + "/") and resolved != workdir.rstrip("/"):
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
                return (_resolve_from_dir(base, out, job_id), "script")
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
                return (_resolve_from_dir(base, err, job_id), "script")
        # 3. If no explicit stderr, it follows stdout in generic Slurm
        if scontrol_stdout:
            return (scontrol_stdout, "default")
        # Also check script stdout for fallback
        if script_text:
            out, _ = parse_output_error(script_text)
            if out:
                from hpc_gui.services.slurm_script_parser import _resolve_from_dir
                base = workdir or (script_remote_path.rsplit("/", 1)[0] if script_remote_path else ".")
                return (_resolve_from_dir(base, out, job_id), "default")
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
    streams = job_outputs.get("streams")
    if not isinstance(streams, list) or not streams:
        return []  # Explicit zero channels
    result: list[OutputChannelDefinition] = []
    for stream in streams:
        if not isinstance(stream, dict):
            continue
        sid = str(stream.get("id", "")).strip()
        role = str(stream.get("role", "")).strip()
        resolver = str(stream.get("resolver", "")).strip()
        if not sid or not role or resolver not in _RESOLVER_IDS:
            continue
        labels = stream.get("labels") or {}
        result.append(OutputChannelDefinition(
            id=sid,
            role=role,
            label_en=str(labels.get("en", sid)),
            label_tr=str(labels.get("tr", labels.get("en", sid))),
            resolver=resolver,
            order=int(stream.get("order", len(result))),
        ))
    return result
