"""UI-independent, read-only cluster self-test."""

from __future__ import annotations

import shlex
from dataclasses import asdict, dataclass, replace
from typing import Any, Callable, Mapping

from hpc_gui.services.connection_diagnostics import (
    _default_dns_resolve,
    _default_socket_connect,
    _default_ssh_factory,
    _sftp_available,
)
from hpc_gui.ssh.client import SSHConnInfo

PASS = "PASS"
FAIL = "FAIL"
WARNING = "WARNING"
UNSUPPORTED = "UNSUPPORTED"
NOT_CONFIGURED = "NOT_CONFIGURED"
NOT_TESTED = "NOT_TESTED"

_SCHEDULER_TOOLS = ("squeue", "sbatch", "scancel", "sacct", "scontrol")


@dataclass(frozen=True)
class SelfTestItem:
    id: str
    status: str
    detail: str = ""
    required: bool = False


@dataclass(frozen=True)
class SelfTestSection:
    id: str
    items: tuple[SelfTestItem, ...] = ()


@dataclass(frozen=True)
class ClusterSelfTestResult:
    status: str
    sections: tuple[SelfTestSection, ...]

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _item(item_id: str, status: str, detail: str = "", required: bool = False) -> SelfTestItem:
    return SelfTestItem(item_id, status, detail, required)


def _overall(sections: list[SelfTestSection]) -> str:
    items = [item for section in sections for item in section.items]
    if any(item.status == FAIL and item.required for item in items):
        return FAIL
    if any(item.status == WARNING for item in items):
        return WARNING
    return PASS


def _provider_value(provider: Any, key: str, default: Any = None) -> Any:
    if isinstance(provider, Mapping):
        return provider.get(key, default)
    return getattr(provider, key, default)


def _resolve_path(template: str, *, username: str, project: str, account: str) -> str | None:
    values = {"user": username, "user_first": username.split("@", 1)[0], "project": project, "account": account}
    try:
        return template.format(**values)
    except (KeyError, ValueError):
        return None


