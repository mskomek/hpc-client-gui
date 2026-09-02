"""Entry point.

Not: IDE'lerde bazen modül yerine dosya olarak çalıştırılır (script path).
Bu durumda relative import (from .app ...) "parent package" olmadığı için patlar.

Bu dosya hem `python -m hpc_gui` hem de doğrudan çalıştırma için güvenli olacak
şekilde yazılmıştır.
"""

import importlib.util
import os
import sys
from pathlib import Path


def _load_source_performance_probe():
    """Load the optional source-only profiler without packaging it."""
    if os.environ.get("TRUBA_GUI_PERF_DEBUG") != "1":
        return None
    if bool(getattr(sys, "frozen", False)):
        return None

    probe_path = Path(__file__).resolve().parents[2] / "devtools" / "performance_probe.py"
    if not probe_path.is_file():
        return None

    try:
        spec = importlib.util.spec_from_file_location("_hpc_gui_perf_probe", probe_path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        module.start(Path(__file__).resolve().parents[2])
        return module
    except Exception as exc:
        print(f"[perf-debug] profiler could not start: {exc}", file=sys.stderr)
        return None


_PERFORMANCE_PROBE = _load_source_performance_probe()

_CLI_COMMANDS = {"--help", "-h", "version", "gui", "commands", "profile", "doctor", "files", "jobs"}


def _is_wx_invocation(argv: list[str]) -> bool:
    return "--wx" in argv


def _is_cli_invocation(argv: list[str]) -> bool:
    # Global CLI options may appear before the subcommand, for example
    # ``--format json version``.  An empty invocation remains the GUI path.
    return any(argument in _CLI_COMMANDS for argument in argv)


if __package__ is None or __package__ == "":
    # script olarak çalıştırıldı -> src/ dizinini sys.path'e ekle
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hpc_gui.runtime import DEFAULT_GUI_RUNTIME

if "--wx" in sys.argv[1:]:
    from hpc_gui.wx_shell import main
elif "--updater-helper" in sys.argv[1:]:
    from hpc_gui.services.updater_helper import run_helper
elif _is_cli_invocation(sys.argv[1:]):
    from hpc_gui.cli.main import run_cli
else:
    if DEFAULT_GUI_RUNTIME == "wx":
        from hpc_gui.wx_shell import main
    else:
        from hpc_gui.app import main

if _PERFORMANCE_PROBE is not None:
    _PERFORMANCE_PROBE.mark("application_imports_complete")

if __name__ == "__main__":
    if "--wx" in sys.argv[1:]:
        raise SystemExit(main())
    if "--updater-helper" in sys.argv[1:]:
        index = sys.argv.index("--updater-helper")
        raise SystemExit(run_helper(Path(sys.argv[index + 1])))
    if _is_cli_invocation(sys.argv[1:]):
        raise SystemExit(run_cli())
    raise SystemExit(main())
