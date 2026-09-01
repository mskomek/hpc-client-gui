from types import SimpleNamespace

import pytest

from hpc_gui.services.job_failure_classifier import explain_job_failure


@pytest.mark.parametrize("reason", ["OUT_OF_MEMORY", "TIMEOUT", "NODE_FAIL", "PREEMPTED", "CANCELLED", "BOOT_FAIL", "DEADLINE"])
def test_known_scheduler_failure_categories(reason):
    result = explain_job_failure(SimpleNamespace(state=reason, reason="", failure_reason="", exit_code="0"))
    assert result is not None
    assert result.category
    assert result.as_lines()[0].startswith("Possible cause:")
    assert result.as_lines()[1].startswith("Scheduler reported:")


def test_unknown_and_completed_jobs_are_not_overstated():
    assert explain_job_failure(SimpleNamespace(state="FAILED", reason="Unknown", failure_reason="", exit_code="0")) is None
    assert explain_job_failure(SimpleNamespace(state="COMPLETED", reason="", failure_reason="", exit_code="0")) is None


def test_nonzero_exit_and_scheduler_metadata_are_reported():
    result = explain_job_failure(SimpleNamespace(state="FAILED", reason="NonZeroExitCode", failure_reason="", exit_code="1:0", max_rss="8G"))
    assert result.category == "nonzero_exit"
    assert "NonZeroExitCode" in result.scheduler_reported


def test_localization_hook_is_used():
    translations = {"failure.timeout.cause": "Süre sınırına ulaşıldı.", "failure.scheduler_reported": "Zaman aşımı bildirildi."}
    def translate(key, fallback):
        return translations.get(key, fallback)
    result = explain_job_failure(SimpleNamespace(state="TIMEOUT"), translate)
    assert result.possible_cause == translations["failure.timeout.cause"]
    assert result.scheduler_reported == translations["failure.scheduler_reported"]
