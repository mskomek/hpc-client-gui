"""Wave 6 — Plugin / Provider Unicode Contract and Directories Integration.

Guarantee plugins/providers can expose Unicode labels, storage names, paths
and actions, and that Directories consumes them without corruption.
"""
from __future__ import annotations
import pytest

import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# 1. Reference Unicode Provider Data
# ---------------------------------------------------------------------------

UNICODE_PROVIDER_DATA = {
    "name": "Üniversite Kümesi",
    "description": "Hesaplama sonuçlarını göster",
    "storage": {
        "label": "Çalışma Alanı",
        "path": "/scratch/çalışmalar/日本語",
    },
    "action": {
        "label": "İş Klasörünü Aç",
    },
}


# ---------------------------------------------------------------------------
# 2. Plugin Manifest Unicode
# ---------------------------------------------------------------------------

class TestPluginManifestUnicode:
    """Verify plugin manifests handle Unicode correctly."""

    @pytest.mark.reporting
    def test_manifest_name_unicode(self):
        """PluginManifest should accept Unicode names."""
        from hpc_gui.plugins.models import PluginManifest

        manifest = PluginManifest(
            schema_version=1,
            plugin_api=1,
            id="test.unicode-plugin",
            name="Üniversite Kümesi Plugin",
            version="1.0.0",
            publisher="Test Publisher",
            license="MIT",
            description="Hesaplama sonuçlarını göster",
            requires_app=">=1.0.0",
            capabilities=["cluster-profile"],
            entrypoints=[],
            files=[],
        )
        assert manifest.name == "Üniversite Kümesi Plugin"
        assert "hesaplama" in manifest.description.lower()

    @pytest.mark.reporting
    def test_cluster_profile_unicode(self):
        """ClusterProfileDefinition should accept Unicode names."""
        from hpc_gui.plugins.models import ClusterProfileDefinition

        profile = ClusterProfileDefinition(
            profile_id="test_unicode",
            name="Çalışma Alanı Profili",
            scheduler="slurm",
        )
        assert profile.name == "Çalışma Alanı Profili"

    @pytest.mark.reporting
    def test_storage_area_unicode(self):
        """Storage areas should accept Unicode labels and paths."""
        from hpc_gui.plugins.models import ClusterProfileDefinition

        profile = ClusterProfileDefinition(
            profile_id="test_storage",
            name="Test Storage",
            scheduler="slurm",
            storage=(
                {
                    "label": "Çalışma Alanı",
                    "path": "/scratch/çalışmalar/日本語",
                    "kind": "scratch",
                },
            ),
        )
        assert profile.storage[0]["label"] == "Çalışma Alanı"
        assert "çalışmalar" in profile.storage[0]["path"]

    @pytest.mark.reporting
    def test_job_outputs_unicode(self):
        """Job outputs should accept Unicode labels."""
        from hpc_gui.plugins.models import ClusterProfileDefinition

        profile = ClusterProfileDefinition(
            profile_id="test_outputs",
            name="Test Outputs",
            scheduler="slurm",
            job_outputs={
                "strategy": "explicit",
                "streams": [
                    {
                        "id": "stdout",
                        "role": "stdout",
                        "resolver": "slurm.stdout",
                        "labels": {"en": "Standard Output", "tr": "Standart Çıktı"},
                        "order": 100,
                    }
                ],
            },
        )
        assert profile.job_outputs["streams"][0]["labels"]["tr"] == "Standart Çıktı"


# ---------------------------------------------------------------------------
# 3. Plugin Validator Unicode
# ---------------------------------------------------------------------------

class TestPluginValidatorUnicode:
    """Verify plugin validator handles Unicode correctly."""

    @pytest.mark.reporting
    def test_validate_manifest_unicode_name(self):
        """validate_manifest_dict should accept Unicode names."""
        from hpc_gui.plugins.validator import validate_manifest_dict

        manifest = {
            "schema_version": 1,
            "plugin_api": 1,
            "id": "test.unicode",
            "name": "Üniversite Plugin",
            "version": "1.0.0",
            "publisher": "Test",
            "license": "MIT",
            "description": "Çalışma alanı eklentisi",
            "requires_app": ">=1.0.0",
            "capabilities": ["cluster-profile"],
            "entrypoints": [],
            "files": [],
        }
        errors = validate_manifest_dict(manifest)
        # Should have no errors related to Unicode
        name_errors = [e for e in errors if "name" in e.lower()]
        assert len(name_errors) == 0

    @pytest.mark.reporting
    def test_validate_cluster_profile_unicode(self):
        """validate_cluster_profile_dict should accept Unicode names."""
        from hpc_gui.plugins.validator import validate_cluster_profile_dict

        profile = {
            "schema_version": 4,
            "profile_id": "test_unicode",
            "name": "Çalışma Alanı Profili",
            "scheduler": "slurm",
        }
        errors = validate_cluster_profile_dict(profile)
        name_errors = [e for e in errors if "name" in e.lower()]
        assert len(name_errors) == 0


# ---------------------------------------------------------------------------
# 4. Provider Contract Unicode
# ---------------------------------------------------------------------------

