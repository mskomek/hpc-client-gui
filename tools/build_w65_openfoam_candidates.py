"""Build deterministic, source-bound W65 OpenFOAM Plugin API 3 candidates."""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import stat
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


GENERATOR_VERSION = "1"
PUBLISHER = "HPC Client GUI"
STUDIO_ID = "org.hpcclient.openfoamcasestudio"
LINTER_ID = "org.hpcclient.openfoamlint"
STUDIO_VERSION = "0.3.1-w65r19.20261027.2"
LINTER_VERSION = "0.2.1-w65r19.20261027.2"
APP_FLOOR = ">=1.5.9"
STUDIO_ENGINE = "engine/openfoam_studio/__init__.py"
LINTER_ENGINE = "engine/openfoam_lint/__init__.py"

_TRUBA_TEMPLATE = """#!/usr/bin/env bash
#SBATCH --job-name=openfoam-v2312
#SBATCH --nodes={{nodes}}
#SBATCH --ntasks={{ntasks}}
#SBATCH --time={{time_limit}}
#SBATCH --output=slurm-%j.out
#SBATCH --error=slurm-%j.err

# Draft only. Review cluster policy and module availability before submission.
set -eo pipefail
if ! command -v module >/dev/null 2>&1 && [[ -r /etc/profile.d/modules.sh ]]; then
    source /etc/profile.d/modules.sh
fi
if ! command -v module >/dev/null 2>&1; then
    echo "Environment Modules is unavailable." >&2
    exit 127
fi
module load apps/openfoam/v2312-2025
set +e
source "$WM_PROJECT_DIR/etc/bashrc"
openfoam_env_status=$?
set -e
if (( openfoam_env_status != 0 )); then
    echo "OpenFOAM environment initialization failed: $openfoam_env_status" >&2
    exit "$openfoam_env_status"
fi
set -u
expected_allrun_sha256={{allrun_sha256}}
if [[ ! -f ./Allrun || -L ./Allrun ]]; then
    echo "Refusing missing or symlinked Allrun." >&2
    exit 2
fi
printf '%s  %s\\n' "$expected_allrun_sha256" ./Allrun | sha256sum --check --status || {
    echo "Allrun does not match the reviewed Studio workflow." >&2
    exit 3
}
exec bash -- ./Allrun
"""


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def _git_bytes(root: Path, commit: str, path: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), "show", f"{commit}:{path}"])


def _source_binding(
    root: Path,
    commit: str,
    path: str,
    output: bytes,
    transform: str,
    *,
    package_path: str,
) -> dict:
    original = _git_bytes(root, commit, path)
    blob = _git(root, "rev-parse", f"{commit}:{path}")
    return {
        "package_path": package_path,
        "source_path": path.replace("\\", "/"),
        "git_blob": blob,
        "source_sha256": _sha(original),
        "source_bytes": len(original),
        "output_sha256": _sha(output),
        "output_bytes": len(output),
        "transform": transform,
    }


def _relocate_core_imports(source: bytes, *, core_module: bool) -> tuple[bytes, str]:
    text = source.decode("utf-8", errors="strict")
    pattern = re.compile(r"(?m)^(\s*from\s+)hpc_gui\.openfoam_core(?P<tail>(?:\.[A-Za-z0-9_.]+)?)\s+import\s+")
    if core_module:
        text = pattern.sub(lambda match: match.group(1) + "." + match.group("tail").lstrip(".") + " import ", text)
    else:
        text = pattern.sub(lambda match: match.group(1) + ".openfoam_core" + match.group("tail") + " import ", text)
    changed = text.encode("utf-8")
    label = "hpc_gui.openfoam_core imports rewritten to package-relative closure" if changed != source else "identity"
    return changed, label


def _project_module_path(root: Path, module: str) -> Path | None:
    relative = Path("src") / Path(*module.split("."))
    candidates = [root / relative.with_suffix(".py"), root / relative / "__init__.py"]
    return next((candidate for candidate in candidates if candidate.is_file()), None)


