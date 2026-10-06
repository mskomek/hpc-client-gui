"""Durable caller-session receipts for controller-owned direct Wave phases.

The helper transports a result; the Python controller still validates and
commits every phase result and owns scheduling, progress, and Wave lifecycle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_json(path: Path, value: dict[str, Any], *, exclusive: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if exclusive:
        fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
        tmp = Path(raw)
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
                json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.link(tmp, path)
        finally:
            try:
                tmp.unlink()
            except FileNotFoundError:
                pass
        return
    fd, raw = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    tmp = Path(raw)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def paths(run_dir: Path, phase_instance_id: str) -> tuple[Path, Path]:
    token = _digest(phase_instance_id.encode("utf-8"))
    root = run_dir / "direct-execution"
    return root / f"{token}.contract.json", root / f"{token}.receipt.json"


def publish_contract(run_dir: Path, contract: dict[str, Any]) -> tuple[Path, Path]:
    instance = str(contract.get("phase_instance_id") or "").strip()
    if not instance:
        raise ValueError("direct execution contract requires phase_instance_id")
    contract_path, receipt_path = paths(run_dir, instance)
    if receipt_path.exists():
        return contract_path, receipt_path
    if contract_path.exists():
        old = json.loads(contract_path.read_text(encoding="utf-8"))
        if old != contract:
            raise ValueError("current direct execution contract changed for an active phase")
        return contract_path, receipt_path
    _atomic_json(contract_path, contract)
    return contract_path, receipt_path


def _validate_result(result: Any, schema: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict):
        raise ValueError("direct result must be a JSON object")
    required = schema.get("required") or []
    properties = schema.get("properties") or {}
    if not isinstance(properties, dict) or any(key not in result for key in required):
        raise ValueError("direct result is missing required phase-result fields")
    if schema.get("additionalProperties") is False and set(result) - set(properties):
        raise ValueError("direct result contains unsupported phase-result fields")
    for key, rules in properties.items():
        if key not in result:
            continue
        value = result[key]
        expected = rules.get("type")
        choices = expected if isinstance(expected, list) else [expected]
        valid = any(
            (kind == "string" and isinstance(value, str))
            or (kind == "null" and value is None)
            or (kind == "array" and isinstance(value, list))
            or (kind == "object" and isinstance(value, dict))
            or (kind == "boolean" and isinstance(value, bool))
            for kind in choices
        )
        if not valid:
            raise ValueError(f"direct result field {key!r} violates the phase-result schema")
        if value is not None and "enum" in rules and value not in rules["enum"]:
            raise ValueError(f"direct result field {key!r} is outside its allowed values")
        if isinstance(value, list) and rules.get("items", {}).get("type") == "string":
            if any(not isinstance(item, str) for item in value):
                raise ValueError(f"direct result field {key!r} must contain only strings")
    return result


def submit_result(contract_path: Path, result: dict[str, Any],
                  progress_events: list[dict[str, Any]] | None = None) -> Path:
    contract_path = contract_path.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    schema_path = Path(str(contract["result_schema_path"])).resolve()
    schema_bytes = schema_path.read_bytes()
    if contract.get("result_schema_sha256") and _digest(schema_bytes) != contract["result_schema_sha256"]:
        raise ValueError("controller phase-result schema changed after dispatch")
    if contract.get("prompt_path") and contract.get("repo_root") and contract.get("prompt_sha256"):
        prompt_path = (Path(str(contract["repo_root"])) / str(contract["prompt_path"])).resolve()
        if _digest(prompt_path.read_bytes()) != contract["prompt_sha256"]:
            raise ValueError("controller phase prompt changed after dispatch")
    schema = json.loads(schema_bytes.decode("utf-8"))
    normalized = _validate_result(result, schema)
    instance = str(contract.get("phase_instance_id") or "")
    if not instance:
        raise ValueError("direct execution contract has no phase instance")
    _contract_path, receipt_path = paths(contract_path.parent.parent, instance)
    if receipt_path.resolve().parent != contract_path.parent:
        raise ValueError("direct execution contract path does not match its receipt location")
    progress = list(progress_events or [])
    for event in progress:
        if not isinstance(event, dict) or any(event.get(key) != expected for key, expected in (
                ("phase_instance_id", instance), ("wave_id", contract.get("wave_id")),
                ("phase", contract.get("phase")))):
            raise ValueError("direct progress event does not match the current phase identity")
    receipt = {
        "version": 1,
        "run_id": contract.get("run_id"),
        "wave_id": contract.get("wave_id"),
        "phase": contract.get("phase"),
        "phase_instance_id": instance,
        "contract_sha256": _digest(contract_path.read_bytes()),
        "progress": progress,
        "result": normalized,
    }
    _atomic_json(receipt_path, receipt, exclusive=True)
    return receipt_path


def wait_for_receipt(run_dir: Path, contract_path: Path, *, poll_seconds: float = 0.5) -> dict[str, Any]:
    contract_path = contract_path.resolve()
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    instance = str(contract.get("phase_instance_id") or "")
    expected_contract, receipt_path = paths(run_dir, instance)
    if expected_contract.resolve() != contract_path:
        raise ValueError("direct execution contract is outside its controller run")
    while not receipt_path.exists():
        time.sleep(max(0.1, poll_seconds))
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    expected = {
        "run_id": contract.get("run_id"),
        "wave_id": contract.get("wave_id"),
        "phase": contract.get("phase"),
        "phase_instance_id": instance,
        "contract_sha256": _digest(contract_path.read_bytes()),
    }
    if not isinstance(receipt, dict) or any(receipt.get(key) != value for key, value in expected.items()):
        raise ValueError("direct result receipt does not match the current controller contract")
    progress = receipt.get("progress") or []
    if not isinstance(progress, list):
        raise ValueError("direct progress receipt must be an array")
    for event in progress:
        if not isinstance(event, dict) or any(event.get(key) != value for key, value in (
                ("phase_instance_id", instance), ("wave_id", contract.get("wave_id")),
                ("phase", contract.get("phase")))):
            raise ValueError("direct progress event does not match the current phase identity")
    schema_path = Path(str(contract["result_schema_path"])).resolve()
    schema_bytes = schema_path.read_bytes()
    if contract.get("result_schema_sha256") and _digest(schema_bytes) != contract["result_schema_sha256"]:
        raise ValueError("controller phase-result schema changed after dispatch")
    if contract.get("prompt_path") and contract.get("repo_root") and contract.get("prompt_sha256"):
        prompt_path = (Path(str(contract["repo_root"])) / str(contract["prompt_path"])).resolve()
        if _digest(prompt_path.read_bytes()) != contract["prompt_sha256"]:
            raise ValueError("controller phase prompt changed after dispatch")
    schema = json.loads(schema_bytes.decode("utf-8"))
    receipt["result"] = _validate_result(receipt.get("result"), schema)
    return receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Submit a controller-validated direct phase result")
    sub = parser.add_subparsers(dest="command", required=True)
    submit = sub.add_parser("submit-result")
    submit.add_argument("--contract", required=True, type=Path)
    submit.add_argument("--result-file", required=True, type=Path)
    submit.add_argument("--progress-file", type=Path)
    args = parser.parse_args(argv)
    result = json.loads(args.result_file.read_text(encoding="utf-8"))
    events = []
    if args.progress_file:
        events = [json.loads(line) for line in args.progress_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    receipt = submit_result(args.contract, result, events)
    print(json.dumps({"status": "SUBMITTED", "receipt": str(receipt)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