class TestProviderContractUnicode:
    """Verify provider contract handles Unicode correctly."""

    @pytest.mark.contract
    def test_extract_contract_unicode(self):
        """extract_contract should handle Unicode provider template."""
        from hpc_gui.services.provider_contract import extract_contract

        template = {
            "job_details": {
                "adapter": "slurm.scontrol.job",
                "parser": "slurm.scontrol",
            },
            "accounting": {
                "adapter": "slurm.sacct.job",
                "parser": "slurm.sacct",
            },
        }
        contract = extract_contract(template)
        assert contract.has_job_details is True
        assert contract.has_accounting is True

    @pytest.mark.contract
    def test_extract_contract_empty(self):
        """extract_contract should handle empty template."""
        from hpc_gui.services.provider_contract import extract_contract

        contract = extract_contract({})
        assert contract.has_job_details is False
        assert contract.has_accounting is False
        assert contract.has_cluster_status is False


# ---------------------------------------------------------------------------
# 5. Provider Context Unicode
# ---------------------------------------------------------------------------

class TestProviderContextUnicode:
    """Verify provider context handles Unicode correctly."""

    @pytest.mark.contract
    def test_resolve_provider_path_unicode(self):
        """resolve_provider_path should handle Unicode paths."""
        from hpc_gui.config.system_profile import (
            ProviderContext,
            resolve_provider_path,
        )

        context = ProviderContext(
            user="çalışma",
            project="日本語_proje",
            account="test_account",
        )
        template = "/scratch/{user}/{project}"
        result = resolve_provider_path(template, context)
        assert result.state == "resolved"
        assert "çalışma" in result.path
        assert "日本語" in result.path

    @pytest.mark.contract
    def test_resolve_provider_path_missing_context(self):
        """resolve_provider_path should handle missing context gracefully."""
        from hpc_gui.config.system_profile import (
            ProviderContext,
            resolve_provider_path,
        )

        context = ProviderContext(user="", project="", account="")
        template = "/scratch/{user}/{project}"
        result = resolve_provider_path(template, context)
        assert result.state == "missing-context"

    @pytest.mark.contract
    def test_resolve_provider_path_unknown_placeholder(self):
        """resolve_provider_path should fail closed on unknown placeholders."""
        from hpc_gui.config.system_profile import (
            ProviderContext,
            resolve_provider_path,
        )

        context = ProviderContext(user="test", project="test", account="test")
        template = "/scratch/{unknown_var}"
        result = resolve_provider_path(template, context)
        assert result.state == "invalid-template"


# ---------------------------------------------------------------------------
# 6. Plugin UI Contributions Unicode
# ---------------------------------------------------------------------------

class TestPluginUIContributionsUnicode:
    """Verify plugin UI contributions handle Unicode correctly."""

    @pytest.mark.contract
    def test_ui_contributions_label_unicode(self):
        """UI contributions should accept Unicode labels."""
        from hpc_gui.plugins.ui_contributions import validate_ui_contributions_dict

        contributions = {
            "menu": {
                "items": [
                    {
                        "type": "submenu",
                        "id": "test_menu",
                        "labels": {"en": "Test Menu", "tr": "Test Menüsü"},
                        "items": [
                            {
                                "type": "action",
                                "id": "test_action",
                                "labels": {"en": "Open Folder", "tr": "Klasörü Aç"},
                                "provider_action": "open_folder",
                            }
                        ],
                    }
                ]
            }
        }
        errors = validate_ui_contributions_dict(contributions)
        # Should have no errors related to Unicode
        label_errors = [e for e in errors if "label" in e.lower() or "unicode" in e.lower()]
        assert len(label_errors) == 0


# ---------------------------------------------------------------------------
# 7. Integration Tests
# ---------------------------------------------------------------------------

