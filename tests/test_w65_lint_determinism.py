from hpc_gui.plugin_engines.openfoam_lint.api import lint_files, lint_paths
from hpc_gui.plugins.openfoam_lint.cli import _lint_paths


def test_lint_files_json_is_stable_across_mapping_order():
    items = [
        ("system/fvSolution", "solvers { p { solver PCG } }"),
        ("system/controlDict", "application simpleFoam\n"),
    ]
    forward = lint_files(dict(items), case_context=False)
    reverse = lint_files(dict(reversed(items)), case_context=False)
    assert forward.to_json() == reverse.to_json()


def test_standalone_cli_matches_engine_diagnostics_for_path_order(tmp_path):
    first = tmp_path / "controlDict"
    second = tmp_path / "fvSolution"
    first.write_text("application simpleFoam\n", encoding="utf-8")
    second.write_text("solvers { p { solver PCG } }", encoding="utf-8")
    paths = [str(first), str(second)]

    cli_forward = _lint_paths(paths)
    cli_reverse = _lint_paths(list(reversed(paths)))
    engine = lint_paths(paths)

    assert cli_forward == cli_reverse
    assert [
        (item["rule"], item["severity"], item["certainty"], item["file"],
         item["line"], item["column"], item["message"], item["fix_preview"])
        for item in cli_forward
    ] == [
        (item.rule_id, item.severity, item.confidence, item.path, item.line,
         item.column, item.message, item.suggested_fix)
        for item in engine.diagnostics
    ]
