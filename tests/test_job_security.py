"""Regression coverage for workspace snapshot secret redaction."""

import pytest

from hpc_gui.services.job_security import is_sensitive_key, redact_sensitive_text


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("api_token", True),
        ("private-key", True),
        ("PASSWORD", True),
        ("credential_id", True),
        ("job_id", False),
        ("partition", False),
    ],
)
def test_secret_key_detection(key, expected):
    assert is_sensitive_key(key) is expected


def test_redact_multiple_assignments_without_removing_nonsecrets():
    source = "API_TOKEN=fake-secret password: hidden PATH=/work/logs"
    redacted = redact_sensitive_text(source)
    assert redacted == "API_TOKEN=[REDACTED] password: [REDACTED] PATH=/work/logs"


def test_redact_commandline_options_and_keep_quoted_shape():
    source = "--api-key 'fake quoted secret' --access-key=hidden --mode=stable"
    redacted = redact_sensitive_text(source)
    assert redacted == "--api-key '[REDACTED]' --access-key=[REDACTED] --mode=stable"


def test_redact_json_style_assignment_and_newlines():
    source = '"private_key":"fake-value"\nSTATE=RUNNING'
    redacted = redact_sensitive_text(source)
    assert redacted == '"private_key":"[REDACTED]"\nSTATE=RUNNING'


def test_redact_empty_input():
    assert redact_sensitive_text("") == ""
    assert redact_sensitive_text(None) == ""
