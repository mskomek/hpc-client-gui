"""Static include safety and cycle checks; directives are never expanded by the runtime."""
from __future__ import annotations

from collections import deque
from pathlib import Path, PurePosixPath

from hpc_gui.openfoam_core import Diagnostic, ParsedDictionary, SOURCE_DOCS
from hpc_gui.openfoam_core.limits import MAX_INCLUDE_DEPTH


def include_diagnostics(root: Path, parsed_files: dict[str, ParsedDictionary]) -> tuple[Diagnostic, ...]:
    findings: list[Diagnostic] = []
    graph: dict[str, list[tuple[str, int, int]]] = {name: [] for name in parsed_files}
    root = root.resolve()
    for relative, parsed in parsed_files.items():
        source_parent = PurePosixPath(relative).parent
        for index, token in enumerate(parsed.tokens):
            if token.kind != "directive" or token.value not in {"#include", "#includeEtc"}:
                continue
            target = parsed.tokens[index + 1] if index + 1 < len(parsed.tokens) else None
            if target is None or target.kind != "string":
                continue
            raw = target.value.strip('"\'')
            if token.value == "#includeEtc":
                findings.append(Diagnostic(
                    "OF-CASE-003", "info", "certain", relative, token.line, token.column,
                    "#includeEtc is not expanded by static lint.",
                    "Confirm that the intended OpenFOAM installation provides this file.", SOURCE_DOCS, verification_level="contextual",
                ))
                continue
            normalized = raw.replace("\\", "/")
            parts = PurePosixPath(normalized).parts
            if PurePosixPath(normalized).is_absolute() or ".." in parts or (len(normalized) > 1 and normalized[1] == ":"):
                continue  # OF-SEC-002 is emitted by the dictionary rule pass.
            candidate_rel = (source_parent / PurePosixPath(normalized)).as_posix()
            candidate = root.joinpath(*PurePosixPath(candidate_rel).parts)
            try:
                resolved = candidate.resolve(strict=False)
                if root not in resolved.parents:
                    raise ValueError("path escapes the case root")
                cursor = candidate
                while cursor != root:
                    if cursor.is_symlink():
                        raise ValueError("symlink include is not followed")
                    cursor = cursor.parent
            except (OSError, ValueError):
                findings.append(Diagnostic(
                    "OF-SEC-002", "warning", "structural", relative, token.line, token.column,
                    "Include path escapes the case or traverses a symbolic link.",
                    "Keep includes within the case tree and inspect symlinks before resolving them.", SOURCE_DOCS, verification_level="contextual",
                ))
                continue
            if not candidate.exists():
                findings.append(Diagnostic(
                    "OF-CASE-002", "warning", "contextual", relative, token.line, token.column,
                    f"Included file {raw!r} was not found within the case tree.",
                    "Check the relative path and spelling; static lint does not search OpenFOAM installation paths.", SOURCE_DOCS, verification_level="contextual",
                ))
                continue
            key = resolved.relative_to(root).as_posix()
            if key in parsed_files:
                graph[relative].append((key, token.line, token.column))
            else:
                findings.append(Diagnostic(
                    "OF-CASE-004", "info", "heuristic", relative, token.line, token.column,
                    f"Included file {raw!r} exists but was not parsed as a selected dictionary.",
                    "Add it to the lint selection if it contains a dictionary that should be checked.", SOURCE_DOCS, verification_level="contextual",
                ))

    state: dict[str, int] = {}
    cycle_edges: set[tuple[str, str, int, int]] = set()
    for start in graph:
        if state.get(start, 0) != 0:
            continue
        state[start] = 1
        stack: list[tuple[str, int]] = [(start, 0)]
        while stack:
            node, edge_index = stack[-1]
            outgoing = graph[node]
            if edge_index >= len(outgoing):
                state[node] = 2
                stack.pop()
                continue
            target, line, column = outgoing[edge_index]
            stack[-1] = (node, edge_index + 1)
            target_state = state.get(target, 0)
            if target_state == 1:
                edge = (node, target, line, column)
                if edge not in cycle_edges:
                    cycle_edges.add(edge)
                    findings.append(Diagnostic(
                        "OF-SEC-003", "warning", "structural", node, line, column,
                        f"Circular include detected through {target!r}.",
                        "Break the include cycle before runtime validation.", SOURCE_DOCS, verification_level="contextual",
                    ))
            elif target_state == 0:
                state[target] = 1
                stack.append((target, 0))

    acyclic: dict[str, list[tuple[str, int, int]]] = {name: [] for name in graph}
    indegree = {name: 0 for name in graph}
    for node, outgoing in graph.items():
        for edge in outgoing:
            if (node, *edge) in cycle_edges:
                continue
            acyclic[node].append(edge)
            indegree[edge[0]] += 1

    ready = deque(name for name, degree in indegree.items() if degree == 0)
    depth = dict.fromkeys(graph, 0)
    while ready:
        node = ready.popleft()
        for target, line, column in acyclic[node]:
            candidate_depth = depth[node] + 1
            if candidate_depth == MAX_INCLUDE_DEPTH + 1:
                findings.append(Diagnostic(
                    "OF-SEC-004", "warning", "structural", node, line, column,
                    f"Include chain exceeds the static analysis limit of {MAX_INCLUDE_DEPTH} levels.",
                    "Shorten or flatten the include chain; deeper relationships are not analyzed.", SOURCE_DOCS, verification_level="contextual",
                ))
            if candidate_depth > depth[target]:
                depth[target] = min(candidate_depth, MAX_INCLUDE_DEPTH + 1)
            indegree[target] -= 1
            if indegree[target] == 0:
                ready.append(target)
    return tuple(findings)