def run_cluster_self_test(
    info: SSHConnInfo,
    *,
    provider: Any = None,
    project: str = "",
    account: str = "",
    required_scheduler_tools: tuple[str, ...] = (),
    socket_connect: Callable[..., Any] | None = None,
    dns_resolve: Callable[..., Any] | None = None,
    ssh_factory: Callable[..., Any] | None = None,
) -> ClusterSelfTestResult:
    """Run bounded, read-only probes and return a UI-neutral result."""
    connection: list[SelfTestItem] = []
    scheduler: list[SelfTestItem] = []
    storage: list[SelfTestItem] = []
    provider_items: list[SelfTestItem] = []
    optional: list[SelfTestItem] = []
    sections = [
        SelfTestSection("Connection", tuple(connection)),
        SelfTestSection("Scheduler", tuple(scheduler)),
        SelfTestSection("Storage", tuple(storage)),
        SelfTestSection("Provider", tuple(provider_items)),
        SelfTestSection("Optional", tuple(optional)),
    ]
    dns_resolve = dns_resolve or _default_dns_resolve
    socket_connect = socket_connect or _default_socket_connect
    ssh_factory = ssh_factory or _default_ssh_factory
    wrapper: Any = None
    sock: Any = None

    def finish() -> ClusterSelfTestResult:
        if not scheduler:
            scheduler.extend(_item(tool, NOT_TESTED, "connection test did not reach scheduler") for tool in _SCHEDULER_TOOLS)
        if not storage:
            storage.append(_item("storage", NOT_TESTED, "connection test did not reach storage"))
        if not provider_items:
            provider_items.append(_item("provider", NOT_TESTED, "connection test did not reach provider metadata"))
        if not optional:
            optional.extend(
                (_item("checksum", NOT_TESTED, "connection test did not reach checksum"),
                 _item("x11", NOT_TESTED, "connection test did not reach X11"),
                 _item("quota", NOT_TESTED, "connection test did not reach quota"))
            )
        sections[0] = SelfTestSection("Connection", tuple(connection))
        sections[1] = SelfTestSection("Scheduler", tuple(scheduler))
        sections[2] = SelfTestSection("Storage", tuple(storage))
        sections[3] = SelfTestSection("Provider", tuple(provider_items))
        sections[4] = SelfTestSection("Optional", tuple(optional))
        return ClusterSelfTestResult(_overall(sections), tuple(sections))

    try:
        try:
            dns_resolve(info.host, info.port, info.timeout)
            connection.append(_item("dns", PASS, "name resolved", True))
        except Exception:
            connection.append(_item("dns", FAIL, "name resolution failed", True))
            return finish()
        try:
            sock = socket_connect(info.host, info.port, info.timeout)
            connection.append(_item("tcp", PASS, "port reachable", True))
        except Exception:
            connection.append(_item("tcp", FAIL, "port not reachable", True))
            return finish()
        try:
            wrapper = ssh_factory(replace(info, preconnected_socket=sock))
            sock = None
            connection.append(_item("ssh", PASS, "authenticated", True))
        except Exception:
            connection.append(_item("ssh", FAIL, "authentication failed", True))
            return finish()
        try:
            if _sftp_available(wrapper):
                connection.append(_item("sftp", PASS, "SFTP subsystem available", True))
            else:
                connection.append(_item("sftp", FAIL, "SFTP subsystem unavailable", True))
                return finish()
        except Exception:
            connection.append(_item("sftp", FAIL, "SFTP subsystem unavailable", True))
            return finish()

        provider_name = _provider_value(provider, "name", "")
        provider_id = _provider_value(provider, "profile_id", "")
        if provider is None:
            provider_items.append(_item("provider", NOT_CONFIGURED, "no provider profile configured"))
        else:
            provider_items.append(_item("provider", PASS, str(provider_name or provider_id or "provider")))

        for tool in _SCHEDULER_TOOLS:
            try:
                code, _, _ = wrapper.run(f"command -v {tool}", log_output=False)
                status = PASS if code == 0 else (FAIL if tool in required_scheduler_tools else WARNING)
                detail = "available" if code == 0 else "scheduler tool not found"
            except Exception:
                status = FAIL if tool in required_scheduler_tools else WARNING
                detail = "scheduler probe failed"
            scheduler.append(_item(tool, status, detail, tool in required_scheduler_tools))

        areas = _provider_value(provider, "storage", ()) if provider is not None else ()
        if not areas:
            storage.append(_item("storage", NOT_CONFIGURED, "no provider-defined storage is configured"))
        else:
            for index, area in enumerate(areas):
                area = area if isinstance(area, Mapping) else {}
                label = str(area.get("id") or area.get("label") or f"storage-{index}")
                template = str(area.get("path_template") or "").strip()
                path = _resolve_path(template, username=info.username, project=project, account=account) if template else None
                missing = [name for name, value in (("project", project), ("account", account)) if "{" + name + "}" in template and not value]
                if missing:
                    storage.append(_item(label, NOT_CONFIGURED, f"missing {', '.join(missing)}"))
                elif not path:
                    storage.append(_item(label, UNSUPPORTED, "storage path cannot be resolved"))
                else:
                    try:
                        code, _, _ = wrapper.run(f"test -d -- {shlex.quote(path)}", log_output=False)
                        storage.append(_item(label, PASS if code == 0 else WARNING, "directory available" if code == 0 else "directory unavailable"))
                    except Exception:
                        storage.append(_item(label, WARNING, "storage probe failed"))

        try:
            code, _, _ = wrapper.run("command -v sha256sum", log_output=False)
            optional.append(_item("checksum", PASS if code == 0 else WARNING, "sha256sum available" if code == 0 else "sha256sum unavailable"))
        except Exception:
            optional.append(_item("checksum", WARNING, "checksum probe failed"))
        if getattr(info, "x11_forwarding", False):
            try:
                code, _, _ = wrapper.run("command -v xauth", log_output=False)
                optional.append(_item("x11", PASS if code == 0 else WARNING, "X11 helper available" if code == 0 else "xauth unavailable"))
            except Exception:
                optional.append(_item("x11", WARNING, "X11 probe failed"))
        else:
            optional.append(_item("x11", NOT_CONFIGURED, "X11 forwarding is disabled"))
        quota_sources = _provider_value(provider, "quota_sources", ()) if provider is not None else ()
        optional.append(_item("quota", NOT_CONFIGURED if not quota_sources else NOT_TESTED, "no quota source configured" if not quota_sources else "quota probe is not run by self-test"))
        return finish()
    finally:
        if wrapper is not None:
            try:
                wrapper.close()
            except Exception:
                pass
        elif sock is not None:
            try:
                sock.close()
            except Exception:
                pass
