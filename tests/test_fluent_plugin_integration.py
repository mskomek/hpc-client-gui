"""Wave 09 integration tests: the real published Fluent lint plugin.

The plugin lives in the sibling checkout ``hpc-client-gui-plugins``; tests
that need it skip automatically when that repository is not present. No
Fluent process is ever launched and no network access happens: files are
read from disk and served to the installer through an injected fetcher.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from hpc_gui.lint.engine import lint_text
from hpc_gui.lint.models import LintContext, Severity
from hpc_gui.lint.rulepack import parse_rule_pack
from hpc_gui.plugins.registry_client import OFFICIAL_RAW_BASE, OFFICIAL_REGISTRY_URL
from hpc_gui.plugins.compatibility import is_app_compatible
from packaging.version import Version

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "fluent"
PLUGIN_REPO = Path(__file__).resolve().parents[2] / "hpc-client-gui-plugins"

requires_plugin_repo = pytest.mark.skipif(
    not (PLUGIN_REPO / "registry.json").is_file(),
    reason="sibling hpc-client-gui-plugins checkout not present",
)


def latest_fluent_dir() -> Path:
    registry = json.loads((PLUGIN_REPO / "registry.json").read_text(encoding="utf-8"))
    entries = [
        entry for entry in registry["plugins"]
        if entry["id"] == "org.hpcclient.fluent"
        and is_app_compatible(entry["requires_app"], "1.5.8")
    ]
    latest = max(entries, key=lambda entry: Version(entry["version"]))
    return PLUGIN_REPO / Path(latest["manifest_path"]).parent


def load_published_pack() -> "object":
    fluent_dir = latest_fluent_dir()
    manifest = json.loads((fluent_dir / "manifest.json").read_text(encoding="utf-8"))
    index_rel = manifest["entrypoints"]["lint_index"]
    index = json.loads((fluent_dir / index_rel).read_text(encoding="utf-8"))
    return parse_rule_pack(
        index,
        plugin_id=manifest["id"],
        plugin_version=manifest["version"],
        package_dir=fluent_dir,
    )


def rule_ids(pack, diags):
    _ = pack
    return [d.rule_id for d in diags]


@requires_plugin_repo
def test_pack_metadata_and_rules():
    pack = load_published_pack()
    assert pack.linter_id == "fluent-journal"
    assert pack.matches("case.jou")
    assert not pack.matches("job.slurm")
    ids = {rule.id for rule in pack.rules}
    assert {"FLUENT001", "FLUENT002", "FLUENT003", "FLUENT010", "FLUENT011"} <= ids


@requires_plugin_repo
def test_clean_fixture_has_no_errors():
    pack = load_published_pack()
    text = (FIXTURES / "clean_25_2.jou").read_text(encoding="utf-8")
    context = LintContext(
        application_version="25.2",
        remote_platform="linux",
    )
    diags = lint_text(text, file_name="run.jou", rule_pack=pack, context=context)
    errors = [d for d in diags if d.severity is Severity.ERROR]
    assert errors == []
    # FLUENT011 portability info is expected for the absolute scratch path.
    assert "FLUENT011" in rule_ids(pack, diags)


@requires_plugin_repo
def test_missing_tui_version_detected():
    pack = load_published_pack()
    text = "/display set-lsd-bc\n/solve/initialize/hyb-initialization\n"
    diags = lint_text(text, file_name="run.jou", rule_pack=pack)
    assert "FLUENT001" in rule_ids(pack, diags)


@requires_plugin_repo
def test_wrong_declared_version_flagged_only_for_25_2_target():
    pack = load_published_pack()
    text = '/file/set-tui-version "24.1"\n/display set-lsd-bc\n'

    with_target = LintContext(application_version="25.2")
    diags = lint_text(text, file_name="a.jou", rule_pack=pack, context=with_target)
    assert "FLUENT002" in rule_ids(pack, diags)

    other_target = LintContext(application_version="24.1")
    diags_other = lint_text(text, file_name="a.jou", rule_pack=pack, context=other_target)
    assert "FLUENT002" not in rule_ids(pack, diags_other)

    no_context = lint_text(text, file_name="a.jou", rule_pack=pack, context=None)
    assert "FLUENT002" not in rule_ids(pack, no_context)


@requires_plugin_repo
def test_late_tui_version_is_informational_and_conservative():
    pack = load_published_pack()
    text = (FIXTURES / "late_tui_version.jou").read_text(encoding="utf-8")
    context = LintContext(application_version="25.2")
    diags = lint_text(text, file_name="a.jou", rule_pack=pack, context=context)
    assert "FLUENT003" in rule_ids(pack, diags)

    # Proper ordering stays silent.
    good = '/file/set-tui-version "25.2"\n/solve/initialize/hyb-initialization\n'
    assert lint_text(good, file_name="a.jou", rule_pack=pack, context=context) == [] or (
        "FLUENT003" not in rule_ids(pack, lint_text(good, file_name="a.jou", rule_pack=pack, context=context))
    )


@requires_plugin_repo
def test_windows_path_warning_is_context_sensitive():
    pack = load_published_pack()
    text = (FIXTURES / "windows_path.jou").read_text(encoding="utf-8")

    linux_remote = LintContext(remote_platform="linux")
    flagged = lint_text(text, file_name="a.jou", rule_pack=pack, context=linux_remote)
    assert "FLUENT010" in rule_ids(pack, flagged)

    # Without platform context the rule must be skipped (no false positives).
    unflagged = lint_text(text, file_name="a.jou", rule_pack=pack, context=None)
    assert "FLUENT010" not in rule_ids(pack, unflagged)

    windows_local = LintContext(remote_platform="windows")
    local = lint_text(text, file_name="a.jou", rule_pack=pack, context=windows_local)
    assert "FLUENT010" not in rule_ids(pack, local)


@requires_plugin_repo
def test_absolute_linux_path_portability_info():
    pack = load_published_pack()
    text = (FIXTURES / "absolute_linux_path.jou").read_text(encoding="utf-8")
    diags = lint_text(text, file_name="a.jou", rule_pack=pack)
    assert "FLUENT011" in rule_ids(pack, diags)
    matching = [d for d in diags if d.rule_id == "FLUENT011"]
    assert all(d.severity is Severity.INFO for d in matching)


@requires_plugin_repo
def test_registry_entry_installs_via_exact_file_protocol(tmp_path: Path):
    """Full installer round-trip using the real published bytes."""
    from hpc_gui.plugins.installer import install_plugin_from_registry
    from hpc_gui.plugins.state import read_installed_state

    registry = json.loads((PLUGIN_REPO / "registry.json").read_text(encoding="utf-8"))
    entries = [p for p in registry["plugins"] if p["id"] == "org.hpcclient.fluent"]
    entry = max(entries, key=lambda item: Version(item["version"]))

    responses = {}

    def fetch(url: str, max_bytes: int) -> bytes:
        if url == OFFICIAL_REGISTRY_URL:
            return (PLUGIN_REPO / "registry.json").read_bytes()
        assert url.startswith(OFFICIAL_RAW_BASE)
        rel = url[len(OFFICIAL_RAW_BASE) :]
        return (PLUGIN_REPO / rel).read_bytes()

    responses  # unused; fetch reads directly from the sibling checkout

    result = install_plugin_from_registry(
        entry,
        root=tmp_path,
        app_version="1.5.8",
        fetcher=fetch,
    )
    assert result.activated is True
    assert "org.hpcclient.fluent" in read_installed_state(tmp_path)

    packs = __import__(
        "hpc_gui.lint.rulepack", fromlist=["load_lint_packs"]
    ).load_lint_packs(root=tmp_path, app_version="1.4.0")
    assert [p.linter_id for p in packs] == ["fluent-journal"]
    assert entry["version"] == "0.2.0"


@requires_plugin_repo
def test_latest_fluent_template_renders_after_install(tmp_path: Path):
    from hpc_gui.plugins.installer import install_plugin_from_registry
    from hpc_gui.plugins.job_templates import load_job_templates, render_template

    registry = json.loads((PLUGIN_REPO / "registry.json").read_text(encoding="utf-8"))
    entry = max(
        (item for item in registry["plugins"] if item["id"] == "org.hpcclient.fluent"),
        key=lambda item: Version(item["version"]),
    )

    def fetch(url: str, max_bytes: int) -> bytes:
        source = (PLUGIN_REPO / "registry.json") if url == OFFICIAL_REGISTRY_URL else PLUGIN_REPO / url[len(OFFICIAL_RAW_BASE):]
        payload = source.read_bytes()
        assert len(payload) <= max_bytes
        return payload

    install_plugin_from_registry(entry, root=tmp_path, app_version="1.5.8", fetcher=fetch)
    template = load_job_templates(root=tmp_path, app_version="1.5.8")[0]
    rendered = render_template(template, {
        "partition": "standard",
        "cpus": 8,
        "time_limit": "02:00:00",
        "fluent_version": "v252",
        "journal_file": "case.jou",
        "journal_base": "case",
    })
    assert "#SBATCH --partition=standard" in rendered
    assert "fluent 3ddp -g -t8 -i case.jou" in rendered
    assert "{{" not in rendered and "}}" not in rendered
