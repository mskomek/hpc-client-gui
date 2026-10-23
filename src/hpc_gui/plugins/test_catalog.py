"""Test-only local plugin catalog (file://) for offline install and update tests.

Enabled ONLY when both switches are set:

* ``HPC_GUI_TEST_MODE=1`` (same ``<APP>_TEST_MODE=1`` convention as
  ``TRUBA_GUI_FTP_TEST_MODE``), and
* ``HPC_GUI_PLUGIN_TEST_CATALOG`` set to ``file:///<absolute dir>`` or an
  absolute local directory.

While active, every URL under the official raw base is served from that
directory at the same relative path (``registry.json``, manifests, payloads).
The network is never contacted. Not for production use.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from hpc_gui.plugins.models import is_safe_relative_path

TEST_MODE_ENV = "HPC_GUI_TEST_MODE"
TEST_CATALOG_ENV = "HPC_GUI_PLUGIN_TEST_CATALOG"
REGISTRY_REL = "registry.json"

# Values naming a remote or foreign location: URI schemes, drive paths, UNC.
_FOREIGN_LOCATION = re.compile(r"^(?:[a-zA-Z][a-zA-Z0-9+.-]*://|file:|[A-Za-z]:[\\/]|\\\\|//)")

logger = logging.getLogger(__name__)


class CatalogRefusedError(RuntimeError):
    """The test catalog is enabled but refused a location or a file."""


def configured_catalog_setting() -> str | None:
    """Return the catalog setting only when BOTH switches are set."""
    if os.environ.get(TEST_MODE_ENV, "").strip() != "1":
        return None
    return os.environ.get(TEST_CATALOG_ENV, "").strip() or None


def _local_text(setting: str) -> str:
    if not setting.lower().startswith("file:"):
        return setting
    if any(char in setting for char in "?#\\"):
        raise CatalogRefusedError("file:// catalog URL must not contain a query, fragment or backslash")
    parts = urlsplit(setting)
    if parts.scheme.lower() != "file" or parts.netloc:
        raise CatalogRefusedError("file:// catalog URL must have no host: use file:///<absolute path>")
    text = unquote(parts.path)
    if re.match(r"^/[A-Za-z]:/", text):
        text = text[1:]
    return text


def resolve_catalog_root(setting: str) -> Path:
    """Validate the catalog location and return its real absolute directory."""
    text = _local_text(setting.strip())
    if text.startswith(("\\\\", "//")):
        raise CatalogRefusedError("UNC or network catalog paths are refused")
    if ".." in re.split(r"[\\/]", text):
        raise CatalogRefusedError("catalog path must not contain '..' segments")
    candidate = Path(text)
    if not candidate.is_absolute():
        raise CatalogRefusedError("catalog must be a file:// URL or an absolute local directory")
    try:
        root = candidate.resolve(strict=True)
    except OSError as exc:
        raise CatalogRefusedError(f"catalog directory is not accessible: {exc}") from exc
    if not root.is_dir() or str(root).startswith(("\\\\", "//")):
        raise CatalogRefusedError("catalog must resolve to an existing local directory")
    return root


def active_catalog_root() -> Path | None:
    """Return the validated catalog root when the override is active, else None."""
    setting = configured_catalog_setting()
    if setting is None:
        return None
    root = resolve_catalog_root(setting)
    logger.warning(
        "PLUGIN TEST CATALOG ACTIVE: plugins are served from %s; the official registry is not contacted.",
        root,
    )
    return root


def _catalog_relative(url: str, raw_base: str) -> str:
    if not url.startswith(raw_base):
        raise CatalogRefusedError(f"test catalog cannot serve a URL outside {raw_base}")
    rel = url[len(raw_base):]
    if not rel or ":" in rel or "\\" in rel or not is_safe_relative_path(rel):
        raise CatalogRefusedError(f"unsafe test catalog path: {rel!r}")
    return rel


def _refuse_foreign_locations(value: object, raw_base: str) -> None:
    """Mixed-catalog guard: only the official raw base may appear as a location."""
    if isinstance(value, dict):
        for item in value.values():
            _refuse_foreign_locations(item, raw_base)
    elif isinstance(value, list):
        for item in value:
            _refuse_foreign_locations(item, raw_base)
    elif isinstance(value, str) and value != raw_base and _FOREIGN_LOCATION.match(value):
        raise CatalogRefusedError(f"registry names a foreign location: {value[:80]!r}")


def read_catalog_url(root: Path, url: str, raw_base: str, max_bytes: int) -> bytes:
    """Return the bytes of the catalog file an official URL maps to."""
    rel = _catalog_relative(url, raw_base)
    try:
        resolved = (root / rel).resolve(strict=True)
    except OSError as exc:
        raise CatalogRefusedError(f"not present in the test catalog: {rel}") from exc
    if not resolved.is_relative_to(root):
        raise CatalogRefusedError(f"test catalog path escapes the catalog root: {rel}")
    if not resolved.is_file():
        raise CatalogRefusedError(f"not a file in the test catalog: {rel}")
    with resolved.open("rb") as handle:
        data = handle.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise CatalogRefusedError(f"{rel} exceeds the size limit")
    if rel == REGISTRY_REL:
        try:
            parsed = json.loads(data.decode("utf-8"))
        except ValueError:
            parsed = None  # parse_registry reports malformed registries
        _refuse_foreign_locations(parsed, raw_base)
    return data


def mark_test_catalog_title(title: str, badge: str) -> str:
    """Append the visible test-mode badge only while the override is configured."""
    return f"{title} \u2014 {badge}" if configured_catalog_setting() else title
