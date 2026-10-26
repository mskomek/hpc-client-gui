"""Flow-card model + drag/drop reorder + lazy wx flow panel (W65 UI-012, G33).

Pure-data layer is headless-testable; wx widgets are built lazily inside
:func:`build_flow_panel` so engine tests never need a display. Every
button binds a caller-supplied callback or is rendered disabled with an
explanatory tooltip — no dead controls. This panel is not yet registered in
the host's plugin manifest/action dispatch; no new toolkit fork.
"""

from __future__ import annotations

from dataclasses import dataclass, field

TOOL_TITLES = {
    "blockMesh": ("Block Mesh", "Blok Ağ"),
    "snappyHexMesh": ("Snappy Mesh", "Snappy Ağ"),
    "checkMesh": ("Check Mesh", "Ağ Denetimi"),
    "simpleFoam": ("Simple Foam (steady)", "Simple Foam (daimi)"),
    "pimpleFoam": ("Pimple Foam (transient)", "Pimple Foam (geçici)"),
    "chtMultiRegionSimpleFoam": ("CHT Solver", "CHT Çözücü"),
    "decomposePar": ("Decompose (parallel)", "Ayrıştır (paralel)"),
    "reconstructPar": ("Reconstruct", "Birleştir"),
    "postProcess": ("Post-Process", "Art İşleme"),
    "foamToVTK": ("Export VTK", "VTK Dışa Aktar"),
    "surfaceFeatureExtract": ("Feature Extract", "Özellik Çıkar"),
    "splitMeshRegions": ("Split Regions", "Bölgeleri Ayır"),
}


@dataclass
class FlowCard:
    node_id: str
    tool: str
    title_en: str = ""
    title_tr: str = ""
    status: str = "DRAFT"  # DRAFT | VALID | BLOCKED | RAW-ADVANCED
    detail: str = ""
    params_summary: dict = field(default_factory=dict)


def cards_for_dag(dag, lint_status: dict | None = None) -> list[FlowCard]:
    cards = []
    for node in dag.nodes:
        en, tr = TOOL_TITLES.get(node.tool, (node.tool, node.tool))
        status = (lint_status or {}).get(node.node_id, "DRAFT")
        cards.append(FlowCard(node.node_id, node.tool, en, tr, status,
                              detail=f"{node.tool} {len(node.params)} param(s)",
                              params_summary=dict(node.params)))
    return cards


def move_node(dag, node_id: str, new_index: int):
    """Drag/drop reorder model: returns a NEW dag with the node moved.

    Edges are preserved; callers must re-run the compiler guards
    (solver-before-mesh, cycles) on the result.
    """
    from hpc_gui.plugins.openfoam_studio.workflow import WorkflowDAG
    ids = dag.ids()
    if node_id not in ids:
        raise ValueError(f"cannot move unknown node '{node_id}'")
    if not 0 <= new_index < len(ids):
        raise ValueError(f"drop index {new_index} out of range")
    nodes = [n for n in dag.nodes if n.node_id != node_id]
    moving = next(n for n in dag.nodes if n.node_id == node_id)
    nodes.insert(new_index, moving)
    return WorkflowDAG(nodes=nodes, edges=list(dag.edges))


def build_flow_panel(parent, dag, *, on_select=None, on_move=None,
                     on_preview=None, lang: str = "en"):
    """Lazy wx flow panel: vertical 3-pane center column of node cards.

    Requires wx at call time only. Every button is wired to the supplied
    callback or disabled with a tooltip explaining the missing action.
    """
    import wx

    from hpc_gui.plugins.openfoam_studio.wx_panels import LABELS
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    cards = cards_for_dag(dag)
    for card in cards:
        box = wx.StaticBoxSizer(wx.StaticBox(panel, label=card.title_en
                                             if lang == "en" else card.title_tr),
                                wx.VERTICAL)
        title = wx.StaticText(panel, label=f"{card.tool} [{card.status}]")
        title.SetToolTip(f"{card.node_id}: {card.detail}")
        box.Add(title, 0, wx.ALL, 4)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, callback, tip in (
                ("Select", on_select, "select node in inspector"),
                ("Preview", on_preview, "preview node file diff"),
                ("Move", on_move, "drag/drop reorder via move_node")):
            btn = wx.Button(panel, label=label)
            if callback is None:
                btn.Disable()
                btn.SetToolTip(f"{tip}{LABELS['no_handler'][lang]}")
            else:
                btn.SetToolTip(tip)
                btn.Bind(wx.EVT_BUTTON,
                         lambda _e, nid=card.node_id, cb=callback: cb(nid))
            row.Add(btn, 0, wx.ALL, 2)
        box.Add(row, 0, wx.EXPAND)
        sizer.Add(box, 0, wx.EXPAND | wx.ALL, 4)
    panel.SetSizer(sizer)
    return panel
