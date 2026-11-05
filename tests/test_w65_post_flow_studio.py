'''Focused UNIT D regression tests for W65 post, flow, and studio (W65).'''
from __future__ import annotations
import pytest
from hpc_gui.openfoam_v2312 import flow, postprocess, studio
def _view(**overrides):
    base = {"name": "residuals", "command": "postProcess", "functions": (), "artifacts": ("residuals-log",)}
    base.update(overrides)
    return postprocess.PostView(**base)
def _node(**overrides):
    base = {"node_id": "n1", "stage": "mesh", "produces": ("mesh-state",), "consumes": ()}
    base.update(overrides)
    return flow.FlowNode(**base)
def _card(**overrides):
    base = {"page": "results", "title": "Results", "action": "open_results_navigator"}
    base.update(overrides)
    return studio.PageCard(**base)
@pytest.mark.unit
def test_valid_post_view_passes() -> None:
    assert postprocess.validate_post(_view()) == ()
@pytest.mark.unit
def test_post_view_round_trip() -> None:
    assert postprocess.PostView.from_dict(_view().to_dict()) == _view()
@pytest.mark.unit
def test_post_view_malformed_lists_rejected() -> None:
    with pytest.raises(ValueError):
        postprocess.PostView.from_dict({"name": "x", "functions": "probes"})
@pytest.mark.unit
def test_unknown_post_command_rejected() -> None:
    assert any("command" in e for e in postprocess.validate_post(_view(command="paraview")))
@pytest.mark.unit
def test_unknown_function_and_artifact_rejected() -> None:
    errors = postprocess.validate_post(_view(functions=("teleport",), artifacts=("nope",)))
    assert any("function object" in e for e in errors)
    assert any("artifact" in e for e in errors)
@pytest.mark.unit
def test_empty_artifacts_rejected() -> None:
    assert any("no result artifacts" in e for e in postprocess.validate_post(_view(artifacts=())))
@pytest.mark.unit
def test_case_vtk_needs_foamtovtk() -> None:
    assert any("foamToVTK" in e for e in postprocess.validate_post(_view(artifacts=("case-vtk",))))
    assert postprocess.validate_post(_view(command="foamToVTK", artifacts=("case-vtk",))) == ()
@pytest.mark.unit
def test_forces_artifact_needs_forces_function() -> None:
    assert any("forces" in e for e in postprocess.validate_post(_view(artifacts=("forces-dat",))))
    assert postprocess.validate_post(_view(functions=("forces",), artifacts=("forces-dat",))) == ()
@pytest.mark.unit
def test_report_needs_methodology() -> None:
    assert any("methodology" in e for e in postprocess.validate_post(_view(artifacts=("report-md",))))
    view = _view(functions=("probes",), artifacts=("probes-csv", "report-md"), methodology="probe means over time")
    assert postprocess.validate_post(view) == ()
@pytest.mark.unit
def test_missing_artifacts_never_zero() -> None:
    view = _view(artifacts=("residuals-log", "report-md"))
    assert postprocess.missing_artifacts(view, {"residuals-log": True}) == ("report-md",)
    assert postprocess.missing_artifacts(view, {"residuals-log": True, "report-md": True}) == ()
@pytest.mark.unit
def test_valid_flow_passes() -> None:
    nodes = (
        _node(node_id="m", stage="mesh", produces=("mesh-state",)),
        _node(node_id="c", stage="check", produces=("mesh-ok",), consumes=("mesh-state",)),
        _node(node_id="s", stage="solve", produces=("fields",), consumes=("mesh-ok",)),
        _node(node_id="p", stage="post", produces=("report-md",), consumes=("fields",)),
    )
    assert flow.validate_flow(nodes) == ()
@pytest.mark.unit
def test_flow_node_round_trip() -> None:
    assert flow.FlowNode.from_dict(_node().to_dict()) == _node()
@pytest.mark.unit
def test_empty_flow_rejected() -> None:
    assert any("empty" in e for e in flow.validate_flow(()))
@pytest.mark.unit
def test_duplicate_node_ids_rejected() -> None:
    assert any("duplicate node id" in e for e in flow.validate_flow((_node(), _node())))
@pytest.mark.unit
def test_unknown_stage_rejected() -> None:
    assert any("unknown pipeline stage" in e for e in flow.validate_flow((_node(stage="warp"),)))
@pytest.mark.unit
def test_solve_before_mesh_rejected() -> None:
    assert any("precedes any mesh" in e for e in flow.validate_flow((_node(node_id="s", stage="solve"),)))
@pytest.mark.unit
def test_post_before_solve_rejected() -> None:
    nodes = (_node(node_id="m", stage="mesh", produces=("mesh-state",)), _node(node_id="p", stage="post"))
    assert any("precedes any solve" in e for e in flow.validate_flow(nodes))
@pytest.mark.unit
def test_stale_consumer_rejected() -> None:
    assert any("no earlier producer" in e for e in flow.validate_flow((_node(consumes=("ghost",)),)))
@pytest.mark.unit
def test_duplicate_destructive_mesh_needs_review() -> None:
    first = _node(node_id="m1", destructive=True)
    second = _node(node_id="m2", destructive=True)
    assert any("needs review" in e for e in flow.validate_flow((first, second)))
    reviewed = _node(node_id="m1", destructive=True, needs_review=True)
    second_reviewed = _node(node_id="m2", destructive=True, needs_review=True)
    assert flow.validate_flow((reviewed, second_reviewed)) == ()
@pytest.mark.unit
def test_legacy_import_maps_and_reports_unknown() -> None:
    stages, unknown = flow.from_legacy(("blockMesh", "checkMesh", "simpleFoam", "frobnicate"))
    assert stages == ("mesh", "check", "solve")
    assert unknown == ("frobnicate",)
@pytest.mark.unit
def test_journey_templates_match() -> None:
    for journey in ("T1", "T2", "T3", "T4", "T5", "T6", "T7", "T8"):
        assert flow.validate_journey(journey, flow.JOURNEY_SPECS[journey][2]) == ()
    assert any("unknown journey" in e for e in flow.validate_journey("T9", ("mesh",)))
    assert any("expects" in e for e in flow.validate_journey("T1", ("solve",)))
@pytest.mark.unit
def test_valid_page_card_passes() -> None:
    assert studio.validate_page(_card()) == ()
@pytest.mark.unit
def test_page_card_round_trip() -> None:
    assert studio.PageCard.from_dict(_card().to_dict()) == _card()
@pytest.mark.unit
def test_unknown_page_empty_title_and_action_rejected() -> None:
    assert any("unknown studio page" in e for e in studio.validate_page(_card(page="holodeck")))
    assert any("title" in e for e in studio.validate_page(_card(title="  ")))
    assert any("backing action" in e for e in studio.validate_page(_card(action="  ")))
@pytest.mark.unit
def test_journey_pages_match_and_guard_required() -> None:
    for journey, pages in studio.JOURNEY_PAGES.items():
        assert studio.validate_journey_pages(journey, pages) == ()
    assert any("unknown journey" in e for e in studio.validate_journey_pages("T9", ("results",)))
    assert any("unknown studio page" in e for e in studio.validate_journey_pages("T1", ("results", "holodeck")))
    assert any("required pages" in e for e in studio.validate_journey_pages("T1", ("results",)))
    assert any("duplicate page" in e for e in studio.validate_journey_pages("T1", ("results", "results", "source-editor", "validation")))
    assert any("expects" in e for e in studio.validate_journey_pages("T1", ("source-editor", "validation")))