def _host_imports(root: Path, tree: ast.Module) -> set[str]:
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(
                alias.name for alias in node.names
                if alias.name == "hpc_gui" or alias.name.startswith("hpc_gui.")
            )
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            module = node.module or ""
            if module == "hpc_gui" or module.startswith("hpc_gui."):
                imports.add(module)
                for alias in node.names:
                    child = f"{module}.{alias.name}"
                    if alias.name != "*" and _project_module_path(root, child) is not None:
                        imports.add(child)
    return imports


def _host_dependencies(root: Path, commit: str, engine_files: list[Path]) -> list[dict]:
    pending: list[str] = []
    for source in engine_files:
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        pending.extend(
            module for module in _host_imports(root, tree)
            if not module.startswith("hpc_gui.openfoam_core")
        )
    modules: set[str] = set()
    while pending:
        module = pending.pop()
        if module in modules:
            continue
        modules.add(module)
        source = _project_module_path(root, module)
        if source is None:
            raise RuntimeError(f"unresolved host API dependency: {module}")
        tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
        pending.extend(_host_imports(root, tree) - modules)

    dependencies = []
    for module in sorted(modules):
        source = _project_module_path(root, module)
        if source is None:
            raise RuntimeError(f"unresolved host API dependency: {module}")
        git_path = source.relative_to(root).as_posix()
        payload = _git_bytes(root, commit, git_path)
        dependencies.append({
            "module": module,
            "source_path": git_path,
            "git_blob": _git(root, "rev-parse", f"{commit}:{git_path}"),
            "source_sha256": _sha(payload),
            "source_bytes": len(payload),
            "binding": "transitive host API import-closure dependency; imported from the application",
        })
    return dependencies


def _safe_output_path(value: str) -> Path:
    path = Path(value).expanduser().resolve()
    if path.exists():
        raise FileExistsError(f"output path already exists: {path}")
    return path


