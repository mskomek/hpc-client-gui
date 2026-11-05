"""Contract checks for the generated TRUBA v2312 template."""

from pathlib import Path
import importlib.util


def _template() -> str:
    root = Path(__file__).resolve().parents[1]
    path = root / "tools" / "build_w65_openfoam_candidates.py"
    spec = importlib.util.spec_from_file_location("w65_candidate_builder", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module._TRUBA_TEMPLATE


def test_truba_template_validates_loaded_runtime_without_errexit_false_failure():
    text = _template()

    assert "if module load apps/openfoam/v2312-2025; then" in text
    assert "module_rc=$?" in text
    assert "expected_project_version=v2312" in text
    assert "expected_project_dir=/arf/sw/apps/openfoam/v2312-2025" in text
    assert "${WM_PROJECT_VERSION:-}" in text
    assert "${WM_PROJECT_DIR:-}" in text
    assert "command -v \"$required_command\"" in text
    assert 'source "$WM_PROJECT_DIR/etc/bashrc"' not in text
    assert text.index("module load apps/openfoam/v2312-2025") < text.index("set -u")
