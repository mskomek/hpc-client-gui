"""Render Journal Studio source text without long single-thread UI stalls."""

_CHUNK_CHARS = 8 * 1024
_ASYNC_RENDER_THRESHOLD = 64 * 1024
MAX_VISUAL_STRUCTURE_LINES = 10_000
MAX_VISUAL_STRUCTURE_CHARS = 4 * 1024 * 1024


def exceeds_visual_limits(text: str) -> bool:
    return (
        len(text) > MAX_VISUAL_STRUCTURE_CHARS
        or len(text.splitlines()) > MAX_VISUAL_STRUCTURE_LINES
    )


def render_source(editor, display_text: str) -> None:
    editor._source_model_at_render = editor.document.text
    editor._source_text_at_render = display_text
    editor._source_render_generation += 1
    generation = editor._source_render_generation
    source = editor.source
    if getattr(editor, "_source_render_frozen", False):
        try:
            source.Thaw()
        except Exception:
            pass
        editor._source_render_frozen = False
    setter = getattr(source, "SetText", None) or getattr(source, "SetValue")
    append = getattr(source, "AddText", None)

    if len(display_text) <= _ASYNC_RENDER_THRESHOLD or not callable(append):
        editor._rendering_source = True
        try:
            setter(display_text)
        finally:
            editor._rendering_source = False
            source.Enable(True)
        editor._schedule_refresh()
        return

    editor._rendering_source = True
    if exceeds_visual_limits(display_text):
        try:
            import wx.stc as stc

            source.SetLexer(stc.STC_LEX_NULL)
            editor._source_highlighting_paused = True
        except Exception:
            pass
    try:
        source.Freeze()
        editor._source_render_frozen = True
    except Exception:
        editor._source_render_frozen = False
    setter("")
    source.Enable(False)
    offset = 0

    def append_chunk(_event=None) -> None:
        nonlocal offset
        if generation != editor._source_render_generation:
            return
        try:
            if not source or source.IsBeingDeleted():
                return
        except Exception:
            return
        end = min(offset + _CHUNK_CHARS, len(display_text))
        source.AddText(display_text[offset:end])
        offset = end
        if end < len(display_text):
            editor.wx.CallAfter(append_chunk)
            return
        if hasattr(source, "EmptyUndoBuffer"):
            source.EmptyUndoBuffer()
        if hasattr(source, "SetSavePoint"):
            source.SetSavePoint()
        source.Enable(True)
        if editor._source_render_frozen:
            source.Thaw()
            editor._source_render_frozen = False
        editor._rendering_source = False
        editor._schedule_refresh()

    editor.wx.CallAfter(append_chunk)
