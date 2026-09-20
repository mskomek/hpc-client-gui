"""Artifact identity helper (W14 / HPC-W04-IDENTITY-001..002).

Every package evidence log must begin with the six-line identity header so
any later code or packaging change (which changes the artifact hash)
explicitly invalidates evidence tied to the prior hash.
"""

from __future__ import annotations

IDENTITY_LABELS = (
    "Artifact",
    "SHA256",
    "Main SHA",
    "Plugin SHA",
    "Version",
    "OS/arch",
)


def format_artifact_identity(
    artifact: str,
    sha256: str,
    main_sha: str,
    plugin_sha: str,
    version: str,
    os_arch: str,
) -> str:
    """Return the canonical six-line identity header (no trailing newline)."""
    values = (artifact, sha256, main_sha, plugin_sha, version, os_arch)
    return "\n".join(f"{label}: {value}" for label, value in zip(IDENTITY_LABELS, values))


def parse_artifact_identity(header: str) -> dict[str, str]:
    """Parse a six-line identity header back into a label->value mapping."""
    parsed: dict[str, str] = {}
    for line in header.strip().splitlines():
        label, sep, value = line.partition(":")
        if not sep:
            raise ValueError(f"malformed identity line: {line!r}")
        parsed[label.strip()] = value.strip()
    missing = [label for label in IDENTITY_LABELS if label not in parsed]
    if missing:
        raise ValueError(f"identity header missing labels: {missing}")
    return parsed
