"""Fixtures shared by the plugin contract test (W65 architecture split)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from hpc_gui.plugins.registry_client import (
    OFFICIAL_RAW_BASE,
    OFFICIAL_REGISTRY_URL,
    parse_registry,
)

REPO = os.environ.get("HPC_GUI_CONTRACT_REPO", "")


@pytest.fixture(scope="module")
def plugins_repo() -> Path:
    return Path(REPO).resolve()


@pytest.fixture(scope="module")
def local_fetcher(plugins_repo: Path):
    def fetch(url: str, max_bytes: int) -> bytes:
        if url == OFFICIAL_REGISTRY_URL:
            payload = (plugins_repo / "registry.json").read_bytes()
        elif url.startswith(OFFICIAL_RAW_BASE):
            payload = (plugins_repo / url[len(OFFICIAL_RAW_BASE):]).read_bytes()
        else:
            raise OSError(f"unexpected URL outside the official raw base: {url}")
        if len(payload) > max_bytes:
            raise OSError("response exceeds size limit")
        return payload

    return fetch


@pytest.fixture(scope="module")
def registry(plugins_repo: Path) -> dict:
    return parse_registry((plugins_repo / "registry.json").read_bytes())
