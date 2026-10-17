"""Cross-repository Plugin API v1 contract test.

Runs against a real checkout of the official plugin registry
(https://github.com/mskomek/hpc-client-gui-plugins). Set
``HPC_GUI_CONTRACT_REPO`` to the checkout path to enable it; CI checks the
repository out into a sibling directory. All downloads are served from the
local checkout through an injected fetcher, so no network access and no
GitHub token are needed at test time.
"""

from __future__ import annotations

pytest_plugins = ('support.test_plugin_contract_shared',)
from support.test_plugin_contract_shared import (
    CONTRACT_APP_VERSION,
    Path,
    REPO,
    _install,
    activate_version,
    find_registry_entry,
    load_installed_plugins,
    pytest,
)

pytestmark = pytest.mark.skipif(
    not REPO or not Path(REPO).is_dir(),
    reason="HPC_GUI_CONTRACT_REPO does not point to an official plugins checkout",
)

@pytest.mark.integration
def test_fluent_latest_compatible_and_loads(registry, local_fetcher, tmp_path: Path):
    entry = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version=CONTRACT_APP_VERSION
    )
    assert entry["version"] == "0.3.0"
    # Explicit selection still resolves exactly.
    old = find_registry_entry(
        registry, "org.hpcclient.fluent", version="0.1.0", app_version=CONTRACT_APP_VERSION
    )
    assert old["version"] == "0.1.0"

    result = _install(local_fetcher, tmp_path, entry)
    assert result.installed.manifest.version == "0.3.0"
    capabilities = set(result.installed.manifest.capabilities)
    assert {"lint-rules", "job-template"} <= capabilities

@pytest.mark.integration
def test_fluent_lint_rules_run(registry, local_fetcher, tmp_path: Path):
    from hpc_gui.lint.engine import lint_text
    from hpc_gui.lint.rulepack import load_lint_packs

    entry = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version=CONTRACT_APP_VERSION
    )
    _install(local_fetcher, tmp_path, entry)

    packs = load_lint_packs(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    fluent_packs = [
        pack for pack in packs if pack.plugin_id == "org.hpcclient.fluent"
    ]
    assert fluent_packs, "Fluent lint pack must load"

    journal_without_tui = "/solve/iterate 100\n"
    diagnostics = []
    for pack in fluent_packs:
        diagnostics.extend(
            lint_text(journal_without_tui, file_name="run.jou", rule_pack=pack)
        )
    rule_ids = {diagnostic.rule_id for diagnostic in diagnostics}
    assert any(rule_id.startswith("FLUENT") for rule_id in rule_ids), sorted(rule_ids)

@pytest.mark.integration
def test_fluent_slurm_template_is_plain_substitution(
    registry, local_fetcher, tmp_path: Path
):
    from hpc_gui.plugins.job_templates import load_job_templates, render_template

    entry = find_registry_entry(
        registry, "org.hpcclient.fluent", app_version=CONTRACT_APP_VERSION
    )
    result_version = _install(local_fetcher, tmp_path, entry).installed.manifest.version

    templates = load_job_templates(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    assert templates, "Fluent job template must load"
    template = next(t for t in templates if t.id == "fluent-slurm-basic")

    values = {
        "partition": "long",
        "cpus": 16,
        "time_limit": "04:00:00",
        "fluent_version": "v252",
        "journal_file": "case.jou",
        "journal_base": "fluent_run",
    }
    rendered = render_template(template, values)

    # Plain substitution proof: manual replacement over the exact installed
    # template bytes must produce identical output. No shell/format
    # evaluation happens during rendering.
    body = (
        tmp_path
        / "packages"
        / "org.hpcclient.fluent"
        / result_version
        / "templates"
        / "fluent_job.slurm.tpl"
    ).read_text(encoding="utf-8")
    expected = body
    for key, value in values.items():
        expected = expected.replace("{{" + key + "}}", str(value))
    assert rendered == expected
    assert "{{" not in rendered

    # Template content never executes anything by itself: no command is run
    # during rendering; this assertion documents the invariant explicitly.
    assert "#!/bin/bash" in rendered

@pytest.mark.integration
def test_fluent_update_then_rollback_preserves_versions(
    registry, local_fetcher, tmp_path: Path
):
    old = find_registry_entry(
        registry, "org.hpcclient.fluent", version="0.1.0", app_version=CONTRACT_APP_VERSION
    )
    new = find_registry_entry(
        registry, "org.hpcclient.fluent", version="0.2.0", app_version=CONTRACT_APP_VERSION
    )

    _install(local_fetcher, tmp_path, old)
    packages = tmp_path / "packages" / "org.hpcclient.fluent"
    assert (packages / "0.1.0").is_dir()

    _install(local_fetcher, tmp_path, new)
    loaded = load_installed_plugins(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    active_fluent = [
        p.manifest.version for p in loaded.plugins if p.manifest.id == "org.hpcclient.fluent"
    ]
    assert active_fluent == ["0.2.0"]
    assert (packages / "0.1.0").is_dir()  # kept for rollback

    activate_version("org.hpcclient.fluent", "0.1.0", root=tmp_path)
    loaded = load_installed_plugins(root=tmp_path, app_version=CONTRACT_APP_VERSION)
    active_fluent = [
        p.manifest.version for p in loaded.plugins if p.manifest.id == "org.hpcclient.fluent"
    ]
    assert active_fluent == ["0.1.0"]

@pytest.mark.audit
def test_contract_metadata_documented(plugins_repo: Path):
    readme = (plugins_repo / "README.md").read_text(encoding="utf-8")
    assert "Available plugins" in readme
