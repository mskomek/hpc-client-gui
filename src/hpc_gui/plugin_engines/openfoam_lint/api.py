"""Static OpenFOAM.com v2312 lint API exposed to the application host."""
from __future__ import annotations

from pathlib import Path
from typing import Iterable, Mapping

from hpc_gui.openfoam_core import (
    DecodedSource,
    Diagnostic,
    MAX_CASE_BYTES,
    MAX_CASE_FILES,
    MAX_DICTIONARY_BYTES,
    MAX_MESH_BOUNDARY_BYTES,
    MAX_TEXT_BYTES,
    ParsedDictionary,
    SOURCE_DOCS,
    discover_case_files,
    discover_mesh_boundaries,
    is_dictionary_name,
    is_mesh_boundary_path,
    read_dictionary_file,
    safe_relative_path,
)
from hpc_gui.openfoam_core.local_paths import require_local_path_without_links
from hpc_gui.openfoam_core.cancellation import raise_if_cancelled

from .includes import include_diagnostics
from .rules import LintResult
from .rules_case import lint_case_layout
from .rules_dictionary import RULES as DICTIONARY_RULES, lint_dictionary
from .rules_boundary import RULES as BOUNDARY_RULES, lint_boundary_requirements
from .rules_mesh import lint_mesh_patch_consistency