def _make_package(root: Path, commit: str, out: Path, *, kind: str) -> dict:
    if kind == "studio":
        plugin_id, version, name = STUDIO_ID, STUDIO_VERSION, "OpenFOAM Visual Case Studio"
        engine_root = root / "src/hpc_gui/plugin_engines/openfoam_studio"
        output_prefix, engine_role = "engine/openfoam_studio", "application-engine"
        capabilities = ["application-tools", "job-template"]
        template_payload = _TRUBA_TEMPLATE.encode("utf-8")
        template_hash = _sha(template_payload)
        index_payload = _json_bytes({
            "schema_version": 1,
            "name": "OpenFOAM.com v2312 Slurm templates",
            "description": "Review-only draft for the OpenFOAM.com v2312 target.",
            "templates": [{
                "id": "openfoam-v2312-truba-slurm",
                "name": "OpenFOAM.com v2312 Slurm draft",
                "description": "Verifies the reviewed Studio Allrun before invoking it; never submits a job.",
                "scheduler": "slurm", "application": "openfoam-v2312",
                "file_name": "openfoam_v2312.slurm",
                "content_path": "templates/openfoam_v2312_truba.slurm.tpl",
                "sha256": template_hash,
                "variables": [
                    {"name": "nodes", "type": "integer", "required": True, "default": 1, "minimum": 1, "maximum": 128},
                    {"name": "ntasks", "type": "integer", "required": True, "default": 1, "minimum": 1, "maximum": 256},
                    {"name": "time_limit", "type": "choice", "required": True, "default": "01:00:00", "choices": ["00:05:00", "01:00:00", "04:00:00", "24:00:00"]},
                    {"name": "allrun_sha256", "type": "sha256", "required": True, "description": "Digest of the generated Allrun reviewed with this draft."},
                ],
            }],
        })
        generated_payloads = {
            "templates/index.json": (index_payload, "template-index"),
            "templates/openfoam_v2312_truba.slurm.tpl": (template_payload, "template-content"),
        }
        entrypoints = {"application_tool": STUDIO_ENGINE, "job_templates": "templates/index.json"}
        ui = {"plugins_menu": {
            "label": "OpenFOAM Case Studio",
            "labels": {"en": "OpenFOAM Case Studio", "tr": "OpenFOAM Case Studio"},
            "items": [
                {"kind": "action", "id": "open_studio", "label": "Open Case Studio", "labels": {"en": "Open Case Studio", "tr": "Case Studio'yu Aç"}, "action": "openfoam.open_studio"},
                {"kind": "action", "id": "new_case", "label": "New OpenFOAM Case", "labels": {"en": "New OpenFOAM Case", "tr": "Yeni OpenFOAM Case"}, "action": "openfoam.new_case"},
                {"kind": "action", "id": "job_draft", "label": "Create Slurm Draft", "labels": {"en": "Create Slurm Draft", "tr": "Slurm Taslağı Oluştur"}, "action": "openfoam.create_job_draft"},
            ],
        }}
    else:
        plugin_id, version, name = LINTER_ID, LINTER_VERSION, "OpenFOAM Linter"
        engine_root = root / "src/hpc_gui/plugin_engines/openfoam_lint"
        output_prefix, engine_role = "engine/openfoam_lint", "linter-engine"
        capabilities = ["linter-tool"]
        generated_payloads = {}
        entrypoints = {"linter_engine": LINTER_ENGINE}
        ui = {"plugins_menu": {
            "label": "OpenFOAM Linter",
            "labels": {"en": "OpenFOAM Linter", "tr": "OpenFOAM Linter"},
            "items": [{"kind": "action", "id": "validate", "label": "Validate OpenFOAM Case", "labels": {"en": "Validate OpenFOAM Case", "tr": "OpenFOAM Case'i Doğrula"}, "action": "openfoam.validate"}],
        }}

    package_dir = out / ("openfoam-case-studio" if kind == "studio" else "openfoam-linter")
    package_dir.mkdir(parents=True)
    binding_rows = []
    files: dict[str, tuple[bytes, str]] = {}
    engine_sources = sorted(engine_root.rglob("*.py"))
    core_root = root / "src/hpc_gui/openfoam_core"
    core_sources = sorted(core_root.rglob("*.py"))
    for source in [*engine_sources, *core_sources]:
        if source.is_symlink() or not source.resolve().is_relative_to(root.resolve()):
            raise RuntimeError(f"plugin source is a link or escapes the repository: {source}")
    for source in [*engine_sources, *core_sources]:
        is_engine_source = source.is_relative_to(engine_root)
        relative_root = engine_root if is_engine_source else core_root
        relative = source.relative_to(relative_root).as_posix()
        if is_engine_source:
            package_path = f"{output_prefix}/{relative}"
        else:
            package_path = f"{output_prefix}/openfoam_core/{relative}"
        source_path = source.relative_to(root).as_posix()
        source_bytes = _git_bytes(root, commit, source_path)
        transformed, transform = _relocate_core_imports(
            source_bytes, core_module=not is_engine_source,
        )
        files[package_path] = (transformed, engine_role)
        binding_rows.append(_source_binding(
            root, commit, source_path, transformed, transform, package_path=package_path,
        ))
    if kind == "studio":
        catalog_source = "src/hpc_gui/plugin_engines/openfoam_studio/data/command_catalog.json"
        catalog_payload = _git_bytes(root, commit, catalog_source)
        catalog_path = f"{output_prefix}/data/command_catalog.json"
        files[catalog_path] = (catalog_payload, "application-catalog")
        binding_rows.append(_source_binding(
            root, commit, catalog_source, catalog_payload, "identity",
            package_path=catalog_path,
        ))
    host_deps = _host_dependencies(root, commit, engine_sources)
    generator_path = Path(__file__).resolve().relative_to(root).as_posix()
    for path, (payload, role) in generated_payloads.items():
        files[path] = (payload, role)
        binding_rows.append(_source_binding(
            root, commit, generator_path, payload,
            f"deterministically generated by {generator_path}@{GENERATOR_VERSION}",
            package_path=path,
        ))
    readme = (
        f"# {name}\n\n"
        f"Version: `{version}`; Plugin API 3; application-pinned release.\n\n"
        "This package is bound to the source rows in `W65_SOURCE_BINDINGS.json`. Python code runs in-process with application privileges; SHA-256 pinning verifies provenance and is not an OS sandbox.\n\n"
        "OpenFOAM target: OpenFOAM.com / ESI v2312, module `apps/openfoam/v2312-2025`. Job files are drafts only; the plugin never submits them.\n"
    ).encode("utf-8")
    files["README.md"] = (readme, "documentation")
    binding_rows.append(_source_binding(
        root, commit, generator_path, readme,
        f"deterministically generated by {generator_path}@{GENERATOR_VERSION}",
        package_path="README.md",
    ))
    binding_document = {
        "schema_version": 1,
        "plugin_id": plugin_id,
        "version": version,
        "source_commit": commit,
        "generator": {"path": generator_path, "version": GENERATOR_VERSION, "git_blob": _git(root, "rev-parse", f"{commit}:{generator_path}")},
        "generated_payloads": "Deterministic UTF-8 JSON/text bytes declared in the source-controlled candidate builder.",
        "source_files": sorted(binding_rows, key=lambda row: row["source_path"]),
        "host_api_dependencies": host_deps,
        "self_binding": "This file is excluded from its own rows; manifest.json binds it by size and SHA-256.",
    }
    binding_payload = _json_bytes(binding_document)
    files["W65_SOURCE_BINDINGS.json"] = (binding_payload, "documentation")
    for path, (payload, role) in sorted(files.items()):
        rel = PurePosixPath(path)
        if rel.is_absolute() or any(part in {"", ".", ".."} for part in rel.parts) or "\\" in path:
            raise ValueError(f"unsafe generated package path: {path!r}")
        target = package_dir.joinpath(*rel.parts)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)

    manifest_files = [
        {"path": path, "sha256": _sha(payload), "size": len(payload), "role": role}
        for path, (payload, role) in sorted(files.items())
    ]
    manifest = {
        "schema_version": 1, "plugin_api": 3, "id": plugin_id, "name": name,
        "version": version, "publisher": PUBLISHER, "license": "MIT",
        "description": f"{name} {version}, bound to an application-owned API 3 release pin.",
        "requires_app": APP_FLOOR, "capabilities": capabilities,
        "entrypoints": entrypoints, "files": manifest_files,
        "ui_contributions": ui,
    }
    manifest_bytes = _json_bytes(manifest)
    (package_dir / "manifest.json").write_bytes(manifest_bytes)
    archive_path = out / ("openfoam-case-studio.zip" if kind == "studio" else "openfoam-linter.zip")
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in ["manifest.json", *sorted(files)]:
            payload = manifest_bytes if path == "manifest.json" else files[path][0]
            info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            info.external_attr = (stat.S_IFREG | 0o644) << 16
            archive.writestr(info, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
    pin_proposal = {
        "plugin_id": plugin_id, "version": version, "publisher": PUBLISHER,
        "api": 3, "capabilities": capabilities, "entrypoints": entrypoints,
        "manifest_sha256": _sha(manifest_bytes),
        "files": [[entry["path"], entry["role"], entry["sha256"]] for entry in manifest_files],
    }
    return {
        "plugin_id": plugin_id, "version": version, "manifest_sha256": _sha(manifest_bytes),
        "zip_path": archive_path.name, "zip_sha256": _sha(archive_path.read_bytes()),
        "file_count": len(manifest_files), "pin_proposal": pin_proposal,
        "package_dir": package_dir.name,
    }


def _verify_zip(root: Path, out: Path, commit: str, result: dict) -> None:
    archive_path = out / result["zip_path"]
    with zipfile.ZipFile(archive_path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError(f"duplicate archive path in {archive_path.name}")
        if len({name.casefold() for name in names}) != len(names):
            raise ValueError(f"case-colliding archive paths in {archive_path.name}")
        if any(PurePosixPath(name).is_absolute() or "\\" in name or ".." in PurePosixPath(name).parts for name in names):
            raise ValueError(f"unsafe path in {archive_path.name}")
        if {name for name in names if name != "manifest.json"} != {
            entry["path"] for entry in json.loads((out / result["package_dir"] / "manifest.json").read_bytes())["files"]
        }:
            raise ValueError(f"archive contents differ from manifest in {archive_path.name}")
        for info in archive.infolist():
            if stat.S_ISLNK(info.external_attr >> 16):
                raise ValueError(f"symlink payload in {archive_path.name}: {info.filename}")
    package_dir = out / result["package_dir"]
    manifest = json.loads((package_dir / "manifest.json").read_bytes())
    binding_path = package_dir / "W65_SOURCE_BINDINGS.json"
    bindings = json.loads(binding_path.read_bytes())
    rows = bindings.get("source_files", [])
    bound_paths = [row.get("package_path") for row in rows]
    expected_bound = {entry["path"] for entry in manifest["files"]
                      if entry["path"] != "W65_SOURCE_BINDINGS.json"}
    if len(bound_paths) != len(set(bound_paths)) or set(bound_paths) != expected_bound:
        raise ValueError(f"source-binding coverage differs from payload files in {archive_path.name}")
    for row in rows:
        rel = PurePosixPath(str(row["package_path"]))
        target = package_dir.joinpath(*rel.parts)
        if _sha(target.read_bytes()) != row.get("output_sha256"):
            raise ValueError(f"source-binding output digest mismatch: {archive_path.name}:{rel}")
        source_bytes = _git_bytes(root, commit, row["source_path"])
        actual_blob = _git(root, "rev-parse", f"{commit}:{row['source_path']}")
        if (actual_blob != row.get("git_blob")
                or _sha(source_bytes) != row.get("source_sha256")
                or len(source_bytes) != row.get("source_bytes")):
            raise ValueError(f"source binding does not match Git blob: {row['source_path']}")
    for dependency in bindings.get("host_api_dependencies", []):
        source_bytes = _git_bytes(root, commit, dependency["source_path"])
        actual_blob = _git(root, "rev-parse", f"{commit}:{dependency['source_path']}")
        if (actual_blob != dependency.get("git_blob")
                or _sha(source_bytes) != dependency.get("source_sha256")
                or len(source_bytes) != dependency.get("source_bytes")):
            raise ValueError(f"host dependency binding does not match Git blob: {dependency['source_path']}")
    if _sha(archive_path.read_bytes()) != result["zip_sha256"]:
        raise ValueError(f"archive digest changed while verifying: {archive_path.name}")


def build(output: str) -> Path:
    root = Path(__file__).resolve().parents[1]
    status = _git(root, "status", "--porcelain")
    if status:
        raise RuntimeError("candidate build requires a clean committed source tree")
    commit = _git(root, "rev-parse", "HEAD")
    branch = _git(root, "branch", "--show-current")
    out = _safe_output_path(output)
    out.mkdir(parents=True)
    results = [_make_package(root, commit, out, kind="studio"), _make_package(root, commit, out, kind="linter")]
    for result in results:
        _verify_zip(root, out, commit, result)
    provenance = {
        "schema_version": 1,
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "source_repository": str(root), "source_commit": commit, "branch": branch,
        "worktree_clean": True, "generator": "tools/build_w65_openfoam_candidates.py",
        "generator_version": GENERATOR_VERSION, "python": sys.version,
        "artifacts": results,
        "host_execution_note": "Plugin engines are in-process; integrity pins do not create an OS sandbox.",
    }
    (out / "W65-OpenFOAM-FIX-PROVENANCE.json").write_bytes(_json_bytes(provenance))
    (out / "API3_RELEASE_PIN_PROPOSALS.json").write_bytes(_json_bytes({
        "source_commit": commit, "pins": [item["pin_proposal"] for item in results],
    }))
    checksum_rows = []
    for path in sorted(out.rglob("*")):
        if path.is_file() and path.name != "SHA256SUMS.txt":
            checksum_rows.append(f"{_sha(path.read_bytes())}  {path.relative_to(out).as_posix()}")
    (out / "SHA256SUMS.txt").write_text("\n".join(checksum_rows) + "\n", encoding="utf-8")
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, help="new, non-existent candidate output directory")
    args = parser.parse_args()
    try:
        print(build(args.output))
    except Exception as exc:
        print(f"candidate build failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
