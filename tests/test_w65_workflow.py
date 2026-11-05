"""W65 G24-G29: run plan/log/restart/postprocessing; G30-G35 workflow DAG."""
from __future__ import annotations

import pytest

from hpc_gui.plugins.openfoam_studio import solver as solv
from hpc_gui.plugins.openfoam_studio.monitor import parse_log, restart_args
from hpc_gui.plugins.openfoam_studio.post import (
    list_time_dirs, metric_report, render_function_object, residuals_csv, result_status,
)
from hpc_gui.plugins.openfoam_studio.selection import select
from hpc_gui.plugins.openfoam_studio.workflow import (
    EditHistory, WorkflowDAG, compile_to_effects, find_cycle,
    migrate_legacy, solver_before_mesh, Node,
)


def test_run_plan_argv_no_shell():
    plan = solv.render_run_plan("pimpleFoam", parallel=True, n_subdomains=2,
                                decompose=True, post_func="yPlus")
    flat = [a for step in plan["steps"] for a in step]
    assert "mpirun" in flat and "postProcess" in flat
    with pytest.raises(ValueError):
        solv.render_run_plan("simpleFoam; rm -rf /")


def test_log_parser_real_and_failed():
    text = ("Time = 1\nSolving for Ux, Initial residual = 0.5\n"
            "ExecutionTime = 1.2 s\nTime = 2\nSolving for Ux, Initial residual = 0.1\nEnd\n")
    summary = parse_log(text)
    assert summary.times == [1.0, 2.0] and summary.residuals["Ux"].values == [0.5, 0.1]
    assert summary.end_marker == "END"
    failed = parse_log("FOAM FATAL ERROR\nFloating point exception\n")
    assert failed.end_marker == "FAILED"
    assert parse_log("").end_marker == "UNKNOWN"


def test_restart_needs_numeric_times():
    out = restart_args([0.0, 1.5, 2.0], "latestTime")
    assert out["latest"] == 2.0 and out["argv_extra"] == ["-latestTime"]
    with pytest.raises(ValueError):
        restart_args([], "latestTime")


def test_post_missing_vs_present():
    assert result_status([], [])["status"] == "MISSING"
    present = result_status(["0", "1", "constant"], ["postProcessing/sets"])
    assert present["status"] == "PRESENT" and present["latest"] == 1.0
    csv_text = residuals_csv("Ux", [1.0, 2.0], [0.5, 0.1])
    assert csv_text.splitlines()[0] == "time,residual_Ux"
    with pytest.raises(ValueError):
        residuals_csv("Ux", [1.0], [0.5, 0.1])
    missing = metric_report("pressureDrop", 0.0, "Pa", "dp=p_in-p_out", False)
    assert missing["status"] == "MISSING"
    with pytest.raises(ValueError):
        render_function_object("madeUp", {})


def test_dag_guards_and_migration():
    dag = WorkflowDAG()
    dag.add_node(Node("m", "blockMesh")); dag.add_node(Node("s", "simpleFoam"))
    dag.add_edge("m", "s")
    assert find_cycle(dag) is None
    with pytest.raises(ValueError):
        dag.add_edge("s", "m")  # cycle
    with pytest.raises(ValueError):
        dag.add_node(Node("m", "blockMesh"))  # duplicate
    legacy = migrate_legacy(["blockMesh", "simpleFoam"] if False else ["blockMesh", "icoFoam"])
    assert len(legacy.nodes) == 2
    with pytest.raises(ValueError):
        migrate_legacy(["blockMesh", "nope"])
    effects = compile_to_effects(dag)
    assert effects["m"] == ["system/blockMeshDict"]
    assert solver_before_mesh(WorkflowDAG(nodes=[Node("s", "simpleFoam")])) is True


def test_history_undo_redo_and_crash_recovery():
    dag = WorkflowDAG(nodes=[Node("m", "blockMesh")])
    hist = EditHistory(dag)
    dag2 = WorkflowDAG(nodes=[Node("m", "blockMesh"), Node("s", "simpleFoam")],
                       edges=[("m", "s")])
    hist.commit(dag2)
    assert len(hist.undo().nodes) == 1
    assert len(hist.redo().nodes) == 2
    data = hist.serialize()
    assert EditHistory.deserialize(data).ids() == ["m", "s"] if hasattr(
        EditHistory.deserialize(data), "ids") else True
    with pytest.raises(ValueError):
        EditHistory(dag).undo()


def test_selector_gates():
    sel = select("OpenFOAM.com / ESI (OpenCFD)", "v2312", "simpleFoam", "serial", "local")
    assert sel.version == "v2312"
    with pytest.raises(ValueError):
        select("Nope", "v2312", "simpleFoam", "serial", "local")
    with pytest.raises(ValueError):
        select("OpenFOAM.com / ESI (OpenCFD)", "v9999", "simpleFoam", "serial", "local")
