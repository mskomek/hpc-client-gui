"""wx job-draft flow: open a case first, then review Allrun plus wrapper.

Mirrors the Qt flow with wx dialogs. Saving stays create-only and the
wrapper save stays disabled until the on-disk Allrun matches the
reviewed digest. Remote saves use the live main-window session.
"""

from __future__ import annotations

from hpc_gui.core.i18n import t

from .job_draft import (
    DEFAULT_JOB_NAME,
    DEFAULT_MODULE,
    DEFAULT_TIME,
    build_draft_bundle,
    validate_job_spec,
)
from .job_draft_store import DEFAULT_JOB_FILENAME, allrun_matches, create_local_job, create_remote_job


def _wx_session_files(page):
    session = (getattr(page, "session_state", None) or {}).get("session") or {}
    if isinstance(session, dict) and session.get("files") is not None:
        return session.get("files")
    cursor = getattr(page, "panel", None)
    seen = set()
    while cursor is not None and id(cursor) not in seen:
        seen.add(id(cursor))
        state = getattr(cursor, "session_state", None)
        if isinstance(state, dict):
            session = state.get("session") or {}
            if isinstance(session, dict) and session.get("files") is not None:
                try:
                    page.session_state = state
                except Exception:
                    pass
                return session.get("files")
        getter = getattr(cursor, "GetParent", None)
        try:
            cursor = getter() if callable(getter) else None
        except Exception:
            break
    return None


def ensure_case_for_draft(page) -> bool:
    """Guide the user to open a case before any draft preview."""
    if getattr(page, "workspace", None) is not None:
        return True
    page.status.SetLabel(t("openfoam.no_case"))
    try:
        page.case_manager_actions._open_case(None)
    except Exception as exc:
        page._show_error(t("openfoam.case_open_failed").format(error=exc))
    return False


def build_wx_bundle(page, *, job_name, nodes, ntasks, time, partition, module):
    """Validate inputs and render Allrun plus wrapper; raises on violation."""
    spec = validate_job_spec(
        job_name=(job_name or "").strip() or DEFAULT_JOB_NAME,
        nodes=int(nodes),
        ntasks=int(ntasks),
        time=(time or "").strip() or DEFAULT_TIME,
        partition=(partition or "").strip(),
        module=(module or "").strip() or DEFAULT_MODULE,
    )
    if page.workspace is None:
        raise ValueError(t("openfoam.no_case"))
    if page.workspace.read_only:
        raise PermissionError(t("openfoam.read_only_snapshot"))
    if page.workspace.modified_paths():
        raise ValueError(t("openfoam.unsaved_draft_blocked"))
    return build_draft_bundle(page.documents, page.command_catalog, page.workflow_plan.steps, spec)


def _prompt_text(wx, parent, title, message, default):
    dialog = wx.TextEntryDialog(parent, message, title, default)
    try:
        if dialog.ShowModal() != wx.ID_OK:
            return None
        return dialog.GetValue()
    finally:
        dialog.Destroy()


def open_job_draft(page) -> bool:
    """Prompt for a case when needed, then review and optionally save a draft."""
    wx = page.wx
    if not ensure_case_for_draft(page):
        return False
    job_name = _prompt_text(
        wx, page.panel, t("openfoam.job_draft_title"), t("openfoam.job_name"), DEFAULT_JOB_NAME
    )
    if job_name is None:
        return False
    ntasks_text = _prompt_text(
        wx, page.panel, t("openfoam.job_draft_title"), t("openfoam.tasks"), "1"
    )
    if ntasks_text is None:
        return False
    try:
        ntasks = int(str(ntasks_text).strip())
    except ValueError:
        page._show_error(t("openfoam.ntasks_integer_required"))
        return False
    time_text = _prompt_text(
        wx, page.panel, t("openfoam.job_draft_title"), t("openfoam.walltime"), DEFAULT_TIME
    )
    if time_text is None:
        return False
    try:
        bundle = build_wx_bundle(
            page, job_name=job_name, nodes=1, ntasks=ntasks,
            time=time_text, partition="", module=DEFAULT_MODULE,
        )
    except Exception as exc:
        page._show_error(t("openfoam.draft_build_failed").format(error=exc))
        return False
    preview = (
        t("openfoam.draft_preview_header").format(
            solver=bundle.solver, sha256=bundle.allrun_sha256
        )
        + f"\n\n{t('openfoam.generated_allrun_review')}\n{bundle.allrun_text}\n\n"
        + f"{t('openfoam.generated_slurm_review')}\n{bundle.slurm_text}\n\n"
        + t("openfoam.nothing_submitted")
    )
    viewer = wx.Dialog(page.panel, title=t("openfoam.job_draft_title"))
    try:
        viewer.SetSize((760, 560))
        sizer = wx.BoxSizer(wx.VERTICAL)
        text = wx.TextCtrl(viewer, value=preview, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        sizer.Add(text, 1, wx.EXPAND | wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        create_button = wx.Button(viewer, label=t("openfoam.create_allrun_create_only"))
        save_button = wx.Button(viewer, label=t("openfoam.save_wrapper_create_only"))
        close_button = wx.Button(viewer, label=t("openfoam.close"))
        for button in (create_button, save_button, close_button):
            row.Add(button, 0, wx.ALL, 4)
        sizer.Add(row, 0, wx.ALIGN_RIGHT)
        viewer.SetSizer(sizer)
        trusted = allrun_matches(page.workspace, bundle.allrun_sha256)
        save_button.Enable(bool(trusted))

        def _on_create(_event):
            try:
                page.workspace.create_allrun(bundle.allrun_text)
            except FileExistsError as exc:
                page._show_error(t("openfoam.allrun_preserved").format(error=exc))
                return
            except Exception as exc:
                page._show_error(t("openfoam.allrun_create_failed").format(error=exc))
                return
            save_button.Enable(allrun_matches(page.workspace, bundle.allrun_sha256))

        def _on_save(_event):
            if not allrun_matches(page.workspace, bundle.allrun_sha256):
                page._show_error(t("openfoam.draft_allrun_mismatch"))
                save_button.Enable(False)
                return
            try:
                if page.workspace.remote:
                    files = _wx_session_files(page)
                    if files is None:
                        page._show_error(t("openfoam.remote_unavailable"))
                        return
                    path = create_remote_job(
                        page.workspace.root, files, bundle.slurm_text, filename=DEFAULT_JOB_FILENAME
                    )
                else:
                    path = create_local_job(
                        page.workspace.root, bundle.slurm_text, filename=DEFAULT_JOB_FILENAME
                    )
            except FileExistsError as exc:
                page._show_error(t("openfoam.wrapper_preserved").format(error=exc))
                return
            except Exception as exc:
                page._show_error(t("openfoam.wrapper_save_failed").format(error=exc))
                return
            page.status.SetLabel(t("openfoam.wrapper_created").format(path=path))
            save_button.Enable(False)

        create_button.Bind(wx.EVT_BUTTON, _on_create)
        save_button.Bind(wx.EVT_BUTTON, _on_save)
        close_button.Bind(wx.EVT_BUTTON, lambda _event: viewer.EndModal(wx.ID_OK))
        viewer.ShowModal()
        return True
    finally:
        viewer.Destroy()