CASE_RULES = {
    "OF-CASE-001": {"title": "Case root", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-CASE-002": {"title": "Missing include", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-CASE-003": {"title": "Unresolved includeEtc", "severity": "info", "confidence": "certain", "verification_level": "contextual"},
    "OF-CASE-004": {"title": "Unparsed include", "severity": "info", "confidence": "heuristic", "verification_level": "contextual"},
    "OF-CASE-007": {"title": "Unsupported input file", "severity": "info", "confidence": "heuristic", "verification_level": "contextual"},
    "OF-SEC-004": {"title": "Include depth limit", "severity": "warning", "confidence": "structural", "verification_level": "contextual"},
    "OF-CTRL-001": {"title": "Control time interval", "severity": "warning", "confidence": "structural", "verification_level": "static"},
    "OF-CTRL-002": {"title": "Positive time step", "severity": "warning", "confidence": "structural", "verification_level": "static"},
    "OF-CTRL-003": {"title": "Positive write interval", "severity": "warning", "confidence": "structural", "verification_level": "static"},
    "OF-SOLVER-001": {"title": "Solver context", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-SOLVER-002": {"title": "Solver dictionaries", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-BC-001": {"title": "Boundary fields", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-BC-002": {"title": "Boundary condition type", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-PAR-001": {"title": "Parallel decomposition", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-PAR-002": {"title": "Cartesian decomposition dimensions", "severity": "warning", "confidence": "structural", "verification_level": "static"},
    "OF-MESH-001": {"title": "Mesh patch coverage", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-MESH-002": {"title": "Mesh patch metadata unverified", "severity": "info", "confidence": "contextual", "verification_level": "contextual"},
    "OF-CROSS-001": {"title": "Multi-region context", "severity": "info", "confidence": "contextual", "verification_level": "contextual"},
    "OF-CROSS-002": {"title": "Region declaration", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-CROSS-003": {"title": "Region initial fields", "severity": "warning", "confidence": "contextual", "verification_level": "contextual"},
    "OF-CROSS-004": {"title": "Shared initial fields", "severity": "info", "confidence": "contextual", "verification_level": "contextual"},
}
SUPPORTED_SUFFIXES = frozenset({".foam", ".dict"})
SUPPORTED_FILENAMES = frozenset({
    "controlDict", "fvSchemes", "fvSolution", "decomposeParDict", "blockMeshDict",
    "snappyHexMeshDict", "regionProperties", "transportProperties", "thermophysicalProperties",
    "turbulenceProperties", "fvOptions", "changeDictionaryDict", "topoSetDict",
    "surfaceFeatureExtractDict",
})


def _check_file_name(file_name: str) -> str:
    if not isinstance(file_name, str):
        raise TypeError("lint file_name must be str")
    if not file_name:
        return "<memory>"
    if len(file_name) > 4096 or "\x00" in file_name:
        raise ValueError("lint file_name is unsafe")
    if any(ord(char) < 0x20 or ord(char) == 0x7F for char in file_name):
        raise ValueError("lint file_name carries control characters")
    normalized = file_name.replace("\\", "/")
    if normalized.startswith("/") or ".." in normalized.split("/"):
        raise ValueError("lint file_name must not be absolute or traversive")
    if len(normalized) > 1 and normalized[1] == ":":
        raise ValueError("lint file_name must not carry a drive prefix")
    return file_name


def _check_text(text: str) -> str:
    if not isinstance(text, str):
        raise TypeError("lint input must be str; decode bytes explicitly before linting")
    try:
        size = len(text.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ValueError("lint input is not valid UTF-8 text") from exc
    if size > MAX_TEXT_BYTES:
        raise ValueError(f"lint input exceeds {MAX_TEXT_BYTES} bytes")
    return text


def _decode(data: bytes, path: str) -> tuple[str | None, Diagnostic | None]:
    try:
        return DecodedSource.from_bytes(data).text, None
    except UnicodeError as exc:
        return None, Diagnostic(
            "OF-DICT-005", "warning", "structural", path, 1, 1,
            f"Dictionary bytes are not valid UTF text ({type(exc).__name__}); the source was not modified.",
            "Open as raw source and confirm its encoding before linting.",
        )


def _lint_text_result(text: str, path: str) -> tuple[ParsedDictionary, tuple[Diagnostic, ...]]:
    return lint_dictionary(text, path=path)


def lint_text(text: str, *, file_name: str = "<memory>", options=None) -> LintResult:
    """Lint one in-memory dictionary without expanding includes or running directives."""
    label = _check_file_name(file_name)
    body = _check_text(text)
    _parsed, findings = _lint_text_result(body, label)
    return LintResult(findings, (label,))


def _oversize_diagnostic(relative: str) -> Diagnostic:
    return Diagnostic(
        "OF-CASE-005", "warning", "heuristic", relative, 1, 1,
        "Dictionary exceeds the per-file static lint size limit.",
        "Review the file manually or select a smaller relevant dictionary.",
    )


def lint_files(
    files: Mapping[str, bytes | str],
    *,
    root: str | Path | None = None,
    case_context: bool | None = None,
) -> LintResult:
    """Lint a bounded set of case-relative source contents, useful for SFTP adapters."""
    if not isinstance(files, Mapping):
        raise TypeError("lint_files input must be a mapping of relative path to bytes or str")
    parsed: dict[str, ParsedDictionary] = {}
    findings: list[Diagnostic] = []
    mesh_sources: dict[str, str] = {}
    checked: set[str] = set()
    total_bytes = 0
    for name, value in files.items():
        if not isinstance(name, str):
            findings.append(Diagnostic(
                "OF-CASE-006", "warning", "certain", "<memory>", 1, 1,
                "Selected path name is not text and was skipped.",
                "Check the selected path and permissions.",
                verification_level="contextual",
            ))
            continue
        relative = name.replace("\\", "/")
        if not safe_relative_path(relative):
            findings.append(Diagnostic(
                "OF-SEC-002", "warning", "structural", name, 1, 1,
                "Selected path escapes the case directory and was skipped.",
                "Keep lint inputs within the case tree.",
                verification_level="contextual",
            ))
            continue
        if len(parsed) + len(mesh_sources) + 1 > MAX_CASE_FILES:
            findings.append(Diagnostic(
                "OF-CASE-005", "warning", "heuristic", relative, 1, 1,
                "Case file-count limit reached; remaining inputs were skipped.",
                "Lint a smaller selection of dictionaries.",
            ))
            break
        if isinstance(value, bytes):
            if len(value) > MAX_DICTIONARY_BYTES and not is_mesh_boundary_path(relative):
                findings.append(_oversize_diagnostic(relative))
                continue
            if is_mesh_boundary_path(relative) and len(value) > MAX_MESH_BOUNDARY_BYTES:
                findings.append(Diagnostic(
                    "OF-MESH-002", "info", "contextual", relative, 1, 1,
                    "Mesh boundary metadata exceeds the bounded contextual scan limit; field/mesh patch coverage was not checked.",
                    "Select a bounded ASCII boundary file or inspect it with the matching OpenFOAM edition.",
                    SOURCE_DOCS, verification_level="contextual",
                ))
                continue
            text, issue = _decode(value, relative)
            if issue:
                findings.append(issue)
                continue
        elif isinstance(value, str):
            try:
                size = len(value.encode("utf-8"))
            except UnicodeEncodeError:
                findings.append(Diagnostic(
                    "OF-DICT-005", "warning", "structural", relative, 1, 1,
                    "Dictionary text is not valid UTF text; the source was not modified.",
                    "Open as raw source and confirm its encoding before linting.",
                ))
                continue
            if is_mesh_boundary_path(relative):
                if size > MAX_MESH_BOUNDARY_BYTES:
                    findings.append(Diagnostic(
                        "OF-MESH-002", "info", "contextual", relative, 1, 1,
                        "Mesh boundary metadata exceeds the bounded contextual scan limit; field/mesh patch coverage was not checked.",
                        "Select a bounded ASCII boundary file or inspect it with the matching OpenFOAM edition.",
                        SOURCE_DOCS, verification_level="contextual",
                    ))
                    continue
            elif size > MAX_DICTIONARY_BYTES:
                findings.append(_oversize_diagnostic(relative))
                continue
            text = value
        else:
            findings.append(Diagnostic(
                "OF-DICT-005", "warning", "structural", relative, 1, 1,
                "Dictionary input is not bytes or text and was skipped.",
                "Decode inputs to UTF-8 text before linting.",
            ))
            continue
        if total_bytes + len(text.encode("utf-8")) > MAX_CASE_BYTES:
            findings.append(Diagnostic(
                "OF-CASE-005", "warning", "heuristic", relative, 1, 1,
                "Case byte limit reached; remaining inputs were skipped.",
                "Lint a smaller selection of dictionaries.",
            ))
            break
        total_bytes += len(text.encode("utf-8"))
        if is_mesh_boundary_path(relative):
            mesh_sources[relative] = text
            checked.add(relative)
            continue
        if not is_dictionary_name(relative):
            findings.append(Diagnostic(
                "OF-CASE-007", "info", "heuristic", relative, 1, 1,
                "Input is not a supported dictionary and was not parsed.",
                "Select a supported OpenFOAM dictionary; static lint does not run other files.",
                verification_level="contextual",
            ))
            continue
        document, file_findings = _lint_text_result(text, relative)
        parsed[relative] = document
        checked.add(relative)
        findings.extend(file_findings)
    if root is not None:
        findings.extend(include_diagnostics(Path(root), parsed))
    if case_context is None:
        case_context = root is not None or "system/controlDict" in parsed
    if case_context:
        findings.extend(lint_case_layout(parsed))
        findings.extend(lint_boundary_requirements(parsed))
        findings.extend(lint_mesh_patch_consistency(parsed, mesh_sources))
    return LintResult(tuple(findings), tuple(sorted(checked)))


def lint_paths(paths: Iterable[str | Path], options=None, *, cancel_event=None) -> LintResult:
    """Lint selected dictionaries or case folders; bounded and read-only."""
    selected = tuple(Path(item).expanduser() for item in paths)
    findings: list[Diagnostic] = []
    files_checked: list[str] = []
    for item in selected:
        raise_if_cancelled(cancel_event)
        try:
            # Check the user's original path before Path.is_dir()/resolve()
            # can follow a selected symlink or junction into an innocent
            # looking target directory.
            item = require_local_path_without_links(item)
            if item.is_dir():
                root = item.resolve(strict=True)
                discovered = discover_case_files(root, cancel_event=cancel_event)
                if not discovered:
                    findings.append(Diagnostic(
                        "OF-CASE-001", "warning", "contextual", str(root), 1, 1,
                        "No supported dictionaries were found under system/, constant/, or 0/.",
                        "Select a case root or an individual OpenFOAM dictionary.",
                        verification_level="contextual",
                    ))
                    continue
                content = {file.relative_path: file.data for file in discovered}
                content.update(discover_mesh_boundaries(
                    root,
                    maximum_case_bytes=max(0, MAX_CASE_BYTES - sum(len(data) for data in content.values())),
                    maximum_files=max(0, MAX_CASE_FILES - len(content)),
                    cancel_event=cancel_event,
                ))
                result = lint_files(content, root=root, case_context=True)
                findings.extend(result.diagnostics)
                files_checked.extend(str(root / file) for file in result.files_checked)
            elif item.is_file():
                raise_if_cancelled(cancel_event)
                file = read_dictionary_file(item)
                raise_if_cancelled(cancel_event)
                text, issue = _decode(file.data, str(file.absolute_path))
                if issue:
                    findings.append(issue)
                elif text is not None:
                    _parsed, file_findings = _lint_text_result(text, str(file.absolute_path))
                    findings.extend(file_findings)
                    files_checked.append(str(file.absolute_path))
            else:
                findings.append(Diagnostic(
                    "OF-CASE-006", "warning", "certain", str(item), 1, 1,
                    "Selected path does not exist.", "Check the selected path and permissions.",
                    verification_level="contextual",
                ))
        except (OSError, ValueError) as exc:
            findings.append(Diagnostic(
                "OF-CASE-006", "warning", "certain", str(item), 1, 1,
                f"Selected path could not be read: {exc}", "Check file permissions and symlink targets.",
                verification_level="contextual",
            ))
    return LintResult(tuple(findings), tuple(files_checked))


def rule_catalog() -> dict[str, dict[str, str]]:
    merged = {key: dict(value) for key, value in DICTIONARY_RULES.items()}
    merged.update({key: dict(value) for key, value in CASE_RULES.items()})
    merged.update({key: dict(value) for key, value in BOUNDARY_RULES.items()})
    merged["OF-DICT-005"] = {"title": "Text encoding", "severity": "warning", "confidence": "structural", "verification_level": "static"}
    merged["OF-CASE-005"] = {"title": "File size bound", "severity": "warning", "confidence": "heuristic", "verification_level": "static"}
    merged["OF-CASE-006"] = {"title": "Selected path", "severity": "warning", "confidence": "certain", "verification_level": "contextual"}
    merged["OF-SEC-003"] = {"title": "Include cycle", "severity": "warning", "confidence": "structural", "verification_level": "contextual"}
    for metadata in merged.values():
        metadata.setdefault("source", SOURCE_DOCS)
        metadata.setdefault("verification_level", "static")
    return merged


def supports_filename(name: str) -> bool:
    leaf = str(name).replace("\\", "/").rsplit("/", 1)[-1]
    return leaf in SUPPORTED_FILENAMES or Path(leaf).suffix.casefold() in SUPPORTED_SUFFIXES
