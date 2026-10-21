"""Local job snapshots and Jobs-to-Files navigation callbacks."""

from __future__ import annotations


def make_persistence_callbacks(context):
    def delete_job_details(job_ids):
        identities = [
            context.scoped_record(job_id)
            for job_id in job_ids
            if str(job_id).strip()
        ]
        return context.job_store().delete_details(identities)

    def save_output_snapshot(job_id, channel_id, path, content):
        text = str(content or "")
        if not text:
            return
        import time

        context.job_store().record_observation({
            **context.scoped_record(job_id),
            "source": "output_read",
            "outputs": {
                str(channel_id): {
                    "path": str(path or ""),
                    "text": text,
                    "captured_at": time.time(),
                    "source": "remote",
                }
            },
        })

    def load_output_snapshots(job_id):
        record = context.job_store().get(str(job_id), **context.profile_identity())
        return dict(record.get("outputs") or {}) if record else {}

    def save_job_raw_snapshot(job_id, kind, content):
        text = str(content or "")
        if not text or kind not in {"raw_details", "raw_accounting"}:
            return
        context.job_store().record_observation({
            **context.scoped_record(job_id),
            "source": "details_read",
            "details": {kind: text},
        })

    def output_channel_defs():
        from hpc_gui.services.output_channel_resolver import definitions_from_provider

        config = context.resolve_provider_config()
        return definitions_from_provider(config.get("job_outputs"))

    def open_main_files(path="", highlight_path=""):
        state = context.state
        main_notebook = state.get("_embedded_main_notebook")
        files_page = state.get("_embedded_files_page")
        remote_panel = state.get("_embedded_remote_files_panel")
        if main_notebook is None or files_page is None or remote_panel is None:
            return False
        path = str(path or "").strip()
        if not path:
            return False
        page_index = next(
            (index for index in range(main_notebook.GetPageCount())
             if main_notebook.GetPage(index) is files_page),
            -1,
        )
        if page_index >= 0:
            main_notebook.SetSelection(page_index)
        remote_notebook = getattr(remote_panel, "_wx_remote_notebook", None)
        tabs = getattr(remote_panel, "_wx_remote_tabs", ())
        if remote_notebook is not None and tabs:
            active_index = remote_notebook.GetSelection()
            if 0 <= active_index < len(tabs):
                tabs[active_index]["highlight_path"] = str(highlight_path or "")
        controls = getattr(remote_panel, "_wx_remote_controls", {})
        navigate = controls.get("navigate")
        load = controls.get("load")
        if not callable(navigate) or not callable(load):
            return False
        navigate(path)
        load()
        return True

    return {
        "delete_job_details": delete_job_details,
        "save_output_snapshot": save_output_snapshot,
        "load_output_snapshots": load_output_snapshots,
        "save_job_raw_snapshot": save_job_raw_snapshot,
        "output_channel_defs": None,
        "output_channel_defs_provider": output_channel_defs,
        "open_main_files": open_main_files,
    }
