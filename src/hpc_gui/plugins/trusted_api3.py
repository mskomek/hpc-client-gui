"""Application-owned trust contract for Plugin API v3 OpenFOAM packages.

Phase A scoped host trust for the two verified OpenFOAM package identities
(exact dotted IDs -- never short names):

- ``org.hpcclient.openfoamlint`` lineage (exact dotted ID; executable
  payload allowed only for the code-pinned W65 R18 candidate with a
  host pin -- publisher ``HPC Client GUI``, ``plugin_api`` 3,
  capabilities ``["linter-tool"]``, entrypoint
  ``{"linter_engine": "engine/openfoam_lint/__init__.py"}``, payload role
  ``linter-engine`` (.py only); the shipped ``0.2.0-w65r17-auditfix1``
  tree stays API 2 and unchanged).
- ``org.hpcclient.openfoamcasestudio`` lineage (exact dotted ID;
  application-engine payload allowed only with an exact host pin --
  publisher ``HPC Client GUI``, ``plugin_api`` 3, capabilities
  ``["application-tools"]``, entrypoint
  ``{"application_tool": "engine/openfoam_studio/__init__.py"}``, payload role
  ``application-engine`` (.py only); the shipped ``0.3.0-w65r17-auditfix1``
  tree stays API 2 and unchanged).

The auditfix1 versions remain API 2 and unchanged. The R18 candidate
versions are separately versioned and pinned by the application-owned
``api3-release-pins.json`` package data.

A manifest self-claim grants nothing. Trust requires ALL of the following
from application-owned data (never from the package under review):

1. exact plugin ``id`` AND exact ``version`` present in the host pin table;
2. exact ``publisher``, exact ``plugin_api`` (3), exact ``capabilities``,
   exact ``entrypoints`` and exact file ``(path, role, sha256)`` contract;
3. executable payload bytes hash-equal to the pinned SHA-256 values, and the
   canonical manifest digest hash-equal to the pinned manifest SHA-256,
   both recomputed from bytes on disk immediately before use.

Checking only the hashes declared inside the untrusted manifest is NOT
sufficient; the byte checks in :func:`api3_integrity_error` compare actual
bytes against host pins. An empty or unavailable pin fails closed.

There is intentionally NO generic Python loader here. The only executable
entrypoints are the exact OpenFOAM Linter and Case Studio identities above.
Their bounded loaders call :func:`api3_error_for_dir` before import and
execute only exact bytes verified against the pin (``compile`` + ``exec``
on no-follow reads, never a re-read from disk).
``sys.path``/CWD trust is never added. Pinned sibling modules are served
lazily from verified bytes through a scoped private-namespace finder;
anything unpinned fails closed.

Host process execution is NOT an OS sandbox: verified hashes attest to file
content only. They do not isolate the engine from the host process, the
filesystem, or the network. Treat an approved engine as host-process code
with the user's privileges.

Only the two R18 candidate versions in the host-owned pin file are approved.
Every other API v3 package is rejected at validation, install, load and
dispatch time. Never populate pins from package-provided hashes or persist
a private signing key in this tree. Tests may replace the table with
``monkeypatch``; production loads the immutable application-owned table.

The Linter identity may carry only ``linter-engine``; the Studio identity
may carry only ``application-engine`` plus the JSON-only
``application-catalog`` data role. Both exact entrypoints and every catalog
byte are pinned.
Pin paths are validated as safe package-relative POSIX paths before any
filesystem access (no absolute paths, drive prefixes, backslashes,
NUL/control chars, empty/dot/dotdot segments, or URL schemes), and
payload ``(suffix, role)`` combinations are narrow: ``linter-engine``
requires ``.py`` and is allowed only for the linter identity; every other
pinned payload must use a declarative suffix (``.json``/``.md``/``.txt``/
``.tpl``). Symlinks/reparse points are rejected for the package root, the
manifest, every payload, and every path component; reads use ``O_NOFOLLOW``
where the OS supports it so hashing never follows a link.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from hpc_gui.plugins._api3_release_pins import Api3Pin, load_application_release_pins
from hpc_gui.plugins._api3_files import (
    api3_components_have_links,
    api3_pin_path_error,
    is_api3_link,
    read_verified_bytes,
    sha_of_nofollow,
)

TRUSTED_API3_VERSION = 3
TRUSTED_API3_PUBLISHER = "HPC Client GUI"

# Exact verified identities (dotted reverse-DNS; short names are rejected).
API3_LINTER_ID = "org.hpcclient.openfoamlint"
API3_LINTER_VERSION = "0.2.1-w65r18.20261026.2"
API3_STUDIO_ID = "org.hpcclient.openfoamcasestudio"
API3_STUDIO_VERSION = "0.3.1-w65r18.20261026.2"

API3_LINTER_ENTRYPOINT = "engine/openfoam_lint/__init__.py"
API3_STUDIO_TEMPLATES_ENTRYPOINT = "templates/index.json"

# The two verified OpenFOAM package identities (id, exact version) that
# Phase A trusts only these exact code-pinned release versions.
OPENFOAM_API3_IDENTITIES = (
    (API3_LINTER_ID, API3_LINTER_VERSION),
    (API3_STUDIO_ID, API3_STUDIO_VERSION),
)

# The exact executable role and entrypoint type per application-owned identity.
_API3_EXECUTABLE_ROLES = {
    API3_LINTER_ID: ("linter-engine", "linter_engine"),
    API3_STUDIO_ID: ("application-engine", "application_tool"),
}

__all__ = [
    "api3_pin_path_error",
    "is_api3_link",
    "api3_components_have_links",
    "read_verified_bytes",
    "sha_of_nofollow",
]

RELEASE_PIN_BLOCKER = (
    "the exact identity and version are not in the application-owned "
    "release pin table (package-provided hashes can never substitute)"
)


APPROVED_API3_PINS: Mapping[tuple[str, str], Api3Pin] = load_application_release_pins(
    Path(__file__).with_name("api3-release-pins.json"),
    expected={
        (API3_LINTER_ID, API3_LINTER_VERSION): (
            ("linter-tool",),
            (("linter_engine", API3_LINTER_ENTRYPOINT),),
            "linter-engine",
        ),
        (API3_STUDIO_ID, API3_STUDIO_VERSION): (
            ("application-tools", "job-template"),
            (
                ("application_tool", "engine/openfoam_studio/__init__.py"),
                ("job_templates", API3_STUDIO_TEMPLATES_ENTRYPOINT),
            ),
            "application-engine",
        ),
    },
    publisher=TRUSTED_API3_PUBLISHER,
    api=TRUSTED_API3_VERSION,
    validate_path_role=api3_pin_path_error,
)


def api3_pin_for(
    plugin_id: Any,
    version: Any,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> Api3Pin | None:
    """Return the host pin for an exact (id, version), or None."""
    table = APPROVED_API3_PINS if pins is None else pins
    if not isinstance(plugin_id, str) or not isinstance(version, str):
        return None
    return table.get((plugin_id, version))


def _manifest_view(manifest: Any) -> dict[str, Any]:
    """Normalize a raw manifest dict or PluginManifest to plain data."""
    if isinstance(manifest, Mapping):
        raw_id = manifest.get("id")
        raw_version = manifest.get("version")
        raw_publisher = manifest.get("publisher")
        raw_api = manifest.get("plugin_api")
        raw_caps = manifest.get("capabilities", ())
        raw_eps = manifest.get("entrypoints", {})
        raw_files = manifest.get("files", ())
    else:
        raw_id = getattr(manifest, "id", None)
        raw_version = getattr(manifest, "version", None)
        raw_publisher = getattr(manifest, "publisher", None)
        raw_api = getattr(manifest, "plugin_api", None)
        raw_caps = getattr(manifest, "capabilities", ())
        raw_eps = getattr(manifest, "entrypoints", {})
        raw_files = getattr(manifest, "files", ())
    files: list[tuple[Any, Any, Any]] = []
    for entry in raw_files or ():
        if isinstance(entry, Mapping):
            files.append((entry.get("path"), entry.get("role"), entry.get("sha256")))
        else:
            files.append((getattr(entry, "path", None), getattr(entry, "role", None),
                          getattr(entry, "sha256", None)))
    return {
        "id": raw_id,
        "version": raw_version,
        "publisher": raw_publisher,
        "plugin_api": raw_api,
        "capabilities": tuple(raw_caps) if isinstance(raw_caps, (list, tuple)) else raw_caps,
        "entrypoints": dict(raw_eps) if isinstance(raw_eps, Mapping) else raw_eps,
        "files": files,
    }


def api3_static_error(
    manifest: Any,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> str | None:
    """Check the API 3 identity/contract against host pins (no bytes read).

    Compares manifest-declared values to the host pin. A passing static
    check grants no trust by itself: callers must still verify actual
    payload bytes with :func:`api3_integrity_error` (or
    :func:`api3_error_for_dir`) before import/dispatch.
    """
    view = _manifest_view(manifest)
    if view["plugin_api"] != TRUSTED_API3_VERSION:
        return f"plugin_api 3 contract requires plugin_api {TRUSTED_API3_VERSION}"
    pin = api3_pin_for(view["id"], view["version"], pins=pins)
    if pin is None:
        return (
            f"no host release pin for {view['id']!r}@{view['version']!r} "
            f"({RELEASE_PIN_BLOCKER})"
        )
    if view["publisher"] != pin.publisher:
        return "plugin_api 3 publisher is not application-approved"
    allowed_role, allowed_entrypoint = _API3_EXECUTABLE_ROLES.get(view["id"], (None, None))
    executable_keys = {"linter_engine", "application_tool"}
    if executable_keys.intersection(view["entrypoints"]) - {allowed_entrypoint}:
        return f"plugin_api 3 identity {view['id']!r} has an unapproved executable entrypoint"
    for _path, role, _sha in view["files"]:
        if role in {"linter-engine", "application-engine"} and role != allowed_role:
            return f"plugin_api 3 identity {view['id']!r} may not carry payload role {role!r}"
    if not isinstance(view["capabilities"], tuple):
        return "plugin_api 3 capabilities must be a list"
    if sorted(view["capabilities"]) != sorted(pin.capabilities):
        return "plugin_api 3 capabilities are not application-approved"
    if not isinstance(view["entrypoints"], dict):
        return "plugin_api 3 entrypoints must be an object"
    if dict(view["entrypoints"]) != dict(pin.entrypoints):
        return "plugin_api 3 entrypoints are not application-approved"
    for path, role, _sha in pin.files:
        problem = api3_pin_path_error(path, role)
        if problem:
            return f"host release pin carries an unsafe payload path: {problem}"
    pinned_files = {(path, role, sha) for path, role, sha in pin.files}
    if set(view["files"]) != pinned_files:
        return "plugin_api 3 payload contract does not match the host release pin"
    return None


def api3_integrity_error(
    manifest: Any,
    *,
    actual_files: Mapping[str, str] | None,
    actual_manifest_sha: str | None,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> str | None:
    """Check actual payload bytes against host pins. Fails closed always."""
    view = _manifest_view(manifest)
    pin = api3_pin_for(view["id"], view["version"], pins=pins)
    if pin is None:
        return (
            f"no host release pin for {view['id']!r}@{view['version']!r} "
            f"({RELEASE_PIN_BLOCKER})"
        )
    if not pin.manifest_sha256:
        return f"host release pin for {view['id']!r}@{view['version']!r} has no manifest digest"
    if not actual_manifest_sha:
        return "executable integrity evidence unavailable (fail closed)"
    if actual_manifest_sha != pin.manifest_sha256:
        return "manifest digest does not match the host release pin"
    if not isinstance(actual_files, Mapping):
        return "executable integrity evidence unavailable (fail closed)"
    pinned_paths = {path for path, _role, _sha in pin.files}
    if set(actual_files) != pinned_paths:
        return "installed payload set does not match the host release pin"
    for path, _role, expected_sha in pin.files:
        if actual_files[path] != expected_sha:
            return f"payload integrity mismatch for {path!r}"
    return None


def api3_error(
    manifest: Any,
    *,
    actual_files: Mapping[str, str] | None = None,
    actual_manifest_sha: str | None = None,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> str | None:
    """Full API 3 gate: static contract plus byte integrity (fail closed)."""
    static = api3_static_error(manifest, pins=pins)
    if static is not None:
        return static
    if actual_files is None or actual_manifest_sha is None:
        return "executable integrity evidence unavailable (fail closed)"
    return api3_integrity_error(
        manifest,
        actual_files=actual_files,
        actual_manifest_sha=actual_manifest_sha,
        pins=pins,
    )


def api3_error_for_dir(
    manifest: Any,
    package_dir: str | Path,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> str | None:
    """Full API 3 gate for an on-disk package directory (no import).

    Recomputes the manifest digest and every payload hash from bytes on
    disk with link rejection and no-follow reads, validates every pin path
    before filesystem access, and rejects unexpected extra files, before any
    payload may be imported or dispatched.
    """
    static = api3_static_error(manifest, pins=pins)
    if static is not None:
        return static
    view = _manifest_view(manifest)
    pin = api3_pin_for(view["id"], view["version"], pins=pins)
    if pin is None:  # pragma: no cover - static already failed without a pin
        return "no host release pin (fail closed)"
    for path, role, _sha in pin.files:
        problem = api3_pin_path_error(path, role)
        if problem:
            return f"host release pin carries an unsafe payload path: {problem}"
    base = Path(package_dir)
    try:
        if is_api3_link(base):
            return "plugin_api 3 package directory is a link"
        manifest_path = base / "manifest.json"
        if is_api3_link(manifest_path):
            return "plugin_api 3 manifest is a link"
        actual_manifest_sha = sha_of_nofollow(manifest_path)
    except OSError as exc:
        return f"plugin_api 3 package is unreadable: {exc}"
    actual_files: dict[str, str] = {}
    try:
        for path, _role, _sha in pin.files:
            if api3_components_have_links(base, path):
                return f"plugin_api 3 payload is a link: {path}"
            actual_files[path] = sha_of_nofollow(base / path)
        for existing in base.rglob("*"):
            try:
                if is_api3_link(existing):
                    return f"plugin_api 3 link payload is forbidden: {existing.name}"
            except OSError:
                return f"plugin_api 3 package is unreadable: {existing}"
            if not existing.is_file():
                continue
            rel = existing.relative_to(base).as_posix()
            if rel != "manifest.json" and rel not in actual_files:
                return f"unexpected extra file in plugin_api 3 package: {rel}"
    except OSError as exc:
        return f"plugin_api 3 package is unreadable: {exc}"
    return api3_integrity_error(
        manifest,
        actual_files=actual_files,
        actual_manifest_sha=actual_manifest_sha,
        pins=pins,
    )


def api3_verified_sources(
    manifest: Any,
    package_dir: str | Path,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> dict[str, bytes]:
    """Return exact verified bytes for every pinned payload (fail closed).

    Each payload is read once with link rejection and no-follow semantics
    and hash-checked against the host pin. Callers must execute/import ONLY
    these bytes (``compile`` + ``exec``) and never re-read the same paths
    from disk, closing the hash-to-import race. Raises ``OSError`` when the
    gate fails.
    """
    reason = api3_error_for_dir(manifest, package_dir, pins=pins)
    if reason:
        raise OSError(reason)
    view = _manifest_view(manifest)
    pin = api3_pin_for(view["id"], view["version"], pins=pins)
    if pin is None:  # pragma: no cover - gate already failed without a pin
        raise OSError("no host release pin (fail closed)")
    base = Path(package_dir)
    sources: dict[str, bytes] = {}
    for path, _role, expected_sha in pin.files:
        sources[path] = read_verified_bytes(base, path, expected_sha)
    return sources


def api3_linter_entrypoint(
    manifest: Any,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> str | None:
    """Return the policy-derived executable entrypoint, never manifest-derived.

    Only the exact linter identity may yield its pinned ``linter_engine``.
    """
    view = _manifest_view(manifest)
    if view["id"] != API3_LINTER_ID:
        return None
    pin = api3_pin_for(view["id"], view["version"], pins=pins)
    if pin is None:
        return None
    return dict(pin.entrypoints).get("linter_engine")


def api3_application_entrypoint(
    manifest: Any,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> str | None:
    """Return the pinned application-tool path for the exact Studio identity."""
    view = _manifest_view(manifest)
    if view["id"] != API3_STUDIO_ID:
        return None
    pin = api3_pin_for(view["id"], view["version"], pins=pins)
    return dict(pin.entrypoints).get("application_tool") if pin is not None else None


def is_approved_api3(
    manifest: Any,
    *,
    pins: Mapping[tuple[str, str], Api3Pin] | None = None,
) -> bool:
    """Return True only when the static API 3 contract matches a host pin."""
    return api3_static_error(manifest, pins=pins) is None
