"""OpenFOAM Visual Case Studio trusted-tool descriptor."""


def create_plugin():
    return {
        "id": "org.hpcclient.openfoamcasestudio",
        "title": "OpenFOAM Visual Case Studio",
        "description": "OpenFOAM.com v2312 and limited v1912 case workspace with source-preserving dictionaries and draft-only workflows.",
        "wx_page_factory": _wx_page_factory,
        "qt_page_factory": _qt_page_factory,
    }


def _wx_page_factory(parent=None, *, plugin, session_state=None, initial_path=None, remote=False, **_kwargs):
    from .wx_page import create_wx_page
    return create_wx_page(
        parent=parent, plugin=plugin, session_state=session_state,
        initial_path=initial_path, remote=remote, action=_kwargs.get("action"),
    )


def _qt_page_factory(parent=None, *, plugin, session_state=None, initial_path=None, remote=False, **_kwargs):
    from .qt_page import create_qt_page
    return create_qt_page(
        parent=parent, plugin=plugin, session_state=session_state,
        initial_path=initial_path, remote=remote, action=_kwargs.get("action"),
    )
