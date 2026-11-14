"""W65 LINT-013: CHT regionProperties must declare fluid and solid groups."""
from __future__ import annotations

from hpc_gui.plugin_engines.openfoam_lint.api import lint_files, rule_catalog


def _lint(application: str, regions: str):
    files = {
        "system/controlDict": f"application {application};\n",
        "constant/regionProperties": regions,
    }
    return [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-CROSS-005"]


def test_cht_solver_requires_a_solid_group():
    reported = _lint("chtMultiRegionFoam", "regions (fluid (water air));\n")

    assert len(reported) == 1
    assert "solid" in reported[0].message
    assert reported[0].path == "constant/regionProperties"


def test_cht_solver_requires_a_fluid_group():
    reported = _lint("chtMultiRegionSimpleFoam", "regions (solid (steel));\n")

    assert "fluid" in reported[0].message


def test_complete_cht_groups_are_accepted():
    regions = "regions (fluid (water air) solid (steel));\n"

    assert _lint("chtMultiRegionFoam", regions) == []


def test_non_cht_solver_is_not_judged():
    assert _lint("simpleFoam", "regions (fluid (water));\n") == []


def test_dynamic_regions_do_not_crash_the_group_check():
    reported = _lint("chtMultiRegionFoam", "regions $regions;\n")

    assert reported == []


def test_missing_region_properties_is_reported_for_cht():
    files = {"system/controlDict": "application chtMultiRegionFoam;\n"}

    reported = [d for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-CROSS-005"]

    assert len(reported) == 1
    assert "no constant/regionProperties" in reported[0].message


def test_no_region_properties_is_fine_for_non_cht():
    files = {"system/controlDict": "application simpleFoam;\n"}

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-CROSS-005"] == []


def test_both_groups_missing_is_reported_once():
    reported = _lint("chtMultiRegionFoam", "regions (porous (sponge));\n")

    assert len(reported) == 1
    assert "fluid or solid" in reported[0].message


def test_extra_group_type_is_accepted():
    regions = "regions (fluid (water) solid (steel) porous (sponge));\n"

    assert _lint("chtMultiRegionFoam", regions) == []


def test_dynamic_application_is_not_judged():
    files = {
        "system/controlDict": "application $app;\n",
        "constant/regionProperties": "regions (fluid (water));\n",
    }

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-CROSS-005"] == []


def test_rule_catalog_documents_the_group_rule():
    metadata = rule_catalog()["OF-CROSS-005"]
    assert metadata["title"] == "CHT region groups"
    assert metadata["severity"] == "warning"
    assert metadata["verification_level"] == "contextual"
