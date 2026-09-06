"""Plugin-delivered job templates: safe loading and rendering.

Templates are declarative text with a limited ``{{variable}}`` placeholder
syntax. Rendering performs plain substitution after validation; nothing is
executed, and no shell/Python expression syntax is supported.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hpc_gui import __version__
from hpc_gui.plugins.loader import load_installed_plugins


class JobTemplateError(ValueError):
    """Raised for malformed templates or invalid render values."""


VARIABLE_TYPES = frozenset({"string", "integer", "boolean", "choice", "path"})

_PLACEHOLDER_RE = re.compile(r"\{\{([a-z][a-z0-9_]*)\}\}")

_MAX_TEMPLATE_BYTES = 256 * 1024


@dataclass(frozen=True)
class TemplateVariable:
    name: str
    type: str = "string"
    required: bool = False
    default: str | int | bool | None = None
    minimum: int | None = None
    maximum: int | None = None
    choices: tuple[str, ...] = ()
    description: str = ""


@dataclass(frozen=True)
class JobTemplate:
    id: str
    name: str
    scheduler: str
    plugin_id: str
    plugin_version: str
    file_name: str
    description: str = ""
    application: str = ""
    variables: tuple[TemplateVariable, ...] = ()
    content: str = ""

    def variable(self, name: str) -> TemplateVariable | None:
        return next((v for v in self.variables if v.name == name), None)


def _parse_variable(raw: Any, label: str) -> TemplateVariable:
    if not isinstance(raw, dict):
        raise JobTemplateError(f"{label}: variable must be a JSON object")
    name = raw.get("name")
    var_type = raw.get("type", "string")
    if not isinstance(name, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", name):
        raise JobTemplateError(f"{label}: invalid variable name {name!r}")
    if var_type not in VARIABLE_TYPES:
        raise JobTemplateError(f"{label} [{name}]: unsupported type {var_type!r}")
    choices_raw = raw.get("choices")
    if var_type == "choice":
        if (
            not isinstance(choices_raw, list)
            or not choices_raw
            or not all(isinstance(c, str) for c in choices_raw)
        ):
            raise JobTemplateError(f"{label} [{name}]: choice needs a non-empty choices list")
    minimum = raw.get("minimum") if isinstance(raw.get("minimum"), int) else None
    maximum = raw.get("maximum") if isinstance(raw.get("maximum"), int) else None
    default = raw.get("default")
    return TemplateVariable(
        name=name,
        type=var_type,
        required=bool(raw.get("required", False)),
        default=default,
        minimum=minimum,
        maximum=maximum,
        choices=tuple(choices_raw) if isinstance(choices_raw, list) else (),
        description=str(raw.get("description") or ""),
    )


def _parse_index(index: dict, package_dir: Path, plugin_id: str, version: str) -> list[JobTemplate]:
    templates_raw = index.get("templates")
    if not isinstance(templates_raw, list):
        raise JobTemplateError("job template index needs a 'templates' list")

    templates: list[JobTemplate] = []
    for position, raw in enumerate(templates_raw):
        label = f"template #{position + 1}"
        if not isinstance(raw, dict):
            raise JobTemplateError(f"{label}: must be a JSON object")
        template_id = raw.get("id")
        name = raw.get("name")
        scheduler = raw.get("scheduler", "")
        content_path = raw.get("content_path")
        if not isinstance(template_id, str) or not template_id:
            raise JobTemplateError(f"{label}: missing id")
        if not isinstance(name, str) or not name:
            raise JobTemplateError(f"{label} [{template_id}]: missing name")
        if not isinstance(scheduler, str) or not scheduler:
            raise JobTemplateError(f"{label} [{template_id}]: missing scheduler")
        if not isinstance(content_path, str) or not content_path:
            raise JobTemplateError(f"{label} [{template_id}]: missing content_path")
        if content_path.startswith("/") or ".." in content_path.split("/") or "\\" in content_path:
            raise JobTemplateError(f"{label} [{template_id}]: unsafe content_path {content_path!r}")
        declared_file_name = raw.get("file_name", "job.sh")
        if not isinstance(declared_file_name, str) or not declared_file_name:
            raise JobTemplateError(f"{label} [{template_id}]: invalid file_name")

        variables = tuple(
            _parse_variable(v, f"{label} [{template_id}]")
            for v in raw.get("variables") or []
        )

        payload_path = package_dir / content_path
        try:
            payload = payload_path.read_bytes()
        except OSError as exc:
            raise JobTemplateError(
                f"{label} [{template_id}]: cannot read '{content_path}': {exc}"
            ) from exc
        if len(payload) > _MAX_TEMPLATE_BYTES:
            raise JobTemplateError(f"{label} [{template_id}]: template exceeds the size limit")
        expected_sha = raw.get("sha256")
        if expected_sha is not None and hashlib.sha256(payload).hexdigest() != expected_sha:
            raise JobTemplateError(f"{label} [{template_id}]: content SHA-256 mismatch")
        try:
            content = payload.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise JobTemplateError(f"{label} [{template_id}]: template is not UTF-8: {exc}") from exc

        # Every placeholder in the content must be a declared variable.
        declared = {variable.name for variable in variables}
        unknown = sorted(set(_PLACEHOLDER_RE.findall(content)) - declared)
        if unknown:
            raise JobTemplateError(
                f"{label} [{template_id}]: undeclared placeholders {unknown}"
            )
        unused = sorted(declared - set(_PLACEHOLDER_RE.findall(content)))
        if unused:
            # Declared but unused variables are tolerated (they may appear in
            # optional flows), but a required-unused pair would be odd; keep
            # permissive here.
            pass

        templates.append(
            JobTemplate(
                id=template_id,
                name=name,
                scheduler=scheduler,
                application=str(raw.get("application") or ""),
                description=str(raw.get("description") or ""),
                file_name=declared_file_name,
                variables=variables,
                content=content,
                plugin_id=plugin_id,
                plugin_version=version,
            )
        )
    if not templates:
        raise JobTemplateError("job template index provides no templates")
    return templates


def load_job_templates(root=None, app_version: str = __version__, plugin_id: str | None = None) -> list[JobTemplate]:
    """Load job templates from active, compatible installed plugins.

    When *plugin_id* is supplied only templates belonging to that plugin are
    returned.  The default ``None`` preserves the historic ``all templates``
    behaviour.
    """
    templates: list[JobTemplate] = []
    result = load_installed_plugins(root=root, app_version=app_version)
    for installed in result.plugins:
        if plugin_id is not None and installed.manifest.id != plugin_id:
            continue
        index = installed.job_templates_index
        if not isinstance(index, dict):
            continue
        try:
            templates.extend(
                _parse_index(
                    index,
                    installed.directory,
                    installed.manifest.id,
                    installed.manifest.version,
                )
            )
        except JobTemplateError:
            continue  # malformed template packs never break callers
    return templates


def render_template(template: JobTemplate, values: dict[str, object]) -> str:
    """Validate values and perform plain placeholder substitution."""

    def coerce(variable: TemplateVariable, value: object) -> str:
        if variable.type == "integer":
            if isinstance(value, bool) or not isinstance(value, int):
                parsed = value if isinstance(value, int) else None
                if parsed is None:
                    try:
                        parsed = int(str(value))
                    except ValueError:
                        raise JobTemplateError(
                            f"[{template.id}] variable '{variable.name}' must be an integer"
                        ) from None
            else:
                parsed = value
            if variable.minimum is not None and parsed < variable.minimum:
                raise JobTemplateError(
                    f"[{template.id}] variable '{variable.name}' must be >= {variable.minimum}"
                )
            if variable.maximum is not None and parsed > variable.maximum:
                raise JobTemplateError(
                    f"[{template.id}] variable '{variable.name}' must be <= {variable.maximum}"
                )
            return str(parsed)
        if variable.type == "boolean":
            if isinstance(value, bool):
                return "true" if value else "false"
            lowered = str(value).strip().lower()
            if lowered in ("true", "yes", "1"):
                return "true"
            if lowered in ("false", "no", "0"):
                return "false"
            raise JobTemplateError(
                f"[{template.id}] variable '{variable.name}' must be a boolean"
            )
        if variable.type == "choice":
            text_value = str(value)
            if variable.choices and text_value not in variable.choices:
                raise JobTemplateError(
                    f"[{template.id}] variable '{variable.name}' must be one of "
                    f"{list(variable.choices)}"
                )
            return text_value
        return str(value)

    resolved: dict[str, str] = {}
    allowed = {variable.name for variable in template.variables}
    for key in values:
        if key not in allowed:
            raise JobTemplateError(f"[{template.id}] unknown value '{key}'")

    for variable in template.variables:
        provided = values.get(variable.name)
        if provided is None or (isinstance(provided, str) and not provided.strip()):
            if variable.default is not None:
                resolved[variable.name] = coerce(variable, variable.default)
            elif variable.required:
                raise JobTemplateError(
                    f"[{template.id}] missing required variable '{variable.name}'"
                )
            else:
                resolved[variable.name] = ""
            continue
        resolved[variable.name] = coerce(variable, provided)

    return _PLACEHOLDER_RE.sub(lambda m: resolved[m.group(1)], template.content)