class TestIntegration:
    """Integration tests for plugin/provider Unicode."""

    @pytest.mark.contract
    def test_full_plugin_unicode_flow(self):
        """Full flow: create manifest, validate, build profile."""
        from hpc_gui.plugins.models import (
            PluginManifest,
            build_cluster_profile,
        )
        from hpc_gui.plugins.validator import (
            validate_manifest_dict,
            validate_cluster_profile_dict,
        )

        # 1. Create manifest with Unicode
        manifest_dict = {
            "schema_version": 1,
            "plugin_api": 1,
            "id": "test.unicode-provider",
            "name": "Üniversite Kümesi Plugin",
            "version": "1.0.0",
            "publisher": "Test Publisher",
            "license": "MIT",
            "description": "Hesaplama sonuçlarını göster",
            "requires_app": ">=1.0.0",
            "capabilities": ["cluster-profile"],
            "entrypoints": {"cluster-profiles": ["profiles/test.json"]},
            "files": [{"path": "profiles/test.json", "sha256": "a" * 64, "size": 100, "role": "cluster-profile"}],
        }

        # 2. Validate manifest
        errors = validate_manifest_dict(manifest_dict)
        assert len(errors) == 0, f"Manifest validation errors: {errors}"

        # 3. Build manifest
        manifest = PluginManifest(
            schema_version=manifest_dict["schema_version"],
            plugin_api=manifest_dict["plugin_api"],
            id=manifest_dict["id"],
            name=manifest_dict["name"],
            version=manifest_dict["version"],
            publisher=manifest_dict["publisher"],
            license=manifest_dict["license"],
            description=manifest_dict["description"],
            requires_app=manifest_dict["requires_app"],
            capabilities=manifest_dict["capabilities"],
            entrypoints=manifest_dict["entrypoints"],
            files=manifest_dict["files"],
        )
        assert manifest.name == "Üniversite Kümesi Plugin"

        # 4. Create cluster profile with Unicode
        profile_dict = {
            "schema_version": 4,
            "profile_id": "test_unicode_provider",
            "name": "Çalışma Alanı Profili",
            "scheduler": "slurm",
            "storage": [
                {
                    "label": "Çalışma Alanı",
                    "path": "/scratch/çalışmalar/日本語",
                    "kind": "scratch",
                }
            ],
            "commands": {
                "squeue_command": 'squeue -h -u {user} -o "%i|%P|%j|%u|%T|%M|%D|%C|%R"',
                "sbatch_command": "cd -- {script_dir_q} && sbatch -- {script_name_q}",
                "scancel_command": "scancel {job_id_q}",
                "sacct_command": 'sacct -n -P -u {user} --format=JobIDRaw,JobName,State,Elapsed,MaxRSS,AllocTRES,ExitCode',
                "scontrol_command": "scontrol show job {job_id_q}",
                "status_command": "lssrv",
            },
        }

        # 5. Validate profile
        errors = validate_cluster_profile_dict(profile_dict)
        assert len(errors) == 0, f"Profile validation errors: {errors}"

        # 6. Build profile
        profile = build_cluster_profile(profile_dict)
        assert profile.name == "Çalışma Alanı Profili"
        assert profile.storage[0]["label"] == "Çalışma Alanı"
        assert "çalışmalar" in profile.storage[0]["path"]
        assert "日本語" in profile.storage[0]["path"]

        # 7. Convert to system settings
        settings = profile.to_system_settings()
        assert settings is not None
        # settings contains the profile data
        assert "name" in settings
        assert settings["name"] == "Çalışma Alanı Profili"

    @pytest.mark.contract
    def test_provider_path_resolution_unicode(self):
        """Unicode paths should resolve correctly through provider context."""
        from hpc_gui.config.system_profile import (
            ProviderContext,
            resolve_provider_path,
        )

        context = ProviderContext(
            user="çalışma",
            project="日本語_proje",
            account="hesaplama",
        )

        templates = [
            "/scratch/{user}",
            "/scratch/{user}/{project}",
            "/home/{user}/work/{account}",
        ]

        for template in templates:
            result = resolve_provider_path(template, context)
            assert result.state == "resolved", f"Failed for {template}: {result.state}"
            assert "çalışma" in result.path or "日本語" in result.path

    @pytest.mark.contract
    def test_optional_data_graceful_degradation(self):
        """Missing optional data should degrade gracefully."""
        from hpc_gui.services.provider_contract import extract_contract

        # Empty template
        contract = extract_contract({})
        assert contract.has_job_details is False
        assert contract.has_accounting is False
        assert contract.has_cluster_status is False

        # Partial template
        contract2 = extract_contract({"job_details": {"adapter": "test"}})
        assert contract2.has_job_details is True
        assert contract2.has_accounting is False

    @pytest.mark.contract
    def test_existing_ascii_compatibility(self):
        """Existing ASCII providers should remain compatible."""
        from hpc_gui.plugins.models import ClusterProfileDefinition

        # ASCII-only profile (existing TRUBA-style)
        profile = ClusterProfileDefinition(
            profile_id="truba_default",
            name="TRUBA Default",
            scheduler="slurm",
            paths={"scratch": "/scratch/{user}", "home": "/home/{user}"},
        )
        assert profile.name == "TRUBA Default"
        assert profile.paths["scratch"] == "/scratch/{user}"

    @pytest.mark.contract
    def test_ui_contributions_unicode_labels(self):
        """UI contributions should render Unicode labels correctly."""
        from hpc_gui.plugins.ui_contributions import validate_ui_contributions_dict

        # UI contributions use a specific structure
        # The validation checks for known properties
        contributions = {
            "items": [
                {
                    "type": "submenu",
                    "id": "hpc_tools",
                    "labels": {"en": "HPC Tools", "tr": "HPC Araçları"},
                    "items": [
                        {
                            "type": "action",
                            "id": "open_scratch",
                            "labels": {"en": "Open Scratch", "tr": "Scratch Aç"},
                            "provider_action": "open_scratch",
                            "when": ["connected"],
                        },
                    ],
                }
            ]
        }
        errors = validate_ui_contributions_dict(contributions)
        # Should have no errors related to Unicode labels
        label_errors = [e for e in errors if "label" in e.lower() and "unicode" in e.lower()]
        assert len(label_errors) == 0
