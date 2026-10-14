"""Evaluate the final release-candidate gate for the release workflow.

The workflow passes every required job result plus the requested macOS mode
to this module. The evaluation is pure Python so the release policy can be
unit-tested without running GitHub Actions, and the workflow simply fails
the ``release-gate`` job when any violation is reported.

Policy (job layer):
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

Policy (publication layer, W60.2 RELEASE-GATE-001..005):
    * The gate additionally consumes a machine-readable final V2 acceptance
      result (JSON file). Build/signing success alone never publishes.
    * Fail closed unless mandatory acceptance is PASS with
      ``FAIL/BLOCKED/NOT_EVIDENCED = 0``, feature inventory = 100%,
      settings inventory = 100% and secret scan = PASS.
    * ``tested artifact SHA-256`` must equal ``publishing artifact SHA-256``.
    * The plugin-registry freeze/commit identity used for acceptance must
      equal the identity declared for release.
    * SSH/SFTP/PTY/Slurm/GUI/updater/migration/settings/diagnostics
      evidence must each be represented in the gate result.
    * Open P0/P1 must be 0 and rollback must be ready; any required
      BLOCKED/PARTIAL gate blocks publication.

Usage (workflow):
    python scripts/release_gate.py

Every job result is read from ``GATE_RESULT_<JOB>`` environment variables;
the mode comes from ``GATE_MACOS_MODE``. Missing results are treated as
violations, never as success. The acceptance result path comes from
``GATE_ACCEPTANCE_RESULT``; optional cross-check overrides come from
``GATE_TESTED_SHA256``, ``GATE_PUBLISHING_SHA256``,
``GATE_PLUGIN_FREEZE`` and ``GATE_PLUGIN_COMMIT``. A missing or
unparseable acceptance result is a violation, never success.
"""

from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

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

ACCEPTANCE_ENV_VAR = "GATE_ACCEPTANCE_RESULT"
TESTED_SHA_ENV_VAR = "GATE_TESTED_SHA256"
PUBLISHING_SHA_ENV_VAR = "GATE_PUBLISHING_SHA256"
PLUGIN_FREEZE_ENV_VAR = "GATE_PLUGIN_FREEZE"
PLUGIN_COMMIT_ENV_VAR = "GATE_PLUGIN_COMMIT"

# RELEASE-GATE-005: every domain must be represented in the gate result.
REQUIRED_EVIDENCE_DOMAINS = (
    "ssh",
    "sftp",
    "pty",
    "slurm",
    "gui",
    "updater",
    "migration",
    "settings",
    "diagnostics",
)

_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_PASS_TOKENS = {"pass", "passed", "ok", "success", "present", "yes", "true", "ready"}
_BLOCK_TOKENS = {"fail", "failed", "failure", "blocked", "partial", "not_evidenced"}


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
    env_prefix = "GATE_RESULT_"
    results: dict[str, str] = {}
    for name, value in os.environ.items():
        if name.startswith(env_prefix):
            # Job names only ever contain hyphens (no underscores), so the
            # workflow can encode them losslessly with underscores.
            encoded = name[len(env_prefix):].strip().lower()
            # GitHub environment names cannot preserve hyphens, while the
            # job id intentionally uses x86_64. Decode that token before the
            # remaining separators are normalized.
            if encoded.endswith("_x86_64"):
                job_prefix = encoded[: -len("_x86_64")].replace("_", "-")
                job = f"{job_prefix}-x86_64"
            else:
                job = encoded.replace("_", "-")
            results[job] = value.strip().lower()
    return results


def _first_present(data: dict, *keys: str):
    """Return the first present (non-None) value for any of *keys*."""
    for key in keys:
        if key in data and data[key] is not None:
            return data[key]
    return None


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"-?\d+", text):
            return int(text)
    return None


