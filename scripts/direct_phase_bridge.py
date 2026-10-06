"""Wait for one current-session receipt and expose it as a Codex phase result."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from direct_executor import publish_contract, wait_for_receipt


DISPATCH_RE = re.compile(r"(?m)^Controller dispatch: (\{[^\r\n]*\})\s*$")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--result-path", type=Path, required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--wave", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--node", required=True)
    parser.add_argument("--seq", type=int, required=True)
    parser.add_argument("--phase-instance-id", required=True)
    parser.add_argument("stdin_marker", nargs="?")
    args = parser.parse_args(argv)
    prompt = sys.stdin.read()
    match = DISPATCH_RE.search(prompt)
    if not match:
        raise SystemExit("phase prompt has no controller dispatch identity")
    dispatch = json.loads(match.group(1))
    expected = {"phase_instance_id": args.phase_instance_id, "wave_id": args.wave,
                "phase": args.phase, "node": args.node}
    if any(dispatch.get(key) != value for key, value in expected.items()):
        raise SystemExit("phase prompt identity does not match the direct bridge context")
    prompt_path = args.run_dir / f"{args.seq:04d}-{args.wave}-{args.phase}.prompt.md"
    schema_path = args.run_dir / "phase-result.schema.json"
    if not prompt_path.is_file() or not schema_path.is_file():
        raise SystemExit("controller prompt or phase-result schema is missing")
    # Text stdin is newline-normalized by Python on Windows, while the saved
    # prompt may contain CRLF bytes. Bind the receipt to the controller's raw
    # file identity and compare semantic dispatch identity from both copies.
    saved_prompt_bytes = prompt_path.read_bytes()
    saved_prompt = prompt_path.read_text(encoding="utf-8")
    saved_match = DISPATCH_RE.search(saved_prompt)
    if not saved_match or json.loads(saved_match.group(1)) != dispatch:
        raise SystemExit("controller prompt on disk has a different dispatch identity")
    contract = {
        "version": 1,
        "run_id": args.run_id,
        "wave_id": args.wave,
        "phase": args.phase,
        "node": args.node,
        "seq": args.seq,
        "phase_instance_id": args.phase_instance_id,
        "repo_root": str(args.repo_root.resolve()),
        "prompt_path": str(prompt_path.relative_to(args.repo_root.resolve())),
        "prompt_sha256": hashlib.sha256(saved_prompt_bytes).hexdigest(),
        "result_schema_path": str(schema_path.resolve()),
        "result_schema_sha256": hashlib.sha256(schema_path.read_bytes()).hexdigest(),
        "executor_mode": "direct",
        "backend": "codex",
    }
    contract_path, _receipt_path = publish_contract(args.run_dir, contract)
    print(f"AC_WAVE_DIRECT_EXECUTION_CONTRACT={contract_path.relative_to(args.repo_root.resolve())}", flush=True)
    receipt = wait_for_receipt(args.run_dir, contract_path)
    result = receipt["result"]
    args.result_path.parent.mkdir(parents=True, exist_ok=True)
    args.result_path.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")
    for event in receipt.get("progress", []):
        print("AC_WAVE_PROGRESS_EVENT: " + json.dumps(event, ensure_ascii=False, separators=(",", ":")), flush=True)
    print("AC_WAVE_DIRECT_EXECUTION_RECEIPT_ACCEPTED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
