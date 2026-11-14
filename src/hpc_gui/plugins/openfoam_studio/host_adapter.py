"""Proposed host contribution metadata for the OpenFOAM plugins (W65 HOST-002).

``contributions()`` is the legacy descriptive shape: it is not registered
with the current host loader and its keys are not host-contract keys.
``manifest_ui_contributions()`` (r9) emits a host-validator-clean
``ui_contributions`` fragment for the manifest ``ui_contributions`` field,
so a W65 package can embed it without validator rework. The production
dispatcher derives readiness dynamically in
``hpc_gui.services.plugin_menu_actions.is_openfoam_dispatch_ready`` from
the active, application-pinned API 3 package and its host callback.
Manifest packaging and install/upgrade/rollback/VM proof remain BLOCKED_ENV
(G47). ``DISPATCH_READY`` below is a compatibility diagnostic only; it is
not consulted by the production menu dispatcher.
"""

from __future__ import annotations

from . import PLUGIN_ID, PLUGIN_VERSION, REQUIRES_APP
from hpc_gui.plugins.openfoam_lint import PLUGIN_VERSION as LINTER_PLUGIN_VERSION

FILE_CONTEXT_ACTIONS = (
    {"id": "of.newCase", "label_en": "New OpenFOAM Case", "label_tr": "Yeni OpenFOAM Vakası"},
    {"id": "of.openStudio", "label_en": "Open with OpenFOAM Case Studio",
     "label_tr": "OpenFOAM Vaka Stüdyosu ile Aç"},
    {"id": "of.validate", "label_en": "Validate with OpenFOAM Linter",
     "label_tr": "OpenFOAM Denetleyici ile Doğrula"},
    {"id": "of.createJob", "label_en": "Create Job Draft", "label_tr": "İş Taslağı Oluştur"},
)

PLUGIN_MENU = (
    {"id": "of.studio", "plugin": PLUGIN_ID, "version": PLUGIN_VERSION},
    {"id": "of.linter", "plugin": "openfoam-linter", "version": LINTER_PLUGIN_VERSION},
)


def contributions() -> dict:
    return {"file_context": list(FILE_CONTEXT_ACTIONS), "plugin_menu": list(PLUGIN_MENU),
            "requires_app": ">=1.5.9", "sftp mirrored": True}


# Host action ids requested for dispatch binding (W65 r9 fragment + r10
# registration). The fragment itself is validator-clean; the r10 host
# allowlist knows these ids, but the readiness gate keeps every dispatch
# inert (menu disabled, no execution) until a real host path is VM-proven.
REQUESTED_ACTIONS = (
    {"id": "of.openStudio", "label_en": "Open with OpenFOAM Case Studio",
     "label_tr": "OpenFOAM Vaka Stüdyosu ile Aç", "action": "openfoam.open_studio"},
    {"id": "of.newCase", "label_en": "New OpenFOAM Case",
     "label_tr": "Yeni OpenFOAM Vakası", "action": "openfoam.new_case"},
    {"id": "of.createJob", "label_en": "Create Job Draft",
     "label_tr": "İş Taslağı Oluştur", "action": "openfoam.create_job_draft"},
    {"id": "of.validate", "label_en": "Validate with OpenFOAM Linter",
     "label_tr": "OpenFOAM Denetleyici ile Doğrula", "action": "openfoam.validate"},
)

# Must stay in sync with the host allowlist subset for OpenFOAM actions.
HOST_ACTION_IDS = tuple(entry["action"] for entry in REQUESTED_ACTIONS)

# Compatibility diagnostic retained for existing tests/consumers. Runtime
# menu readiness is derived from the active API 3 pin and a callable host
# path by ``plugin_menu_actions.is_openfoam_dispatch_ready``.
DISPATCH_READY = False


def host_action_ids() -> tuple[str, ...]:
    """Return the OpenFOAM host action ids requested for dispatch."""
    return HOST_ACTION_IDS


def dispatch_readiness() -> dict:
    """Return the legacy diagnostic mirror; production dispatch ignores it."""
    return {
        "ready": bool(DISPATCH_READY),
        "reason": ("legacy diagnostic mirror enabled; not the production gate"
                   if DISPATCH_READY else
                   "legacy diagnostic mirror is false; production readiness "
                   "is computed from the active pinned package and host callback"),
        "reactivation": "Production readiness is computed by "
                        "plugin_menu_actions.is_openfoam_dispatch_ready",
    }


def manifest_ui_contributions() -> dict:
    """Return a host-contract ``ui_contributions`` fragment (W65 HOST-002).

    Passes ``validate_ui_contributions_dict`` with zero errors and parses
    via ``parse_ui_contributions``. No shortcuts/icons (host wave forbids
    them); no ``when`` gating claimed; items render disabled until the host
    binds the requested action ids.
    """
    items = [{"kind": "action", "id": entry["id"], "label": entry["label_en"],
              "labels": {"tr": entry["label_tr"]}, "action": entry["action"],
              "unavailable": "disable"} for entry in REQUESTED_ACTIONS]
    return {"plugins_menu": {"label": "OpenFOAM", "labels": {"tr": "OpenFOAM"},
                             "items": items}}


def owning_identity() -> dict:
    """Plugin manifest identity this fragment is built for."""
    return {"id": PLUGIN_ID, "version": PLUGIN_VERSION, "requires_app": REQUIRES_APP}
