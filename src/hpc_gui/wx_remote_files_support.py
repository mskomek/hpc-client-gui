"""Pure formatting helpers for the wx remote-file browser."""

from hpc_gui.core.i18n import t
from hpc_gui.services.remote_entry_format import category as _shared_category, file_type as _shared_file_type, fmt_mtime as _shared_fmt_mtime, fmt_size as _shared_fmt_size

def _entry_name(entry) -> str:
    name = getattr(entry, "name", "") or ""
    if name:
        return str(name)
    raw = getattr(entry, "path", "") or ""
    return str(raw).replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]

def _format_mtime(mtime_val) -> str:
    return _shared_fmt_mtime(mtime_val)

def _type_label(entry) -> str:
    return _shared_file_type(_entry_name(entry), bool(getattr(entry, "is_dir", False)))

def _delete_confirm_text(names, location, *, generic_prompt=None, detail_template=None) -> str:
    """W23 FILE-035/036: confirmation names the actual target (path + items)."""
    from hpc_gui.services.file_context_actions import delete_confirm_message as _fallback
    from hpc_gui.services.file_context_actions import summarize_delete_targets as _summarize

    count, where, shown = _summarize(names, location)
    if count <= 0:
        return generic_prompt if generic_prompt is not None else t("dirs.delete_confirm")
    template = detail_template if detail_template is not None else t("dirs.delete_confirm_detail")
    if template.startswith("[dirs.delete_confirm_detail]"):
        return _fallback(names, location)
    try:
        return template.format(count=count, location=where, names=shown)
    except Exception:
        return _fallback(names, location)

def _remote_category(entry) -> str:
    try:
        return _shared_category(entry)
    except AttributeError:
        return "folders" if getattr(entry, "is_dir", False) else "other"

def _fmt_size(entry) -> str:
    return _shared_fmt_size(getattr(entry, "size", 0))
