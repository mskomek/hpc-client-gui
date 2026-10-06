"""Run the local Wave controller with this Codex session as its phase executor.

This project-owned adapter leaves the materialized controller untouched. The
controller retains scheduling, validation, state, progress, and lifecycle
authority; a small bridge waits for the current session's bound phase receipt.
"""
from __future__ import annotations

import importlib.util
import sys
import threading
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_ROOT = ROOT / ".opencode" / "scripts"
BRIDGE = Path(__file__).with_name("direct_phase_bridge.py")
sys.path.insert(0, str(SCRIPT_ROOT))

spec = importlib.util.spec_from_file_location("hpc_wave_controller", SCRIPT_ROOT / "run-wave-program.py")
if spec is None or spec.loader is None:
    raise RuntimeError("local Wave controller entrypoint is unavailable")
controller = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = controller
spec.loader.exec_module(controller)

_original_parse = controller.parse_controller_args
_original_bootstrap = controller.bootstrap_controller
_original_codex_exec = controller.codex_exec
_original_codex_args = controller.codex_exec_args
_original_new_instance = controller.new_phase_instance_id
_dispatch = threading.local()


def _parse_direct_args():
    argv = list(sys.argv[1:])
    selected = None
    filtered: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--executor-mode":
            if index + 1 >= len(argv):
                raise SystemExit("--executor-mode requires the value direct")
            selected = argv[index + 1]
            index += 2
            continue
        if token.startswith("--executor-mode="):
            selected = token.split("=", 1)[1]
            index += 1
            continue
        filtered.append(token)
        index += 1
    if selected != "direct":
        raise SystemExit("this project adapter requires --executor-mode direct")
    args = _original_parse(filtered)
    args.executor_mode = "direct"
    if args.backend != "codex":
        raise SystemExit("direct session execution requires --backend codex")
    return args


def _bootstrap_direct(args):
    context = _original_bootstrap(args)
    context.state["executor_mode"] = "direct"
    controller.save_state(context.run_dir, context.state)
    return context


def _direct_codex_args(run_dir: Path, sandbox: str, model: str | None, *, json_output: bool = False):
    context = getattr(_dispatch, "current", None)
    if not isinstance(context, dict):
        raise RuntimeError("direct phase transport has no controller dispatch context")
    return [
        sys.executable, str(BRIDGE),
        "--run-dir", str(run_dir),
        "--repo-root", str(ROOT),
        "--result-path", str(run_dir / "__RESULT_PATH_PLACEHOLDER__"),
        "--run-id", context["run_id"],
        "--wave", context["wave_id"],
        "--phase", context["phase"],
        "--node", context["node"],
        "--seq", str(context["seq"]),
        "--phase-instance-id", context["phase_instance_id"],
    ]


def _direct_codex_exec(repo, run_dir, project, target, wave_path, phase, canonical,
                       findings_path, model, no_progress, seq, state=None):
    state = state if isinstance(state, dict) else {}
    instance = _original_new_instance(run_dir.name, seq, target, phase)
    previous_args = controller.codex_exec_args
    previous_instance = controller.new_phase_instance_id
    _dispatch.current = {
        "run_id": run_dir.name,
        "wave_id": str(target),
        "phase": str(phase),
        "node": str(state.get("node") or controller.default_node_for_phase(phase)),
        "seq": int(seq),
        "phase_instance_id": instance,
    }
    controller.codex_exec_args = _direct_codex_args
    controller.new_phase_instance_id = lambda *_args, **_kwargs: instance
    try:
        return _original_codex_exec(repo, run_dir, project, target, wave_path, phase,
                                    canonical, findings_path, model, no_progress, seq, state)
    finally:
        controller.codex_exec_args = previous_args
        controller.new_phase_instance_id = previous_instance
        _dispatch.current = None


controller.parse_controller_args = _parse_direct_args
controller.bootstrap_controller = _bootstrap_direct
controller.codex_exec = _direct_codex_exec


if __name__ == "__main__":
    try:
        raise SystemExit(controller.main())
    except KeyboardInterrupt:
        print("OPERATOR_CANCELLED", file=sys.stderr)
        raise SystemExit(130)
