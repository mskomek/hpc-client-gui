"""Typed per-file patch plans for workflow DAGs (W65 FLOW-011, G31).

A :class:`PatchPlan` is the compiled form of a :class:`WorkflowDAG`: an
ordered list of typed per-node, per-file mutations with exact file bytes.
``preview`` renders reviewable unified diffs without touching disk;
``apply`` folds a plan onto an in-memory ``{relpath: bytes}`` case map
through :mod:`hpc_gui.openfoam_core.safe_patch`, so unknown bytes outside
the patched spans are preserved verbatim. Nothing here executes a solver.
"""

from __future__ import annotations

import difflib
import json
from dataclasses import dataclass, field

from hpc_gui.openfoam_core.safe_patch import sha256_bytes, single_token_patch

#: Tools whose compiled argv rewrites or deletes existing mesh/result state.
DESTRUCTIVE_TOOLS = frozenset({"decomposePar", "snappyHexMesh", "reconstructPar",
                               "splitMeshRegions", "foamToVTK"})


@dataclass(frozen=True)
class PatchOp:
    """One typed file mutation produced by a single DAG node."""

    node_id: str
    tool: str
    relpath: str
    action: str  # create | replace | append-token | verify
    new_bytes: bytes
    old_token: bytes = b""
    new_token: bytes = b""
    argv: tuple[str, ...] = ()
    detail: str = ""
    destructive: bool = False
    provenance: str = "workflow-compiler:w65r2"
    expected_sha256: str | None = None

    def requires_confirm(self) -> bool:
        return self.destructive


@dataclass
class PatchPlan:
    node_order: list[str] = field(default_factory=list)
    ops: list[PatchOp] = field(default_factory=list)

    def files(self) -> list[str]:
        seen: list[str] = []
        for op in self.ops:
            if op.relpath not in seen:
                seen.append(op.relpath)
        return seen

    def ops_for_node(self, node_id: str) -> list[PatchOp]:
        return [op for op in self.ops if op.node_id == node_id]

    def destructive_ops(self) -> list[PatchOp]:
        return [op for op in self.ops if op.destructive]

    def sha(self) -> str:
        payload = {
            "node_order": self.node_order,
            "ops": [{
                "node_id": op.node_id,
                "tool": op.tool,
                "relpath": op.relpath,
                "action": op.action,
                "new_bytes": op.new_bytes.hex(),
                "old_token": op.old_token.hex(),
                "new_token": op.new_token.hex(),
                "argv": list(op.argv),
                "detail": op.detail,
                "destructive": op.destructive,
                "provenance": op.provenance,
                "expected_sha256": op.expected_sha256,
            } for op in self.ops],
        }
        canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                               separators=(",", ":")).encode("utf-8")
        return sha256_bytes(canonical)


def preview(plan: PatchPlan, originals: dict[str, bytes] | None = None) -> str:
    """Render a reviewable per-file diff. Pure; never writes."""
    originals = originals or {}
    chunks: list[str] = []
    for path in plan.files():
        old = (originals.get(path, b"")).decode("utf-8", "replace").splitlines()
        new_parts = [op for op in plan.ops if op.relpath == path]
        if all(op.action == "verify" for op in new_parts):
            note = new_parts[0].detail or new_parts[0].tool
            chunks.append(f"--- verify-only, no file mutation: {path} [{note}]")
            continue
        merged = (originals.get(path, b"")).decode("utf-8", "replace")
        for op in new_parts:
            if op.action == "create" and path not in (originals or {}):
                merged = op.new_bytes.decode("utf-8", "replace")
            elif op.action == "replace":
                merged = op.new_bytes.decode("utf-8", "replace")
            elif op.action == "append-token" and op.old_token and op.new_token:
                anchor = op.old_token.decode("utf-8", "replace")
                if anchor in merged:
                    merged = merged.replace(
                        anchor, op.new_token.decode("utf-8", "replace"), 1)
        new = merged.splitlines()
        diff = difflib.unified_diff(old, new, fromfile=f"a/{path}",
                                    tofile=f"b/{path}", lineterm="")
        chunks.append("\n".join(diff) or f"--- no change: {path}")
    return "\n".join(chunks)


def apply(plan: PatchPlan, case_files: dict[str, bytes],
          *, allow_destructive: bool = False) -> dict[str, bytes]:
    """Fold a plan onto an in-memory case map. No disk, no subprocess.

    Raises ``ValueError`` when a destructive op is present without
    ``allow_destructive=True``, when a token patch is ambiguous, or when a
    ``replace`` targets bytes that changed since preview (stale input).
    """
    if plan.destructive_ops() and not allow_destructive:
        names = sorted({op.tool for op in plan.destructive_ops()})
        raise ValueError(
            "destructive-overwrite guard: plan mutates existing mesh/results via "
            f"{', '.join(names)}; re-preview with explicit allow_destructive=True")
    result = dict(case_files)
    for op in plan.ops:
        if op.action == "create":
            if op.relpath in result:
                raise ValueError(
                    f"stale input: '{op.relpath}' already exists; "
                    f"node '{op.node_id}' must replace, not create")
            result[op.relpath] = op.new_bytes
        elif op.action == "replace":
            current = result.get(op.relpath)
            if current is None or op.expected_sha256 is None:
                raise ValueError(
                    f"stale input: '{op.relpath}' replace requires existing bytes and expected_sha256")
            if sha256_bytes(current) != op.expected_sha256:
                raise ValueError(f"stale input: '{op.relpath}' changed since preview")
            result[op.relpath] = op.new_bytes
        elif op.action == "append-token":
            current = result.get(op.relpath)
            if current is None:
                raise ValueError(
                    f"stale input: '{op.relpath}' missing for node '{op.node_id}'")
            result[op.relpath] = single_token_patch(current, op.old_token,
                                                    op.new_token)
        elif op.action == "verify":
            pass  # argv/draft preview only; no case-file mutation
        else:
            raise ValueError(f"unknown patch action '{op.action}'")
    return result
