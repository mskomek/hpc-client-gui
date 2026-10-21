"""Provider capability, cluster-status parsing, and raw response display."""

from __future__ import annotations

from dataclasses import dataclass
from threading import Thread
from typing import Any, Callable

from hpc_gui.core.i18n import t
from hpc_gui.services.parser_registry import parse as parse_with_registry
from hpc_gui.services.provider_contract import extract_contract
from hpc_gui.services.raw_command_result import RawCommandResult


@dataclass
class ProviderStatusBindings:
    state: dict[str, Any]
    state_lock: Any
    kwargs: dict[str, Any]
    refresh_status: Callable | None
    has_status_capability: Callable | None
    generation: Callable | None
    post: Callable
    table: Any
    servers_text: Any
    servers_box: Any
    status_text: Any
    refresh_button: Any
    raw_button: Any
    page_sizer: Any
    host: Any
    show_raw_viewer: Callable


class ProviderStatusController:
    """Load status through the active provider contract with stale guards."""

    def __init__(self, bindings: ProviderStatusBindings) -> None:
        self.bindings = bindings

    def provider_connected(self) -> bool:
        b = self.bindings
        if b.state.get("session_state_supplied"):
            return b.state.get("session") is not None
        return bool(
            b.kwargs.get("provider_connected")
            or callable(b.has_status_capability)
            or callable(b.refresh_status)
        )

    def provider_status_supported(self) -> bool:
        b = self.bindings
        if not self.provider_connected() or not callable(b.refresh_status):
            return False
        try:
            return (
                bool(b.has_status_capability())
                if callable(b.has_status_capability)
                else True
            )
        except Exception:
            return False

    def refresh_raw_status(self):
        b = self.bindings
        if not self.provider_status_supported():
            return b.state.get("raw_status_result")
        request_generation = b.generation() if callable(b.generation) else None
        provider_generation = b.state["provider_generation"]
        try:
            result = self._call_status()
            raw = self._normalize(result)
        except Exception as error:
            raw = RawCommandResult.from_response(
                source_id="lssrv", command="lssrv",
                stdout="", stderr=str(error), exit_code=1,
            )
        if not self._is_current(provider_generation, request_generation):
            return b.state.get("raw_status_result")
        b.state["raw_status_result"] = raw
        return raw

    def open_raw_status(self, _event=None):
        b = self.bindings
        result = b.state.get("raw_status_result")
        if result is None:
            result = RawCommandResult(
                source_id="lssrv", command="lssrv", stdout="",
                stderr=t("jobs_outputs.raw_not_available"), exit_code=-1,
            )
        b.show_raw_viewer(
            b.host, result, title=t("raw_viewer.raw_server_status"),
            refresh_callback=self.refresh_raw_status,
        )

    def toggle_cluster_servers(self, _event=None) -> None:
        bindings = self.bindings
        bindings.servers_box.Show(not bindings.servers_box.IsShown())
        bindings.page_sizer.Layout()

    def render_servers(self, raw_text: str, parsed_rows=None) -> None:
        b = self.bindings
        rows = parsed_rows if parsed_rows is not None else self._parse_builtin_rows(raw_text)
        b.table.DeleteAllItems()
        for item in rows:
            index = b.table.InsertItem(b.table.GetItemCount(), item.partition)
            b.table.SetItem(index, 1, item.free_cpus)
            b.table.SetItem(index, 2, item.total_cpus)
            b.table.SetItem(index, 3, item.memory_mb_per_core)
        b.servers_text.SetLabel("")
        if rows:
            key = "jobs_outputs.cluster_status_loaded"
        elif str(raw_text or "").strip():
            b.state["status_parse_error"] = "invalid cluster status"
            key = "jobs_outputs.parse_error_cluster"
        else:
            key = "jobs_outputs.no_cluster_status"
        b.state["cluster_status_key"] = key
        b.status_text.SetLabel(t(key))
        b.table.Show(bool(rows))

    def refresh_provider_status(self, _event=None) -> None:
        b, state = self.bindings, self.bindings.state
        if not self.provider_connected():
            self._show_unavailable("jobs_outputs.no_cluster_connection")
            return
        if not self.provider_status_supported():
            self._show_unavailable("jobs_outputs.cluster_unsupported")
            return
        b.servers_box.Show()
        b.refresh_button.Enable(True)
        b.raw_button.Enable(True)
        state["cluster_status_key"] = "jobs_outputs.refreshing_cluster_status"
        b.status_text.SetLabel(t("jobs_outputs.refreshing_cluster_status"))
        b.table.Hide()
        with b.state_lock:
            state["status_request_id"] += 1
            request_id = state["status_request_id"]
            state["status_in_flight"] = True
            provider_generation = state["provider_generation"]
        session_generation = b.generation() if callable(b.generation) else None

        def worker():
            try:
                result = self._call_status()
                b.post(done, result, None, request_id, provider_generation, session_generation)
            except Exception as error:
                b.post(done, "", error, request_id, provider_generation, session_generation)

        def done(result, error, response_id, response_provider_generation, response_session_generation):
            state["status_in_flight"] = False
            if (
                state["closed"] or response_id != state["status_request_id"]
                or response_provider_generation != state["provider_generation"]
                or callable(b.generation) and response_session_generation != b.generation()
            ):
                return
            raw = self._normalize(result, error=error)
            state["raw_status_result"] = raw
            if raw.has_error:
                b.table.DeleteAllItems()
                b.table.Hide()
                state["cluster_status_key"] = "jobs_outputs.cluster_status_failed"
                b.status_text.SetLabel(t("jobs_outputs.cluster_status_failed"))
            else:
                state["status_parse_error"] = ""
                self.render_servers(raw.stdout, self._parse_contract_rows(raw.stdout))
            b.page_sizer.Layout()

        Thread(target=worker, daemon=True).start()

    def _call_status(self):
        callback = self.bindings.refresh_status
        if not callable(callback):
            raise RuntimeError("Provider cluster status is unavailable")
        try:
            return callback()
        except TypeError:
            return callback("")

    def _normalize(self, result, error=None) -> RawCommandResult:
        if isinstance(result, RawCommandResult):
            return result
        return RawCommandResult.from_response(
            source_id="lssrv", command="lssrv",
            stdout="" if error else str(result or ""),
            stderr=str(error) if error else "", exit_code=1 if error else -1,
        )

    def _is_current(self, provider_generation, request_generation) -> bool:
        generation = self.bindings.generation
        return (
            provider_generation == self.bindings.state["provider_generation"]
            and (
                not callable(generation)
                or generation() == request_generation
            )
        )

    def _parse_contract_rows(self, raw_text):
        state = self.bindings.state
        try:
            session = state.get("session") or {}
            profile = session.get("profile") or {}
            template = profile.get("provider_template") if isinstance(profile, dict) else None
            parser_id = extract_contract(template).cluster_status_parser
            if parser_id:
                parsed = parse_with_registry(parser_id, raw_text, raw_source_id="lssrv")
                if parsed.ok and isinstance(parsed.data, list):
                    return parsed.data
                if parsed.error:
                    state["status_parse_error"] = parsed.error.message
                    return []
        except Exception as error:
            state["status_parse_error"] = str(error)
        return None

    @staticmethod
    def _parse_builtin_rows(raw_text):
        parsed = parse_with_registry(
            "truba.lssrv.v1", str(raw_text or ""), raw_source_id="lssrv"
        )
        return parsed.data if parsed.ok and isinstance(parsed.data, list) else []

    def _show_unavailable(self, key) -> None:
        b, state = self.bindings, self.bindings.state
        state["raw_status_result"] = None
        state["status_parse_error"] = ""
        state["cluster_status_key"] = key
        b.table.DeleteAllItems()
        b.servers_box.Hide()
        b.status_text.SetLabel(t(key))
        b.refresh_button.Enable(False)
        b.raw_button.Enable(False)
        b.page_sizer.Layout()