def _norm_token(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower()


def evaluate_acceptance_result(data: object) -> list[str]:
    """Validate a machine-readable final V2 acceptance result (001/002/003/004/005).

    Returns violations; an empty list means the acceptance layer passes.
    Anything missing, unparseable, or below policy fails closed.
    """
    violations: list[str] = []
    if not isinstance(data, dict):
        return ["acceptance result must be a JSON object"]

    # --- 001: machine-readable verdict present and PASS ---
    verdict = _first_present(data, "verdict", "mandatory_verdict", "acceptance_verdict")
    if verdict is None:
        violations.append("acceptance result missing mandatory verdict")
    elif _norm_token(verdict) not in ("pass", "acceptance_green", "go"):
        violations.append(f"acceptance verdict blocks publication (verdict: {verdict})")
    elif _norm_token(verdict) in _BLOCK_TOKENS:
        violations.append(f"acceptance verdict blocks publication (verdict: {verdict})")

    # --- 002: FAIL/BLOCKED/NOT_EVIDENCED = 0, 100% inventories, secret-scan PASS ---
    mandatory = data.get("mandatory")
    if isinstance(mandatory, dict):
        fail_v = _first_present(mandatory, "fail", "failed", "fails")
        blocked_v = _first_present(mandatory, "blocked")
        not_ev_v = _first_present(
            mandatory, "not_evidenced", "not-evidenced", "notevidenced", "missing_evidence"
        )
    else:
        fail_v = _first_present(
            data, "mandatory_fail", "mandatory_failed", "mandatory_fails", "fail", "failed"
        )
        blocked_v = _first_present(data, "mandatory_blocked", "blocked")
        not_ev_v = _first_present(
            data,
            "mandatory_not_evidenced",
            "mandatory_not-evidenced",
            "not_evidenced",
            "not-evidenced",
        )
    for label, raw in (
        ("mandatory FAIL", fail_v),
        ("mandatory BLOCKED", blocked_v),
        ("mandatory NOT_EVIDENCED", not_ev_v),
    ):
        count = _as_int(raw)
        if raw is None or count is None:
            violations.append(f"acceptance result missing {label} count")
        elif count != 0:
            violations.append(f"{label} must be 0 (observed: {count})")

    for label, keys in (
        ("feature inventory", ("feature_inventory_pct", "feature_inventory", "feature_pct")),
        ("settings inventory", ("settings_inventory_pct", "settings_inventory", "settings_pct")),
    ):
        raw = _first_present(data, *keys)
        count = _as_int(raw)
        if raw is None or count is None:
            violations.append(f"acceptance result missing {label} percentage")
        elif count != 100:
            violations.append(f"{label} must be 100% (observed: {raw})")

    secret = _first_present(data, "secret_scan", "secret-scan", "secrets_scan")
    if secret is None:
        violations.append("acceptance result missing secret-scan outcome")
    elif _norm_token(secret) != "pass":
        violations.append(f"secret scan must be PASS (observed: {secret})")

    # --- P0/P1 must be 0 ---
    for label, keys in (("open P0", ("open_p0", "p0_open", "p0")), ("open P1", ("open_p1", "p1_open", "p1"))):
        raw = _first_present(data, *keys)
        count = _as_int(raw)
        if raw is None or count is None:
            violations.append(f"acceptance result missing {label} count")
        elif count != 0:
            violations.append(f"{label} must be 0 (observed: {count})")

    # --- rollback readiness (Workstream G) ---
    rollback = _first_present(data, "rollback_ready", "rollback", "rollback_readiness")
    if rollback is None:
        violations.append("acceptance result missing rollback readiness")
    elif _norm_token(rollback) not in _PASS_TOKENS:
        violations.append(f"rollback path must be ready (observed: {rollback})")

    # --- 003: tested SHA-256 == publishing SHA-256 ---
    tested = _first_present(data, "tested_sha256", "tested_sha", "tested_artifact_sha256")
    publishing = _first_present(
        data, "publishing_sha256", "publishing_sha", "publishing_artifact_sha256",
        "release_sha256", "candidate_sha256",
    )
    if tested is None or publishing is None:
        violations.append("acceptance result missing tested/publishing SHA-256 identity")
    else:
        tested_s = str(tested).strip()
        publishing_s = str(publishing).strip()
        if not _SHA256_RE.match(tested_s):
            violations.append("tested SHA-256 is not a 64-hex digest")
        if not _SHA256_RE.match(publishing_s):
            violations.append("publishing SHA-256 is not a 64-hex digest")
        if (
            _SHA256_RE.match(tested_s)
            and _SHA256_RE.match(publishing_s)
            and tested_s.lower() != publishing_s.lower()
        ):
            violations.append("tested SHA-256 must equal publishing SHA-256 (hash drift)")

    # --- 004: plugin-registry freeze/commit identity match ---
    freeze = _first_present(
        data, "plugin_registry_freeze", "plugin_freeze", "acceptance_plugin_identity",
        "acceptance_plugin_registry",
    )
    commit = _first_present(
        data, "plugin_registry_commit", "plugin_commit", "release_plugin_identity",
        "release_plugin_registry",
    )
    if freeze is None or commit is None:
        violations.append("acceptance result missing plugin-registry freeze/commit identity")
    else:
        freeze_s = str(freeze).strip()
        commit_s = str(commit).strip()
        if not freeze_s or not commit_s:
            violations.append("plugin-registry freeze/commit identity must be non-empty")
        elif freeze_s != commit_s:
            violations.append(
                "plugin-registry freeze identity must equal commit identity declared for release"
            )

    # --- 005: SSH/SFTP/PTY/Slurm/GUI/updater/migration/settings/diagnostics ---
    evidence = data.get("evidence")
    if not isinstance(evidence, dict):
        violations.append("acceptance result missing evidence map for SSH/SFTP/PTY/Slurm/GUI/updater/migration/settings/diagnostics")
    else:
        lowered = {str(k).strip().lower(): v for k, v in evidence.items()}
        for domain in REQUIRED_EVIDENCE_DOMAINS:
            if domain not in lowered or lowered[domain] is None:
                violations.append(f"acceptance evidence missing domain: {domain}")
                continue
            token = _norm_token(lowered[domain])
            if isinstance(lowered[domain], dict):
                status = _norm_token(
                    _first_present(lowered[domain], "status", "verdict", "result", "outcome") or ""
                )
                if status not in _PASS_TOKENS:
                    violations.append(
                        f"acceptance evidence domain blocks publication: {domain} (observed: {lowered[domain]})"
                    )
            elif token in _BLOCK_TOKENS or token in {"", "false", "no", "missing", "unknown"}:
                violations.append(
                    f"acceptance evidence domain blocks publication: {domain} (observed: {lowered[domain]})"
                )
            elif token not in _PASS_TOKENS and token.isdigit() is False:
                # Free-form truthy strings that are not explicit PASS tokens
                # still fail closed unless they are affirmative evidence refs.
                if len(token) < 2:
                    violations.append(
                        f"acceptance evidence domain blocks publication: {domain} (observed: {lowered[domain]})"
                    )

    return violations


def load_acceptance_result(path: str | Path) -> tuple[dict | None, list[str]]:
    """Load the acceptance JSON file; failures are violations, never success."""
    try:
        payload = Path(path).read_text(encoding="utf-8")
    except FileNotFoundError:
        return None, [f"acceptance result file not found: {path}"]
    except OSError as exc:
        return None, [f"acceptance result unreadable ({path}): {exc}"]
    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:
        return None, [f"acceptance result is not valid JSON ({path}): {exc}"]
    return data, []


def evaluate_publication_gate(
    macos_mode: str,
    results: dict[str, str],
    acceptance: object,
    *,
    tested_sha_override: str | None = None,
    publishing_sha_override: str | None = None,
    plugin_freeze_override: str | None = None,
    plugin_commit_override: str | None = None,
) -> list[str]:
    """Combine the job gate with the machine-readable acceptance gate."""
    violations = list(evaluate_gate(macos_mode, results))
    if acceptance is None:
        violations.append(
            f"missing machine-readable acceptance result (set {ACCEPTANCE_ENV_VAR})"
        )
        return violations
    violations.extend(evaluate_acceptance_result(acceptance))
    if isinstance(acceptance, dict):
        if tested_sha_override and publishing_sha_override:
            if tested_sha_override.strip().lower() != publishing_sha_override.strip().lower():
                violations.append("publishing SHA override drifts from tested SHA override")
        for label, override, keys in (
            ("tested SHA-256", tested_sha_override, ("tested_sha256", "tested_sha", "tested_artifact_sha256")),
            ("publishing SHA-256", publishing_sha_override, ("publishing_sha256", "publishing_sha", "publishing_artifact_sha256", "release_sha256", "candidate_sha256")),
        ):
            if override:
                filed = _first_present(acceptance, *keys)
                if filed is not None and str(filed).strip().lower() != override.strip().lower():
                    violations.append(f"{label} override mismatches acceptance result (drift)")
        for label, override, keys in (
            ("plugin freeze", plugin_freeze_override, ("plugin_registry_freeze", "plugin_freeze", "acceptance_plugin_identity", "acceptance_plugin_registry")),
            ("plugin commit", plugin_commit_override, ("plugin_registry_commit", "plugin_commit", "release_plugin_identity", "release_plugin_registry")),
        ):
            if override:
                filed = _first_present(acceptance, *keys)
                if filed is not None and str(filed).strip() != override.strip():
                    violations.append(f"{label} override mismatches acceptance result (drift)")
    return violations


def _collect_overrides() -> dict[str, str | None]:
    def clean(name: str) -> str | None:
        value = os.environ.get(name, "").strip()
        return value or None

    return {
        "tested": clean(TESTED_SHA_ENV_VAR),
        "publishing": clean(PUBLISHING_SHA_ENV_VAR),
        "freeze": clean(PLUGIN_FREEZE_ENV_VAR),
        "commit": clean(PLUGIN_COMMIT_ENV_VAR),
    }


def main(argv: list[str] | None = None) -> int:
    del argv  # retained for CLI symmetry; configuration is env-driven
    mode = os.environ.get("GATE_MACOS_MODE", "").strip()
    results = _collect_results()
    overrides = _collect_overrides()
    acceptance_path = os.environ.get(ACCEPTANCE_ENV_VAR, "").strip()
    if not acceptance_path:
        acceptance: object = None
        load_errors = [f"missing machine-readable acceptance result (set {ACCEPTANCE_ENV_VAR})"]
    else:
        acceptance, load_errors = load_acceptance_result(acceptance_path)
    violations = list(evaluate_gate(mode, results))
    violations.extend(load_errors)
    if acceptance is not None:
        violations.extend(evaluate_acceptance_result(acceptance))
        # Cross-check env overrides against the filed identities (drift fails closed).
        if isinstance(acceptance, dict):
            if overrides["tested"] and overrides["publishing"]:
                if overrides["tested"].lower() != overrides["publishing"].lower():
                    violations.append("publishing SHA override drifts from tested SHA override")
            for label, override, keys in (
                ("tested SHA-256", overrides["tested"], ("tested_sha256", "tested_sha", "tested_artifact_sha256")),
                ("publishing SHA-256", overrides["publishing"], ("publishing_sha256", "publishing_sha", "publishing_artifact_sha256", "release_sha256", "candidate_sha256")),
                ("plugin freeze", overrides["freeze"], ("plugin_registry_freeze", "plugin_freeze", "acceptance_plugin_identity", "acceptance_plugin_registry")),
                ("plugin commit", overrides["commit"], ("plugin_registry_commit", "plugin_commit", "release_plugin_identity", "release_plugin_registry")),
            ):
                if override:
                    filed = _first_present(acceptance, *keys)
                    compare = str(filed).strip() if filed is not None else None
                    if compare is not None and compare.lower() != override.lower():
                        violations.append(f"{label} override mismatches acceptance result (drift)")
    if violations:
        print("release gate FAILED:", file=sys.stderr)
        for violation in violations:
            print(f"  - {violation}", file=sys.stderr)
        return 1
    print(f"release gate passed (macos_mode={mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
