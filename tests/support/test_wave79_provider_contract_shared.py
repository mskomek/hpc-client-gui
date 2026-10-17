from types import SimpleNamespace
import pytest
from hpc_gui.services.parser_registry import (
    ParseResult, parse, register_parser, known_parser_ids,
)
from hpc_gui.services.adapter_registry import (
    known_adapter_ids,
)
from hpc_gui.services.parsers import (
    ScontrolJobDetails, SacctAccountingResult,
)
from hpc_gui.services.cluster_server_status import ClusterServerStatus
from hpc_gui.services.raw_command_result import RawCommandResult
from hpc_gui.services.provider_contract import (
    execute_adapter, extract_contract, parse_with_contract,
)
from hpc_gui.services.parser_error_ux import (
    format_error_for_user, format_error_with_raw_hint, is_backend_error, is_parser_error,
)
from hpc_gui.plugins.validator import validate_cluster_profile_dict

__all__ = [
    'SimpleNamespace',
    'pytest',
    'ParseResult',
    'parse',
    'register_parser',
    'known_parser_ids',
    'known_adapter_ids',
    'ScontrolJobDetails',
    'SacctAccountingResult',
    'ClusterServerStatus',
    'RawCommandResult',
    'execute_adapter',
    'extract_contract',
    'parse_with_contract',
    'format_error_for_user',
    'format_error_with_raw_hint',
    'is_backend_error',
    'is_parser_error',
    'validate_cluster_profile_dict',
]
