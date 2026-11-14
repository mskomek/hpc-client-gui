"""Pure text renderers for generated fvSchemes/fvSolution dictionaries."""
from __future__ import annotations

from hpc_gui.openfoam_core import time_treatment_for


def ddt_scheme(tool: str) -> str:
    """Steady/transient time scheme from the canonical solver classification."""
    treatment = time_treatment_for(tool)
    if treatment is None:
        raise ValueError(f"solver '{tool}' has no canonical time treatment")
    return "Euler" if treatment == "transient" else "steadyState"


def fv_schemes_text(tool: str, family: str) -> str:
    ddt = ddt_scheme(tool)
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
            f"    object fvSchemes; // {tool}\n}}\n"
            f"ddtSchemes {{ default {ddt}; }}\n"
            "gradSchemes { default Gauss linear; }\n"
            "divSchemes { default Gauss linear; }\n"
            "laplacianSchemes { default Gauss linear corrected; }\n"
            "interpolationSchemes { default linear; }\n"
            "snGradSchemes { default corrected; }\n")


def fv_solution_text(tool: str, family: str) -> str:
    if family == "transient":
        algo = "PIMPLE\n{\n    nCorrectors 2;\n    nNonOrthogonalCorrectors 0;\n}\n"
    else:
        algo = "SIMPLE\n{\n    nNonOrthogonalCorrectors 0;\n}\n"
    return ("FoamFile\n{\n    version 2.0;\n    format ascii;\n    class dictionary;\n"
            f"    object fvSolution; // {tool}\n}}\n"
            "solvers\n{\n    p { solver GAMG; tolerance 1e-06; relTol 0.1; }\n"
            "    U { solver smoothSolver; tolerance 1e-05; relTol 0.1; }\n}\n"
            + algo + "relaxationFactors { equations { U 0.7; } }\n")
