"""Source contracts for modular wx shell command routing."""
from __future__ import annotations

import pathlib
import re

import pytest

def _wx_shell_sources():
    return "\n".join(
        path.read_text(encoding="utf-8")
        for path in sorted(pathlib.Path("src/hpc_gui").glob("wx_shell*.py"))
    )


# ---------------------------------------------------------------------------
# REQ-W02-TRACE-001: dispatch reaches its canonical owner (contract test)
# ---------------------------------------------------------------------------

_DISPATCH_OWNERS = [
    ("APP-SETTINGS", "wx_settings_view", "show_settings"),
    ("APP-UPDATE-CHECK", "wx_updater_view", "WxUpdateDialog"),
    ("APP-SEND-LOGS", "wx_send_logs_view", "show_send_logs"),
    ("APP-ABOUT", "wx_about", "show_about"),
    ("PLUGIN-BROWSE", "wx_plugins_view", "show_plugins"),
    ("PLUGIN-MANAGE", "wx_plugins_view", "show_plugins"),
    ("PLUGIN-UPDATES", "wx_plugins_view", "show_plugins"),
    ("PLUGIN-REQUEST", "plugin_manager_dialog", "PLUGIN_REQUEST_URL"),
    ("APP-HELP", "wx_help", "show_help"),
    ("APP-CONNECT", "wx_connection", "show_connection"),
    ("NAV-FILES", "wx_local_files", "show_local_files"),
    ("NAV-DIRECTORIES", "wx_directories_view", "show_directories"),
    ("NAV-LOGS", "wx_logs_view", "show_logs"),
    ("NAV-JOBS", "wx_jobs", "show_jobs"),
    ("NAV-TERMINAL", "wx_terminal", "show_terminal"),
    ("NAV-EDITOR", "wx_shell", "open_primary"),
]


def _dispatch_block(src, command_id):
    """Extract the ``_dispatch`` branch handling ``command_id``.

    Branches use either ``command_id == "X"`` or
    ``command_id in {"X", ...}``; menu bindings elsewhere reference the same
    ids, so anchor on the ``if/elif command_id`` statement itself.
    """
    pattern = re.compile(
        r"(?:if|elif)\s+command_id\s*(?:==|in)\s*[^\n]*\"" + re.escape(command_id) + r"\"[^\n]*\n"
    )
    match = pattern.search(src)
    assert match, f"no dispatch branch for {command_id}"
    start = match.start()
    end = src.find("\n    elif ", start)
    return src[start : end if end != -1 else len(src)]


@pytest.mark.parametrize("command_id,owner_module,owner_symbol", _DISPATCH_OWNERS)
def test_dispatch__reaches_canonical_owner(command_id, owner_module, owner_symbol):
    """REQ-W02-TRACE-001: every baseline-visible action traces
    requirement -> live implementation owner in ``_dispatch``."""
    src = _wx_shell_sources()
    block = _dispatch_block(src, command_id)
    assert owner_symbol in block, (
        f"{command_id} does not reach canonical owner {owner_module}.{owner_symbol}"
    )


def test_dispatch__no_silent_pass_on_mandatory_branches():
    """ERROR-GOV-001 inventory lock: the six remediated mandatory branches
    must not regress to bare ``except ...: pass``."""
    src = _wx_shell_sources()
    for command_id in (
        "APP-SETTINGS",
        "APP-UPDATE-CHECK",
        "APP-SEND-LOGS",
        "APP-ABOUT",
        "PLUGIN-BROWSE",
        "PLUGIN-REQUEST",
    ):
        block = _dispatch_block(src, command_id)
        lines = [line.strip() for line in block.splitlines()]
        for i, line in enumerate(lines):
            if line == "pass" and i > 0 and lines[i - 1].startswith("except"):
                raise AssertionError(f"silent except-pass regressed in {command_id}")
        assert "report_wx_action_error" in block, (
            f"{command_id} must report failures through the error helper"
        )


# ---------------------------------------------------------------------------
# FIX-W02-A2 (DEF-W02-001, post-green review): chrome handlers route through
# the governed _dispatch chokepoint instead of duplicating silent handlers.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "handler,command_id",
    [
        ("_on_plugins", "PLUGIN-BROWSE"),
        ("_on_send_logs", "APP-SEND-LOGS"),
        ("_on_settings", "APP-SETTINGS"),
    ],
)
def test_chrome_handler__routes_through_dispatch(handler, command_id):
    """Post-green review: no duplicate silent implementation path may survive
    next to the remediated ``_dispatch`` branches."""
    src = _wx_shell_sources()
    start = src.index(f"def {handler}(")
    end = src.find("\n    def ", start + 1)
    block = src[start : end if end != -1 else len(src)]
    assert f'_dispatch("{command_id}"' in block, (
        f"{handler} must route through the governed _dispatch chokepoint"
    )
    lines = [line.strip() for line in block.splitlines()]
    for i, line in enumerate(lines):
        if line == "pass" and i > 0 and lines[i - 1].startswith("except"):
            raise AssertionError(f"silent except-pass survives in {handler}")
