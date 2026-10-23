"""Framework-neutral plugin-owned Plugins-menu contributions (public facade).

The implementation lives in the ``ui_contributions_*`` modules of this package:
model, primitives, conditions, items, parser, validator and collect. This module
only re-exports the import surface used by the loader, validator, and UI code.
"""

from __future__ import annotations

from hpc_gui.plugins.ui_contributions_collect import collect_plugin_menu_contributions  # noqa: F401
from hpc_gui.plugins.ui_contributions_conditions import _validate_when, evaluate_when  # noqa: F401
from hpc_gui.plugins.ui_contributions_items import (  # noqa: F401
    _normalize_separators,
    _parse_action,
    _parse_separator,
    _parse_submenu,
)
from hpc_gui.plugins.ui_contributions_model import (  # noqa: F401
    ID_RE,
    KNOWN_ACTION_KINDS,
    KNOWN_CONDITION_KEYS,
    MAX_ID_LENGTH,
    MAX_LABEL_LENGTH,
    MAX_NESTING_DEPTH,
    MAX_PLUGIN_ITEMS,
    MAX_SUBMENU_ITEMS,
    VALID_LABEL_RE,
    VALID_UNAVAILABLE,
    MenuContext,
    PluginMenuAction,
    PluginMenuContribution,
    PluginMenuItem,
    PluginMenuSeparator,
    PluginMenuSubmenu,
)
from hpc_gui.plugins.ui_contributions_parser import _parse_plugins_menu, parse_ui_contributions  # noqa: F401
from hpc_gui.plugins.ui_contributions_primitives import (  # noqa: F401
    _is_valid_id,
    _is_valid_label,
    _validate_labels,
    get_display_label,
)
from hpc_gui.plugins.ui_contributions_validator import validate_ui_contributions_dict  # noqa: F401
