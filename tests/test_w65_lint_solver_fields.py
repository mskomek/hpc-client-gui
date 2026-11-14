"""W65 LINT-013: solver family/model must have its initial fields under 0/."""
from __future__ import annotations

from hpc_gui.plugin_engines.openfoam_lint.api import lint_files, rule_catalog


def _lint(
    application: str,
    fields: dict[str, str],
    turbulence: str | None = None,
    thermo: str | None = None,
    reactions: str | None = None,
):
    files = {"system/controlDict": f"application {application};\n"}
    for name, text in fields.items():
        files[f"0/{name}"] = text
    if turbulence is not None:
        files["constant/turbulenceProperties"] = turbulence
    if thermo is not None:
        files["constant/thermophysicalProperties"] = thermo
    if reactions is not None:
        files["constant/reactions"] = reactions
    return [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-SOLVER-010"]


def test_laminar_solver_with_both_fields_is_clean():
    fields = {"U": "dimensions [0 1 -1 0 0 0 0];", "p": "dimensions [0 2 -2 0 0 0 0];"}

    assert _lint("icoFoam", fields) == []


def test_laminar_solver_reports_the_missing_field():
    reported = _lint("icoFoam", {"p": "dimensions [0 2 -2 0 0 0 0];"})

    assert len(reported) == 1
    assert "'U'" in reported[0].message
    assert reported[0].path == "0/"


def test_turbulent_model_requires_k_and_omega():
    turbulent = "simulationType RAS;\nRAS { RASModel kOmegaSST; }\n"

    reported = _lint("simpleFoam", {"U": "u", "p": "p"}, turbulent)

    reported_fields = {field for field in ("k", "omega")
                       if any(f"'{field}'" in d.message for d in reported)}
    assert reported_fields == {"k", "omega"}


def test_complete_turbulent_case_is_clean():
    turbulent = "simulationType RAS;\nRAS { RASModel kOmegaSST; }\n"
    fields = {"U": "u", "p": "p", "k": "k", "omega": "w"}

    assert _lint("simpleFoam", fields, turbulent) == []


def test_unknown_solver_is_not_judged():
    assert _lint("myCustomFoam", {"p": "p"}) == []


def test_case_without_initial_fields_is_not_judged():
    files = {"system/controlDict": "application icoFoam;\n"}

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-SOLVER-010"] == []


def test_dynamic_turbulence_model_still_checks_base_fields():
    reported = _lint("simpleFoam", {"U": "u"}, "simulationType $sim;\n")

    assert [d.message for d in reported if "'p'" in d.message]


def test_unrecognised_turbulence_model_still_checks_base_fields():
    turbulent = "simulationType RAS;\nRAS { RASModel SpalartAllmaras; }\n"

    reported = _lint("simpleFoam", {"p": "p"}, turbulent)

    assert any("'U'" in d.message for d in reported)


def test_interfoam_uses_p_rgh():
    fields = {"U": "u", "p_rgh": "p", "alpha.water": "a"}

    assert _lint("interFoam", fields) == []
    assert any("'p_rgh'" in d.message for d in _lint("interFoam", {"U": "u", "p": "p"}))


def test_buoyant_solver_uses_p_rgh_and_temperature():
    fields = {"U": "u", "p_rgh": "p", "T": "t"}

    assert _lint("buoyantSimpleFoam", fields) == []
    assert any("'T'" in d.message for d in _lint("buoyantSimpleFoam", {"U": "u", "p_rgh": "p"}))


def test_reacting_solver_requires_temperature():
    reported = _lint("reactingFoam", {"U": "u", "p": "p"})

    assert any("'T'" in d.message for d in reported)


def test_reacting_solver_requires_a_species_field():
    reported = _lint("reactingFoam", {"U": "u", "p": "p", "T": "t"})

    assert any("species" in d.message for d in reported)


def test_reacting_solver_with_species_field_is_clean():
    fields = {"U": "u", "p": "p", "T": "t", "Ydefault": "y"}

    assert _lint("reactingFoam", fields) == []


def test_reacting_tutorial_formula_species_are_clean():
    fields = {
        "U": "u", "p": "p", "T": "t",
        "CH4": "0.2", "O2": "0.2", "H2O": "0", "CO2": "0", "N2": "0.6",
    }

    assert _lint("reactingFoam", fields) == []


def test_reacting_species_only_in_zero_orig_are_clean():
    files = {
        "system/controlDict": "application reactingFoam;\n",
        "0.orig/U": "u", "0.orig/p": "p", "0.orig/T": "t", "0.orig/CH4": "0.2",
    }
    reported = [d for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-SOLVER-010"]

    assert reported == []


def test_reacting_missing_temperature_and_species_are_separate_findings():
    reported = _lint("reactingFoam", {"U": "u", "p": "p"})

    assert any("'T'" in d.message for d in reported)
    assert any("species" in d.message for d in reported)


def test_declared_species_must_have_initial_fields():
    thermo = "species ( CH4 O2 N2 );\n"
    fields = {"U": "u", "p": "p", "T": "t", "CH4": "0.2"}

    rejected = [d.message for d in _lint("reactingFoam", fields, thermo=thermo)
                if "species" in d.message]

    assert any("'O2'" in message for message in rejected)
    assert any("'N2'" in message for message in rejected)
    assert not any("'CH4'" in message for message in rejected)


def test_all_declared_species_present_is_clean():
    thermo = "species ( CH4 O2 N2 );\n"
    fields = {"U": "u", "p": "p", "T": "t", "CH4": "0.2", "O2": "0.2", "N2": "0.6"}

    assert _lint("reactingFoam", fields, thermo=thermo) == []


def test_multiline_and_quoted_declaration_is_parsed():
    thermo = "species\n(\n    CH4\n    \"O2\"\n    N2, CO2\n);\n"
    fields = {"U": "u", "p": "p", "T": "t", "CH4": "0.2"}

    rejected = [d.message for d in _lint("reactingFoam", fields, thermo=thermo)
                if "species" in d.message]

    assert any("'O2'" in message for message in rejected)
    assert any("'CO2'" in message for message in rejected)
    assert not any("'CH4'" in message for message in rejected)


def test_declared_species_present_only_in_zero_orig_is_clean():
    files = {
        "system/controlDict": "application reactingFoam;\n",
        "constant/thermophysicalProperties": "species ( CH4 O2 );\n",
        "0.orig/U": "u", "0.orig/p": "p", "0.orig/T": "t",
        "0.orig/CH4": "0.2", "0.orig/O2": "0.2",
    }
    reported = [d for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-SOLVER-010"]

    assert reported == []


def test_species_declared_in_reactions_must_have_fields():
    reactions = "species ( CH4 O2 );\n"
    fields = {"U": "u", "p": "p", "T": "t", "CH4": "0.2"}

    messages = [d.message for d in _lint("reactingFoam", fields, reactions=reactions)
                if "species" in d.message]

    assert any("'O2'" in message for message in messages)
    assert not any("only the base transport fields" in message for message in messages)


def test_declared_species_supersedes_the_generic_summary():
    reactions = "species ( CH4 O2 );\n"
    fields = {"U": "u", "p": "p", "T": "t"}

    messages = [d.message for d in _lint("reactingFoam", fields, reactions=reactions)
                if "species" in d.message]

    assert any("'CH4'" in message for message in messages)
    assert any("'O2'" in message for message in messages)
    assert not any("only the base transport fields" in message for message in messages)


def test_both_sources_union_their_species():
    thermo = "species ( CH4 N2 );\n"
    reactions = "species ( CH4 O2 );\n"
    files = {
        "system/controlDict": "application reactingFoam;\n",
        "constant/thermophysicalProperties": thermo,
        "constant/reactions": reactions,
        "0/U": "u",
        "0/p": "p",
        "0/T": "t",
        "0/CH4": "0.2",
    }
    messages = [d.message for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-SOLVER-010" and "species" in d.message]

    # Each source contributes a name that is missing from 0/, so the union --
    # not the loop order -- is what the assertions prove.
    assert any("'O2'" in message for message in messages)
    assert any("'N2'" in message for message in messages)
    assert not any("'CH4'" in message for message in messages)


def test_species_in_thermo_include_are_used():
    files = {
        "system/controlDict": "application reactingFoam;\n",
        "constant/thermophysicalProperties": '#include "thermo.compressibleGas"\n',
        "constant/thermo.compressibleGas": "species ( CH4 O2 );\n",
        "0/U": "u",
        "0/p": "p",
        "0/T": "t",
        "0/CH4": "0.2",
    }
    messages = [d.message for d in lint_files(files, case_context=True).diagnostics
                if d.rule_id == "OF-SOLVER-010" and "species" in d.message]

    assert any("'O2'" in message for message in messages)
    assert not any("'CH4'" in message for message in messages)


def test_quoted_simulation_type_is_understood():
    turbulent = 'simulationType "RAS";\nRAS { RASModel kOmegaSST; }\n'

    reported = _lint("simpleFoam", {"U": "u", "p": "p"}, turbulent)

    assert {field for d in reported for field in ("k", "omega") if f"'{field}'" in d.message} == {
        "k", "omega",
    }


def test_zero_orig_counts_as_initial_fields():
    files = {
        "system/controlDict": "application icoFoam;\n",
        "0.orig/U": "u",
        "0.orig/p": "p",
    }

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-SOLVER-010"] == []


def test_region_scoped_fields_are_not_judged_as_root_fields():
    files = {
        "system/controlDict": "application icoFoam;\n",
        "0/fluid/U": "u",
    }

    assert [d for d in lint_files(files, case_context=True).diagnostics
            if d.rule_id == "OF-SOLVER-010"] == []


def test_solvers_missing_from_the_family_table_are_still_judged():
    assert any("'T'" in d.message
               for d in _lint("buoyantPimpleFoam", {"U": "u", "p_rgh": "p"}))
    assert any("'T'" in d.message
               for d in _lint("sonicFoam", {"U": "u", "p": "p"}))
    assert any("'p'" in d.message for d in _lint("potentialFoam", {"U": "u"}))
    assert _lint("rhoCentralFoam", {"U": "u", "p": "p", "T": "t"}) == []


def test_rule_catalog_documents_the_field_rule():
    metadata = rule_catalog()["OF-SOLVER-010"]
    assert metadata["title"] == "Solver initial fields"
    assert metadata["severity"] == "warning"
    assert metadata["verification_level"] == "contextual"
