from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from hpc_gui.services.capability_report import (  # noqa: E402
    CAPABILITY_KEYS,
    CapabilityReport,
)


class CapabilityReportTests(unittest.TestCase):
    def test_all_capabilities_map_to_stable_statuses(self) -> None:
        probes = {key: True for key in CAPABILITY_KEYS}
        probes["x11_possible"] = None
        report = CapabilityReport.from_probes(probes, release="v9.9.9")

        self.assertEqual(report.statuses["ssh_connected"], "available")
        self.assertEqual(report.statuses["slurm_sacct_available"], "available")
        self.assertEqual(report.statuses["x11_possible"], "unknown")
        self.assertEqual(report.unknown(), ("x11_possible",))
        self.assertEqual(report.unavailable(), ())
        self.assertIn("9/10", report.summary())
        self.assertIn("check x11_possible", report.summary())

    def test_unavailable_and_unknown_are_reported_not_hidden(self) -> None:
        probes: dict[str, bool | None] = {key: True for key in CAPABILITY_KEYS}
        probes.update(
            {
                "slurm_sacct_available": False,
                "slurm_scontrol_available": False,
                "scratch_path_known": None,
            }
        )
        report = CapabilityReport.from_probes(probes)

        self.assertEqual(
            report.unavailable(),
            ("slurm_sacct_available", "slurm_scontrol_available"),
        )
        self.assertEqual(report.unknown(), ("scratch_path_known",))
        self.assertIn("7/10", report.summary())
        self.assertIn("check slurm_sacct_available", report.summary())

    def test_extra_probe_keys_are_ignored(self) -> None:
        probes = {key: True for key in CAPABILITY_KEYS}
        probes["motd_banner_detected"] = True
        report = CapabilityReport.from_probes(probes)
        self.assertNotIn("motd_banner_detected", report.as_dict()["capabilities"])

    def test_as_dict_is_json_serializable(self) -> None:
        report = CapabilityReport.from_probes({key: None for key in CAPABILITY_KEYS})
        decoded = json.loads(json.dumps(report.as_dict()))
        self.assertEqual(decoded["capabilities"]["sftp_available"], "unknown")


if __name__ == "__main__":
    unittest.main()
