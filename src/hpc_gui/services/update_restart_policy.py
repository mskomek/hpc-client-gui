"""W43 — Updater restart, package validation and signing policy.

Owned requirements: HPC-W09-UPD-039..043, 053..055, 068..069, 079..081,
086..088, HPC-W09-PKGUPD-001..002, HPC-W09-TODO-058.

Semantics (authoritative for W43):
- Restart is USER-CONFIRMED, never automatic. The ready dialog offers
  ``Later`` (defer) and ``Install Update`` (explicit confirm).
- Install defers while any editor document is unsaved (dirty). The dialog
  blocks silent install: with N>0 unsaved documents it asks for explicit
  confirmation and stays in READY when the user declines. Nothing is
  installed, closed, or discarded on defer.
- Post-update version is confirmed by exact version equality between the
  expected release version and the installed/reported version.
- Package validation uses the exact artifact under acceptance
  (``verify_artifact`` size + SHA-256 on the exact ``zip_path``); a test
  channel/mock endpoint must exercise the same production
  verification/install code path (``download_and_verify_release`` /
  ``launch_update_installer``), never a parallel unverified path.
- Windows public release is UNSIGNED with documented policy
  (``docs/VERIFYING_RELEASES.md`` §5: "Authenticode signing is not enabled
  yet"). No code path may claim a signed Windows build.
"""

from __future__ import annotations

from typing import Callable, Iterable, Sequence

RESTART_MODE = "user-confirmed"

WINDOWS_SIGNING_STATUS = "unsigned"
WINDOWS_SIGNING_AUTHENTICODE_ENABLED = False
WINDOWS_SIGNING_USER_MESSAGE = (
    "Authenticode signing is not enabled yet. Windows may show a "
    'SmartScreen/"unknown publisher" prompt; SHA-256 and GitHub provenance '
    "are the supported verification path today."
)


_unsaved_providers: list[Callable[[], int]] = []


def restart_mode() -> str:
    """Return the W43 restart mode (always user-confirmed)."""
    return RESTART_MODE


def count_unsaved(documents: Iterable[object] | None) -> int:
    """Count dirty editor documents in *documents*.

    A document counts as unsaved when it exposes a truthy ``dirty``
    attribute. Anything without that attribute is ignored (never counted as
    dirty by accident).
    """
    total = 0
    for doc in documents or ():
        try:
            if bool(getattr(doc, "dirty", False)):
                total += 1
        except Exception:
            continue
    return total


def has_unsaved_changes(documents: Iterable[object] | None) -> bool:
    """Return True when at least one document is unsaved."""
    return count_unsaved(documents) > 0


def should_defer_install(documents: Iterable[object] | None) -> bool:
    """Return True when install must defer until safe shutdown (dirty>0)."""
    return has_unsaved_changes(documents)


def deferral_message(count: int) -> str:
    """User-facing deferral/confirmation message for *count* unsaved docs."""
    n = max(0, int(count))
    noun = "document" if n == 1 else "documents"
    return (
        f"You have {n} unsaved {noun}. "
        "Installing the update restarts the application. "
        "Choose Later to save your work first, or confirm to install anyway. "
        "The update will never install silently while unsaved work exists."
    )


def verify_post_update_version(installed: str, expected: str) -> bool:
    """Confirm post-update version by exact (whitespace-trimmed) equality."""
    return str(installed or "").strip() == str(expected or "").strip() and bool(
        str(expected or "").strip()
    )


def register_unsaved_provider(fn: Callable[[], int]) -> Callable[[], int]:
    """Register a process-wide unsaved-count provider (editor integration)."""
    _unsaved_providers.append(fn)
    return fn


def unregister_unsaved_provider(fn: Callable[[], int]) -> None:
    """Remove a previously registered unsaved-count provider."""
    try:
        _unsaved_providers.remove(fn)
    except ValueError:
        pass


def clear_unsaved_providers() -> None:
    """Remove all registered providers (tests only)."""
    _unsaved_providers.clear()


def get_unsaved_count() -> int:
    """Aggregate registered provider counts (0 when none registered)."""
    total = 0
    for fn in list(_unsaved_providers):
        try:
            value = int(fn() or 0)
        except Exception:
            continue
        if value > 0:
            total += value
    return max(0, total)


def windows_signing_policy() -> dict:
    """Return the W43 Windows signing policy (unsigned with documentation)."""
    return {
        "status": WINDOWS_SIGNING_STATUS,
        "authenticode_enabled": WINDOWS_SIGNING_AUTHENTICODE_ENABLED,
        "user_message": WINDOWS_SIGNING_USER_MESSAGE,
        "policy_doc": "docs/VERIFYING_RELEASES.md",
    }


def handoff_payload(
    *,
    settings_schema_version: str,
    migration_coverage: Sequence[str],
    verification_evidence: str,
    packaging_requirements: str,
) -> dict:
    """Build the W10 handoff payload (UPD-088) carried by the W43 report."""
    return {
        "settings_schema_version": str(settings_schema_version),
        "migration_coverage": [str(item) for item in migration_coverage],
        "verification_evidence": str(verification_evidence),
        "packaging_requirements": str(packaging_requirements),
    }
