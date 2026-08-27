"""Evaluate the final release-candidate gate for the release workflow.

The workflow passes every required job result plus the requested macOS mode
to this module. The evaluation is pure Python so the release policy can be
unit-tested without running GitHub Actions, and the workflow simply fails
the ``release-gate`` job when any violation is reported.

Policy:
    * The four build jobs (Linux, Windows, macOS arm64, macOS x86_64) must
      succeed in every mode.
    * ``macos_mode=signed`` requires both signing/notarization jobs and the
      signed-candidate verification job to succeed.
    * ``macos_mode=unsigned`` requires the signing and signed-verification
      jobs to be skipped, and the unsigned verification job to succeed.
    * Any cancelled or failed required job blocks the gate.
    * Publication itself stays opt-in via the ``publish`` input; a failed
      gate always blocks the ``publish-release`` job because that job needs
      this one.

Usage (workflow):
    python scripts/release_gate.py

Every job result is read from ``GATE_RESULT_<JOB>`` environment variables;
the mode comes from ``GATE_MACOS_MODE``. Missing results are treated as
violations, never as success.
"""

from __future__ import annotations

import os
import sys

MACOS_MODES = ("signed", "unsigned")

BUILD_JOBS = (
    "build-linux",
    "build-windows",
    "build-macos-arm64",
    "build-macos-x86_64",
)

SIGNED_ONLY_JOBS = (
    "sign-macos-arm64",
    "sign-macos-x86_64",
    "verify-macos-signed-candidate",
)

UNSIGNED_VERIFY_JOB = "verify-unsigned-release"


def evaluate_gate(macos_mode: str, results: dict[str, str]) -> list[str]:
    """Return a list of policy violations for the given job results."""
    violations: list[str] = []
    if macos_mode not in MACOS_MODES:
        return [f"unsupported macos_mode: {macos_mode!r}"]

    for job in BUILD_JOBS:
        result = results.get(job)
        if result is None:
            violations.append(f"missing result for required job {job}")
        elif result != "success":
            violations.append(f"job {job} did not succeed (result: {result})")

    for job in SIGNED_ONLY_JOBS:
        result = results.get(job)
        expected = "success" if macos_mode == "signed" else "skipped"
        if result is None:
            violations.append(f"missing result for job {job}")
        elif result != expected:
            violations.append(
                f"job {job} must be {expected} in macos_mode={macos_mode} "
                f"(result: {result})"
            )

    unsigned_result = results.get(UNSIGNED_VERIFY_JOB)
    expected_unsigned = "success" if macos_mode == "unsigned" else "skipped"
    if unsigned_result is None:
        violations.append(f"missing result for job {UNSIGNED_VERIFY_JOB}")
    elif unsigned_result != expected_unsigned:
        violations.append(
            f"job {UNSIGNED_VERIFY_JOB} must be {expected_unsigned} in "
            f"macos_mode={macos_mode} (result: {unsigned_result})"
        )

    return violations


def _collect_results() -> dict[str, str]:
    prefix = "GATE_RESULT_"
    results: dict[str, str] = {}
    for name, value in os.environ.items():
        if name.startswith(prefix):
            # Job names only ever contain hyphens (no underscores), so the
            # workflow can encode them losslessly with underscores.
            job = name[len(prefix):].strip().lower().replace("_", "-")
            results[job] = value.strip().lower()
    return results


def main(argv: list[str] | None = None) -> int:
    del argv  # retained for CLI symmetry; configuration is env-driven
    mode = os.environ.get("GATE_MACOS_MODE", "").strip()
    violations = evaluate_gate(mode, _collect_results())
    if violations:
        print("release gate FAILED:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1
    print(f"release gate passed (macos_mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
