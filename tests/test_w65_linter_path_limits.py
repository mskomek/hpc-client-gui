from hpc_gui.plugin_engines.openfoam_lint import api


def test_lint_paths_bounds_generator_consumption(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "MAX_CASE_FILES", 2)
    visited = []

    def paths():
        for index in range(1000):
            visited.append(index)
            yield tmp_path / f"missing-{index}"

    result = api.lint_paths(paths())

    assert visited == [0, 1, 2]
    assert sum(d.rule_id == "OF-CASE-006" for d in result.diagnostics) == 2
    limit = [d for d in result.diagnostics if d.rule_id == "OF-CASE-005"]
    assert len(limit) == 1
    assert limit[0].path == "<selection>"
    assert "2" in limit[0].message
