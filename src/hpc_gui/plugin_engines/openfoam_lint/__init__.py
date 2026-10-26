"""OpenFOAM.com v2312 static linter plugin API."""
from .api import lint_files, lint_paths, lint_text, rule_catalog, supports_filename
from .api import SUPPORTED_FILENAMES, SUPPORTED_SUFFIXES
from .rules import LintResult
from .remote_case import lint_remote_path

__all__ = [
    "LintResult", "SUPPORTED_FILENAMES", "SUPPORTED_SUFFIXES", "lint_files",
    "lint_paths", "lint_remote_path", "lint_text", "rule_catalog", "supports_filename",
]


def create_plugin():
    return {
        "id": "org.hpcclient.openfoamlint",
        "title": "OpenFOAM Linter",
        "description": "Read-only OpenFOAM.com v2312 static and cross-file diagnostics.",
        "page_factory": _qt_page_factory,
        "wx_page_factory": _wx_page_factory,
    }


def _qt_page_factory(parent=None, initial_paths=None, session_state=None, **_kwargs):
    from .qt_page import create_qt_page
    return create_qt_page(
        parent=parent, initial_paths=initial_paths or (),
        session_state=session_state, host_window=_kwargs.get("host_window"),
    )


def _wx_page_factory(parent=None, initial_paths=None, initial_path=None, session_state=None, **kwargs):
    from .wx_page import create_wx_page
    paths = list(initial_paths or ())
    if initial_path and initial_path not in paths:
        paths.append(initial_path)
    return create_wx_page(
        parent=parent, initial_paths=paths, session_state=session_state,
        remote=bool(kwargs.get("remote", False)) or (
            isinstance(session_state, dict)
            and isinstance(session_state.get("session"), dict)
            and session_state["session"].get("files") is not None
            and any(str(path).startswith("/") for path in paths)
        ),
        auto_run=kwargs.get("action") == "validate",
    )
