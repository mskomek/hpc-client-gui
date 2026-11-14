"""W65 UI-012: relabelling must not depend on a live tab listing.

The file-browser Back/Forward/Parent labels and the filter tab texts used to be
written inside a per-tab loop guarded by "except RuntimeError: continue", so a
dead listing skipped them and they kept the previous language. They are single
widgets, and these tests pin that they are relabelled regardless.
"""

from __future__ import annotations

import types

import pytest


class _Widget:
    def __init__(self, label=""):
        self.label = label
        self.tooltip = ""
        self.enabled = True

    def SetLabel(self, value):  # noqa: N802 - wx naming
        self.label = value

    def SetToolTip(self, value):  # noqa: N802
        self.tooltip = value

    def Enable(self, value):  # noqa: N802
        self.enabled = value


class _DeadListing:
    def SetColumn(self, *_args, **_kwargs):  # noqa: N802
        raise RuntimeError("listing destroyed")


class _FilterNotebook:
    def __init__(self):
        self.texts = {}

    def SetPageText(self, index, value):  # noqa: N802
        self.texts[index] = value


class _Host:
    def set_host_title(self, _value):
        pass


def _build_view():
    """Minimal view namespace for hpc_gui.wx_remote_files_listing.install_listing."""
    filters = types.SimpleNamespace(
        visible_filter_ids=lambda: ["all", "folders"],
        get=lambda fid: types.SimpleNamespace(id=fid, source="core"),
        replace_external=lambda _defs: None,
        matches=lambda entry, fid: True,
    )
    filter_notebook = _FilterNotebook()
    tab = {
        "listing": _DeadListing(),
        "path": "/tmp",
        "filter_notebook": filter_notebook,
        "filter_ids": ["all", "folders"],
        "filter": "all",
    }
    view = types.SimpleNamespace(
        _available=lambda *a, **k: True,
        _current_navigation_store=lambda: None,
        activate=lambda *a, **k: None,
        btn_back=_Widget("Geri"),
        btn_delete=_Widget(),
        btn_download=_Widget(),
        btn_favorites=_Widget(),
        btn_forward=_Widget(),
        btn_history=_Widget(),
        btn_new_file=_Widget(),
        btn_new_folder=_Widget(),
        btn_refresh=_Widget(),
        btn_undo=_Widget(),
        btn_up=_Widget(),
        btn_upload=_Widget(),
        context=lambda *a, **k: None,
        file_filter_registry=filters,
        host=_Host(),
        key_down=lambda *a, **k: None,
        middle_click=lambda *a, **k: None,
        model=types.SimpleNamespace(active_tab=0, current_path="/tmp", tabs=["/tmp"], cards=()),
        next_tab_id=[1],
        notebook=types.SimpleNamespace(GetSelection=lambda: 0, SetPageText=lambda *a: None, GetPageCount=lambda: 1),
        operation=lambda *a, **k: None,
        operation_supported=lambda *a, **k: True,
        path=_Widget(),
        path_label=_Widget(),
        render_for_tab=lambda *a, **k: None,
        tabs=[tab],
        wx=types.SimpleNamespace(
            Panel=lambda *a, **k: object(),
            Notebook=lambda *a, **k: _FilterNotebook(),
            ListCtrl=lambda *a, **k: object(),
        ),
        provider_filters=(),
        plugin_filters=(),
    )
    return view, tab


@pytest.mark.unit
def test_back_forward_parent_relabel_even_when_listing_is_dead(monkeypatch):
    from hpc_gui import wx_remote_files_listing as listing
    from hpc_gui.core import i18n

    i18n.set_language("en")
    view, _tab = _build_view()
    listing.install_listing(view)

    view.btn_back.label = "Geri"
    view.btn_forward.label = "Ileri"
    view.btn_up.label = "Ust Dizin"

    view.refresh_labels()

    # The listing raises RuntimeError in this fixture, so a label written inside
    # that try block would keep the Turkish text and fail here.
    assert view.btn_back.label != "Geri"
    assert view.btn_forward.label != "Ileri"
    assert view.btn_up.label != "Ust Dizin"


@pytest.mark.unit
def test_filter_tab_texts_relabel_even_when_listing_is_dead():
    from hpc_gui import wx_remote_files_listing as listing
    from hpc_gui.core import i18n

    i18n.set_language("en")
    view, tab = _build_view()
    listing.install_listing(view)

    view.refresh_labels()

    assert tab["filter_notebook"].texts, "filter tab labels were not written"
