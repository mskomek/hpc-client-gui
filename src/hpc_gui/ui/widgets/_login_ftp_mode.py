"""FTP mock-mode detection for the login widget (Wave M01).

Qt-free ownership of the environment-gated FTP test-mode helpers. The
login widget re-exports these names so existing imports keep working.
"""

from __future__ import annotations

import os


FTP_TEST_MODE_ENV = "TRUBA_GUI_FTP_TEST_MODE"
FTP_TEST_HOSTS = {"mock", "mock://ftp", "ftp-mock", "ftp_mock"}


def is_ftp_test_mode_enabled() -> bool:
    return os.environ.get(FTP_TEST_MODE_ENV, "").strip() == "1"


def is_ftp_mock_host(host: str) -> bool:
    return (host or "").strip().lower() in FTP_TEST_HOSTS
