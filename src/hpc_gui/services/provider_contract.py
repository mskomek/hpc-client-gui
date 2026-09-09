"""Provider contract loader for Wave 79.

Extracts declarative parser/adapter contracts from loaded cluster profiles
and maps them to the parser/adapter registries.

Provider configs may specify:
    job_details:   {adapter: "slurm.scontrol.job", parser: "slurm.scontrol.v1"}
    accounting:    {adapter: "slurm.sacct.job",    parser: "slurm.sacct.pipe.v1"}
    cluster_status: {adapter: "truba.lssrv",       parser: "truba.lssrv.v1"}

Missing sections mean unsupported/default based on scheduler semantics.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Mapping

from hpc_gui.services.parser_registry import parse, ParseResult
from hpc_gui.services.adapter_registry import get_adapter

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class ProviderContract:
    """Resolved provider contract from a cluster profile."""

    job_details_adapter: str | None = None
    job_details_parser: str | None = None
    accounting_adapter: str | None = None
    accounting_parser: str | None = None
    cluster_status_adapter: str | None = None
    cluster_status_parser: str | None = None

    @property
    def has_job_details(self) -> bool:
        return bool(self.job_details_adapter or self.job_details_parser)

    @property
    def has_accounting(self) -> bool:
        return bool(self.accounting_adapter or self.accounting_parser)

    @property
    def has_cluster_status(self) -> bool:
        return bool(self.cluster_status_adapter or self.cluster_status_parser)


def extract_contract(provider_template: Mapping[str, Any] | None) -> ProviderContract:
    """Extract a ProviderContract from a provider_template dict.

    Safe for missing/malformed sections — returns empty contract on error.
    """
    if not isinstance(provider_template, Mapping):
        return ProviderContract()

    def _get_str(section: str, key: str) -> str | None:
        sec = provider_template.get(section)
        if isinstance(sec, dict):
            val = sec.get(key)
            return str(val) if isinstance(val, str) and val.strip() else None
        return None

    return ProviderContract(
        job_details_adapter=_get_str("job_details", "adapter"),
        job_details_parser=_get_str("job_details", "parser"),
        accounting_adapter=_get_str("accounting", "adapter"),
        accounting_parser=_get_str("accounting", "parser"),
        cluster_status_adapter=_get_str("cluster_status", "adapter"),
        cluster_status_parser=_get_str("cluster_status", "parser"),
    )


def execute_adapter(adapter_id: str, *args: Any, **kwargs: Any) -> Any:
    """Execute a registered adapter by ID.

    Returns None if adapter is unknown.
    """
    spec = get_adapter(adapter_id)
    if spec is None:
        log.warning("Unknown adapter: %s", adapter_id)
        return None
    return spec.execute(*args, **kwargs)


def parse_with_contract(
    parser_id: str | None,
    raw_text: str,
    parser_config: dict[str, Any] | None = None,
    *,
    raw_source_id: str = "",
) -> ParseResult:
    """Parse raw text using the contract-specified parser.

    Falls back gracefully if parser_id is None or unknown.
    """
    if not parser_id:
        return ParseResult.fail("unsupported", "No parser configured", raw_source_id=raw_source_id)
    return parse(parser_id, raw_text, parser_config, raw_source_id=raw_source_id)
