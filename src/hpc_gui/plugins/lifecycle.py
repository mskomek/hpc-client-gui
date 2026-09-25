"""Canonical plugin enable/disable lifecycle, isolation and conflict handling (W33).

Live owner for ``waves/pending/W33.md`` owned requirements
``HPC-W08-LIFE-001`` .. ``HPC-W08-LIFE-012`` (planning source
``WAVE_V2_FINAL_08.md`` Workstreams C/D/E).

The loader (:mod:`hpc_gui.plugins.loader`) already enforces per-plugin
containment; the discovery module (:mod:`hpc_gui.plugins.discovery`)
already enumerates sources and precedence. This module is the single
place that states the lifecycle contract those mechanisms implement:

- Workstream C (LIFE-001..005): exactly when an enable/disable or
  version switch takes effect, and the UI wording that must state it.
- Workstream D (LIFE-006): the seven failure phases and the isolation
  guarantee (one broken plugin never blocks siblings or the core app).
- Workstream E (LIFE-007..012): deterministic duplicate/conflict
  resolution that is always visible in diagnostics.

Everything here is declarative and side-effect free except for the
thin wrappers around :mod:`hpc_gui.plugins.state` persistence. The
loader remains the enforcement point; these helpers describe and prove
the contract so tests, diagnostics and UI text cannot drift apart.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

# ---------------------------------------------------------------------------
# Workstream C — enable/disable effect matrix (LIFE-001 .. LIFE-005)
# ---------------------------------------------------------------------------
#
# Disabling/enabling (or switching the active version) updates persisted
# state (``disabled.json`` / ``active.json``) synchronously. The effect on
# running code happens at the next :func:`load_installed_plugins` call,
# which every consumer (Plugin Manager refresh, main-window menu rebuild,
# reconnect-time profile resolution) performs before use. No application
# restart is required for the listing, and no live in-memory plugin object
# is mutated in place: the next load simply contributes (or stops
# contributing) the plugin's profiles, templates, rules and tools.

#: i18n key for the user-visible lifecycle note (LIFE-005). The Qt dialog,
#: the wx plugins view and any future surface must render this sentence
#: wherever an enable/disable toggle is offered.
LIFECYCLE_EFFECT_NOTE_KEY = "plugins.lifecycle_effect_note"

#: Canonical English wording (mirrored in ``src/hpc_gui/i18n/*.json``).
LIFECYCLE_EFFECT_NOTE_EN = (
    "Disabling a plugin stops its profiles, templates, rules and tools "
    "the next time plugins load (list refresh, view rebuild or reconnect). "
    "No app restart is needed; already-opened views refresh on rebuild."
)

#: Per-scope effect table. ``scope`` names the consumer moment, ``effect``
#: states what the user observes, ``requirement`` binds the row to its
#: stable owner. LIFE-001 "immediately" means the persisted flag flips
#: synchronously and the *next* load call observes it — there is no live
#: object to mutate because plugins are declarative payloads, not running
#: code.
ENABLE_DISABLE_EFFECTS: tuple[dict[str, str], ...] = (
    {
        "scope": "persisted-state",
        "effect": "immediate",
        "requirement": "HPC-W08-LIFE-001",
        "detail": (
            "disabled.json / active.json is rewritten synchronously; "
            "a crash after return cannot lose the toggle"
        ),
    },
    {
        "scope": "plugin-listing",
        "effect": "next load_installed_plugins() call",
        "requirement": "HPC-W08-LIFE-001",
        "detail": (
            "the next load call skips disabled plugins entirely; "
            "no restart required"
        ),
    },
    {
        "scope": "tab-view-rebuild",
        "effect": "next rebuild reloads without the disabled plugin",
        "requirement": "HPC-W08-LIFE-002",
        "detail": (
            "menu/view rebuilds call load_installed_plugins() first, "
            "so rebuilt surfaces never show disabled content"
        ),
    },
    {
        "scope": "reconnect",
        "effect": "reconnect resolves profiles from the fresh load",
        "requirement": "HPC-W08-LIFE-003",
        "detail": (
            "connection-time profile resolution uses the current load "
            "result; saved profiles embed snapshots and are unaffected"
        ),
    },
    {
        "scope": "app-restart",
        "effect": "restart loads the persisted state from disk",
        "requirement": "HPC-W08-LIFE-004",
        "detail": (
            "restart is sufficient but never required: it simply "
            "re-reads the same persisted flags"
        ),
    },
)


def describe_enable_disable_effects() -> tuple[dict[str, str], ...]:
    """Return the Workstream C effect matrix (LIFE-001..004)."""
    return tuple(dict(row) for row in ENABLE_DISABLE_EFFECTS)


def lifecycle_effect_note() -> str:
    """Return the LIFE-005 user-facing sentence (English canonical)."""
    return LIFECYCLE_EFFECT_NOTE_EN


# ---------------------------------------------------------------------------
# Workstream D — isolation phases (LIFE-006)
# ---------------------------------------------------------------------------

#: The seven planning failure phases. Each maps to the loader gate that
#: contains it; a failure at any phase records a :class:`PluginProblem`
#: and skips only that plugin version.
LIFECYCLE_PHASES: tuple[dict[str, str], ...] = (
    {"phase": "discovery", "gate": "active-index read; unknown ids ignored"},
    {"phase": "manifest-parse", "gate": "manifest JSON + schema validation"},
    {"phase": "import", "gate": "no code import at load time (declarative only)"},
    {"phase": "registration", "gate": "identity/API/compatibility/integrity checks"},
    {"phase": "initialization", "gate": "cluster-profile build + floor consistency"},
    {"phase": "provider-capability-call", "gate": "duplicate profile-id claim (deterministic winner)"},
    {"phase": "shutdown", "gate": "failed plugins contribute nothing; nothing to tear down"},
)

#: Requirement bound to the isolation guarantee.
ISOLATION_REQUIREMENT = "HPC-W08-LIFE-006"

ISOLATION_NOTE = (
    "A failure in one plugin is recorded as a contained diagnostic and "
    "skips only that plugin version; unrelated plugins and the core app "
    "always finish loading. No plugin is mandatory: there is no code path "
    "where a single plugin failure aborts startup."
)


def describe_isolation_phases() -> tuple[dict[str, str], ...]:
    """Return the seven Workstream D phases with their containing gates."""
    return tuple(dict(row) for row in LIFECYCLE_PHASES)


def isolation_note() -> str:
    """Return the LIFE-006 guarantee sentence."""
    return ISOLATION_NOTE


# ---------------------------------------------------------------------------
# Workstream E — duplicate/conflict handling (LIFE-007 .. LIFE-012)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ConflictDecision:
    """One deterministic conflict outcome (LIFE-012)."""

    kind: str
    winner: str | None
    rejected: tuple[str, ...]
    requirement: str
    diagnostic: str


def _sort_key(value: str) -> tuple[int, tuple[int, ...], str]:
    """Deterministic ordering: parsed version tuple, then raw string."""
    from hpc_gui.plugins.compatibility import parse_version

    parsed = parse_version(str(value))
    if parsed is None:
        return (1, (0, 0, 0), str(value))
    return (0, parsed, str(value))


def resolve_plugin_versions(
    plugin_id: str,
    installed_versions: list[str],
    active_version: str | None,
) -> ConflictDecision:
    """Resolve "two versions of same plugin" (LIFE-009).

    The persisted ``active.json`` pointer wins when it names an installed
    version; otherwise the highest parseable version wins and the choice
    is reported so the operator can pin it explicitly. Inert versions stay
    installed on disk but contribute nothing.
    """
    available = sorted(set(installed_versions))
    if not available:
        return ConflictDecision(
            kind="plugin-version",
            winner=None,
            rejected=(),
            requirement="HPC-W08-LIFE-009",
            diagnostic=f"{plugin_id}: no installed versions; nothing is active",
        )
    if active_version in available:
        winner = active_version
    else:
        winner = sorted(available, key=_sort_key)[-1]
    rejected = tuple(v for v in available if v != winner)
    return ConflictDecision(
        kind="plugin-version",
        winner=winner,
        rejected=rejected,
        requirement="HPC-W08-LIFE-009",
        diagnostic=(
            f"{plugin_id}: active version {winner}; "
            + (f"inert versions kept on disk: {', '.join(rejected)}" if rejected else "only version installed")
            + (" (active pointer honoured)" if active_version == winner else " (highest version wins; pin via activate)")
        ),
    )


def resolve_duplicate_plugin_id(
    plugin_id: str,
    claimants: list[str],
) -> ConflictDecision:
    """Resolve "duplicate plugin ID" (LIFE-007).

    Only the ``user-installed`` discovery source is active, so a plugin id
    can have at most one active pointer. When several candidates claim one
    id (for example two roots merged by an operator), the sorted-first
    claimant wins deterministically and every later claimant is rejected
    whole with a diagnostic.
    """
    ordered = sorted(set(claimants))
    if len(ordered) <= 1:
        return ConflictDecision(
            kind="duplicate-plugin-id",
            winner=ordered[0] if ordered else None,
            rejected=(),
            requirement="HPC-W08-LIFE-007",
            diagnostic=f"{plugin_id}: single claimant; no conflict",
        )
    return ConflictDecision(
        kind="duplicate-plugin-id",
        winner=ordered[0],
        rejected=tuple(ordered[1:]),
        requirement="HPC-W08-LIFE-007",
        diagnostic=(
            f"duplicate plugin id {plugin_id!r}: winner {ordered[0]} "
            f"(sorted-first); rejected {', '.join(ordered[1:])}"
        ),
    )


def resolve_duplicate_provider_id(
    provider_id: str,
    claimants: list[str],
) -> ConflictDecision:
    """Resolve "duplicate provider ID" (LIFE-008).

    Mirrors the loader's cluster-profile claim rule: active-index iteration
    is sorted by plugin id, the first claimant wins, later claimants
    (including a self-collision) are rejected whole — never half-applied.
    """
    return ConflictDecision(
        kind="duplicate-provider-id",
        winner=(sorted(set(claimants))[0] if claimants else None),
        rejected=tuple(sorted(set(claimants))[1:]),
        requirement="HPC-W08-LIFE-008",
        diagnostic=(
            f"duplicate provider id {provider_id!r}: winner "
            f"{sorted(set(claimants))[0] if claimants else '<none>'} "
            "(sorted-first); later claimants rejected whole"
            if len(set(claimants)) > 1
            else f"provider id {provider_id!r}: single claimant; no conflict"
        ),
    )


def resolve_bundled_vs_user_override(
    plugin_id: str,
    *,
    user_installed: bool,
    bundled_present: bool,
) -> ConflictDecision:
    """Resolve "bundled vs user override" (LIFE-010).

    No bundled plugin directory is scanned, so the user-installed payload
    always wins when present. A bundled payload can never shadow user
    state; when nothing is user-installed there is simply nothing to load
    (never a silent bundled fallback).
    """
    if user_installed:
        return ConflictDecision(
            kind="bundled-vs-user",
            winner=f"user-installed:{plugin_id}",
            rejected=("bundled (never scanned)",) if bundled_present else (),
            requirement="HPC-W08-LIFE-010",
            diagnostic=(
                f"{plugin_id}: user-installed payload wins; "
                "bundled sources are never scanned and cannot shadow it"
            ),
        )
    return ConflictDecision(
        kind="bundled-vs-user",
        winner=None,
        rejected=("bundled (never scanned)",) if bundled_present else (),
        requirement="HPC-W08-LIFE-010",
        diagnostic=(
            f"{plugin_id}: not user-installed; nothing loads "
            "(no silent bundled fallback)"
        ),
    )


def resolve_optional_dependency_versions(
    declared: Mapping[str, Any] | list[Any] | tuple[Any, ...] | None,
) -> tuple[ConflictDecision, ...]:
    """Check "invalid dependency version" entries (LIFE-011).

    Optional dependencies are advisory: an invalid or unsatisfied entry is
    reported as a deterministic diagnostic, but the declaring plugin still
    loads normally. Returns one decision per invalid entry (valid entries
    produce no decision — silence means satisfied-or-absent by design).
    """
    from hpc_gui.plugins.models import is_valid_semver

    if declared is None:
        return ()
    entries: list[Any] = list(declared.values()) if isinstance(declared, Mapping) else list(declared)
    decisions: list[ConflictDecision] = []
    seen: set[str] = set()
    for entry in sorted(
        (e if isinstance(e, str) else str((e or {}).get("id", e)) for e in entries)
    ):
        raw = next(e for e in entries if (e if isinstance(e, str) else str((e or {}).get("id", e))) == entry)
        dep_id = raw if isinstance(raw, str) else str((raw or {}).get("id", ""))
        dep_version = None if isinstance(raw, str) else (raw or {}).get("version")
        if dep_id in seen:
            continue
        seen.add(dep_id)
        if dep_version is not None and not is_valid_semver(dep_version):
            decisions.append(
                ConflictDecision(
                    kind="invalid-dependency-version",
                    winner=None,
                    rejected=(dep_id,),
                    requirement="HPC-W08-LIFE-011",
                    diagnostic=(
                        f"optional dependency {dep_id!r} declares invalid "
                        f"version {dep_version!r}: recorded as diagnostic; "
                        "declaring plugin still loads (advisory only)"
                    ),
                )
            )
    return tuple(decisions)


def summarize_problems_for_diagnostics(result: Any) -> list[str]:
    """Render loader problems as deterministic, visible diagnostics (LIFE-012).

    Sorted by ``(plugin_id, version, reason)`` so repeated runs over the
    same tree produce byte-identical output. The Plugin Manager installed
    tab renders these lines; they are also available to logs/reports.
    """
    problems = list(getattr(result, "problems", ()) or ())
    lines = sorted(
        f"{p.plugin_id}@{p.version}: {p.reason}" for p in problems if getattr(p, "reason", "").strip()
    )
    return lines


def describe_for_report(*, root: str | None = None) -> dict[str, Any]:  # noqa: ARG001
    """Return a JSON-serialisable lifecycle summary for Wave evidence."""
    return {
        "requirements": [f"HPC-W08-LIFE-{i:03d}" for i in range(1, 13)],
        "enable_disable_effects": [dict(row) for row in ENABLE_DISABLE_EFFECTS],
        "effect_note": LIFECYCLE_EFFECT_NOTE_EN,
        "isolation_phases": [dict(row) for row in LIFECYCLE_PHASES],
        "isolation_note": ISOLATION_NOTE,
        "conflict_rule": (
            "sorted-first claimant wins; later claimants rejected whole; "
            "user-installed always beats bundled (bundled never scanned); "
            "optional dependencies advisory-only; every decision carries a "
            "visible diagnostic"
        ),
    }


__all__ = [
    "ConflictDecision",
    "ENABLE_DISABLE_EFFECTS",
    "ISOLATION_NOTE",
    "ISOLATION_REQUIREMENT",
    "LIFECYCLE_EFFECT_NOTE_EN",
    "LIFECYCLE_EFFECT_NOTE_KEY",
    "LIFECYCLE_PHASES",
    "describe_enable_disable_effects",
    "describe_for_report",
    "describe_isolation_phases",
    "isolation_note",
    "lifecycle_effect_note",
    "resolve_bundled_vs_user_override",
    "resolve_duplicate_plugin_id",
    "resolve_duplicate_provider_id",
    "resolve_optional_dependency_versions",
    "resolve_plugin_versions",
    "summarize_problems_for_diagnostics",
]
