"""Wave 11 tests: plugin-delivered job templates."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hpc_gui.plugins.job_templates import (
    JobTemplate,
    JobTemplateError,
    TemplateVariable,
    load_job_templates,
    render_template,
)
from hpc_gui.plugins.storage import write_active_versions


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


TEMPLATE_BODY = (
    "#!/bin/bash\n"
    "#SBATCH --partition={{partition}}\n"
    "#SBATCH --cpus-per-task={{cpus}}\n"
    "#SBATCH --time={{time_limit}}\n"
    "fluent 3ddp -g -t{{cpus}} -i {{journal_file}}\n"
)

TEMPLATE_VARIABLES = [
    {"name": "partition", "type": "string", "required": True},
    {
        "name": "cpus",
        "type": "integer",
        "required": True,
        "default": 1,
        "minimum": 1,
        "maximum": 4096,
    },
    {"name": "time_limit", "type": "string", "required": True, "default": "01:00:00"},
    {"name": "journal_file", "type": "path", "required": True},
]


def install_template_plugin(
    root: Path,
    *,
    version: str = "0.2.0",
    body: str = TEMPLATE_BODY,
    variables=TEMPLATE_VARIABLES,
    broken_index=False,
    content_override: bytes | None = None,
):
    plugin_id = "org.hpcclient.fluent"
    pkg = root / "packages" / plugin_id / version
    pkg.mkdir(parents=True, exist_ok=True)
    payload = body.encode()
    (pkg / "templates").mkdir(exist_ok=True)
    (pkg / "templates" / "fluent_job.slurm.tpl").write_bytes(payload)
    if broken_index:
        (pkg / "templates" / "index.json").write_text("{broken", encoding="utf-8")
    else:
        index = {
            "schema_version": 1,
            "templates": [
                {
                    "id": "fluent-slurm-basic",
                    "name": "Fluent Slurm Batch",
                    "description": "Basic headless Fluent Slurm job.",
                    "scheduler": "slurm",
                    "application": "ansys-fluent",
                    "file_name": "fluent_job.slurm",
                    "content_path": "templates/fluent_job.slurm.tpl",
                    "sha256": sha256_bytes(content_override or payload),
                    "variables": variables,
                }
            ],
        }
        (pkg / "templates" / "index.json").write_text(json.dumps(index), encoding="utf-8")

    if not broken_index:
        index_bytes = (pkg / "templates" / "index.json").read_bytes()
        tpl_entry_files = [
            {
                "path": "templates/index.json",
                "sha256": sha256_bytes(index_bytes),
                "size": len(index_bytes),
                "role": "template-index",
            },
            {
                "path": "templates/fluent_job.slurm.tpl",
                "sha256": sha256_bytes(payload),
                "size": len(payload),
                "role": "template-content",
            },
        ]
    else:
        tpl_entry_files = [
            {"path": "templates/index.json", "sha256": "a" * 64, "size": 1, "role": "template-index"}
        ]

    manifest = {
        "schema_version": 1,
        "plugin_api": 1,
        "id": plugin_id,
        "name": "Fluent Journal Lint",
        "version": version,
        "publisher": "HPC Client GUI",
        "license": "MIT",
        "description": "Fluent lint and templates.",
        "requires_app": ">=1.3.0",
        "capabilities": ["job-template"],
        "entrypoints": {"job_templates": ["templates/index.json"]},
        "files": tpl_entry_files,
    }
    (pkg / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    write_active_versions({plugin_id: version}, root=root)


def make_template(**overrides) -> JobTemplate:
    defaults = dict(
        id="t1",
        name="Template One",
        scheduler="slurm",
        plugin_id="org.hpcclient.test",
        plugin_version="1.0.0",
        file_name="job.slurm",
        variables=(TemplateVariable(name="greeting", type="string", required=True),),
        content="#!/bin/bash\necho {{greeting}}\n",
    )
    defaults.update(overrides)
    return JobTemplate(**defaults)


def greeting_template() -> JobTemplate:
    return make_template(
        variables=(TemplateVariable(name="greeting", type="string", required=True),)
    )


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------


def test_load_installed_templates(tmp_path: Path):
    install_template_plugin(tmp_path)
    templates = load_job_templates(root=tmp_path, app_version="1.4.0")
    assert len(templates) == 1
    template = templates[0]
    assert template.id == "fluent-slurm-basic"
    assert template.plugin_id == "org.hpcclient.fluent"
    assert template.file_name == "fluent_job.slurm"
    assert [v.name for v in template.variables] == [
        "partition",
        "cpus",
        "time_limit",
        "journal_file",
    ]
    assert "{{partition}}" in template.content


def test_broken_template_index_is_skipped(tmp_path: Path):
    install_template_plugin(tmp_path, broken_index=True)
    assert load_job_templates(root=tmp_path, app_version="1.4.0") == []


def test_content_hash_mismatch_skips_pack(tmp_path: Path):
    install_template_plugin(tmp_path, content_override=b"different")
    assert load_job_templates(root=tmp_path, app_version="1.4.0") == []


def test_undeclared_placeholder_in_content_rejected(tmp_path: Path):
    install_template_plugin(tmp_path, body="{{mystery}}\n")
    assert load_job_templates(root=tmp_path, app_version="1.4.0") == []


def test_incompatible_plugin_not_loaded(tmp_path: Path):
    install_template_plugin(tmp_path)
    assert load_job_templates(root=tmp_path, app_version="0.9.0") == []


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_valid_render():
    out = render_template(make_template(), {"greeting": "hello"})
    assert out == "#!/bin/bash\necho hello\n"


def test_missing_required_variable_rejected():
    with pytest.raises(JobTemplateError, match="missing required"):
        render_template(greeting_template(), {})


def test_integer_constraint_violation():
    template = make_template(
        variables=(
            TemplateVariable(name="n", type="integer", default=4, minimum=1, maximum=8),
        ),
        content="{{n}}\n",
    )
    assert render_template(template, {}).strip() == "4"
    with pytest.raises(JobTemplateError, match="must be <="):
        render_template(template, {"n": 9})
    with pytest.raises(JobTemplateError, match="must be an integer"):
        render_template(template, {"n": "many"})


def test_choice_constraint():
    template = make_template(
        variables=(
            TemplateVariable(name="mode", type="choice", choices=["a", "b"], required=True),
        ),
        content="{{mode}}\n",
    )
    assert render_template(template, {"mode": "b"}).strip() == "b"
    with pytest.raises(JobTemplateError, match="must be one of"):
        render_template(template, {"mode": "z"})


def test_unknown_supplied_value_rejected():
    with pytest.raises(JobTemplateError, match="unknown value"):
        render_template(greeting_template(), {"greeting": "hi", "nope": 1})


def test_defaults_fill_optional_placeholders():
    template = make_template(
        variables=(TemplateVariable(name="greeting", type="string", default="hi"),)
    )
    assert render_template(template, {}).strip().endswith("echo hi")


def test_render_never_executes(monkeypatch):
    monkeypatch.setattr(
        "builtins.eval",
        lambda *a, **k: (_ for _ in ()).throw(AssertionError("eval called")),
    )
    template = make_template(variables=greeting_template().variables)
    rendered = render_template(
        template, {"greeting": "__import__('os').system('true')"}
    )
    assert "__import__" in rendered  # plain text substitution only


# ---------------------------------------------------------------------------
# Real published plugin + editor flow
# ---------------------------------------------------------------------------


PLUGIN_REPO = Path(__file__).resolve().parents[2] / "hpc-client-gui-plugins"
FLUENT_DIR = PLUGIN_REPO / "plugins" / "fluent" / "0.2.0"

requires_repo = pytest.mark.skipif(
    not FLUENT_DIR.is_dir(), reason="sibling plugin repo missing"
)


@requires_repo
def test_real_fluent_template_loads_and_renders(tmp_path: Path):
    import shutil

    pkg_root = tmp_path / "packages" / "org.hpcclient.fluent" / "0.2.0"
    pkg_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(FLUENT_DIR, pkg_root)
    write_active_versions({"org.hpcclient.fluent": "0.2.0"}, root=tmp_path)

    templates = load_job_templates(root=tmp_path, app_version="1.4.0")
    assert len(templates) >= 1
    template = next(t for t in templates if t.id == "fluent-slurm-basic")
    values = {"partition": "long"}
    for variable in template.variables:
        if variable.default is not None and variable.name not in values:
            values[variable.name] = variable.default
        elif variable.required and variable.name not in values:
            values[variable.name] = "x"
    rendered = render_template(template, values)
    assert "{{" not in rendered
    assert "--partition=long" in rendered
