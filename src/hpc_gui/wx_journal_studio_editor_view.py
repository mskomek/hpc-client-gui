"""Compose the Journal Studio editor controls and bind controller actions."""

from __future__ import annotations

from hpc_gui.core.i18n import t


def build_editor_view(editor) -> None:
    """Build the editor's resizable panels and bind them to *editor* methods."""
    wx = editor.wx
    root = wx.BoxSizer(wx.VERTICAL)
    meta = wx.WrapSizer(wx.HORIZONTAL)
    editor.product = wx.Choice(editor.page, choices=["Fluent"])
    editor.product.SetSelection(0)
    editor.product.Enable(False)
    editor.version = wx.Choice(editor.page, choices=["2025 R2 (25.2)"])
    editor.version.SetSelection(0)
    editor.version.Enable(False)
    editor.mode_choice = wx.Choice(
        editor.page, choices=[t("journal_studio.solution"), t("journal_studio.meshing")]
    )
    editor.mode_choice.SetSelection(1 if editor.mode == "meshing" else 0)
    editor.language_choice = wx.Choice(
        editor.page, choices=[t("journal_studio.tui"), t("journal_studio.scheme")]
    )
    editor.language_choice.SetSelection(1 if editor.language == "scheme" else 0)
    for label, control in (
        ("journal_studio.product", editor.product),
        ("journal_studio.version", editor.version),
        ("journal_studio.mode", editor.mode_choice),
        ("journal_studio.language", editor.language_choice),
    ):
        meta.Add(wx.StaticText(editor.page, label=t(label)), 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
        meta.Add(control, 0, wx.ALIGN_CENTER_VERTICAL | wx.ALL, 4)
    root.Add(meta, 0, wx.EXPAND)

    split = wx.SplitterWindow(editor.page, style=wx.SP_LIVE_UPDATE)
    editor.structure_panel = wx.Panel(split)
    editor.structure = wx.ListBox(editor.structure_panel, style=wx.LB_SINGLE)
    left = wx.BoxSizer(wx.VERTICAL)
    left.Add(wx.StaticText(editor.structure_panel, label=t("journal_studio.structure")), 0, wx.ALL, 4)
    left.Add(editor.structure, 1, wx.EXPAND | wx.ALL, 4)
    controls = wx.WrapSizer(wx.HORIZONTAL)
    editor.move_up = wx.Button(editor.structure_panel, label=t("journal_studio.move_up"))
    editor.move_down = wx.Button(editor.structure_panel, label=t("journal_studio.move_down"))
    editor.duplicate = wx.Button(editor.structure_panel, label=t("journal_studio.duplicate"))
    editor.delete = wx.Button(editor.structure_panel, label=t("journal_studio.delete"))
    for button in (editor.move_up, editor.move_down, editor.duplicate, editor.delete):
        controls.Add(button, 0, wx.ALL, 2)
    left.Add(controls, 0, wx.EXPAND | wx.ALL, 2)
    editor.structure_panel.SetSizer(left)

    work = wx.SplitterWindow(split, style=wx.SP_LIVE_UPDATE)
    source_panel = wx.Panel(work)
    source_sizer = wx.BoxSizer(wx.VERTICAL)
    editor.source = editor._make_source_control(source_panel)
    source_sizer.Add(wx.StaticText(source_panel, label=t("journal_studio.source")), 0, wx.ALL, 4)
    source_sizer.Add(editor.source, 1, wx.EXPAND | wx.ALL, 4)
    source_panel.SetSizer(source_sizer)

    library_panel = wx.Panel(work)
    library_sizer = wx.BoxSizer(wx.VERTICAL)
    library_sizer.Add(wx.StaticText(library_panel, label=t("journal_studio.library")), 0, wx.ALL, 4)
    editor.search = wx.SearchCtrl(library_panel, style=wx.TE_PROCESS_ENTER)
    editor.library = wx.ListBox(library_panel)
    editor.inspector = wx.TextCtrl(
        library_panel, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL
    )
    library_sizer.Add(editor.search, 0, wx.EXPAND | wx.ALL, 4)
    library_sizer.Add(editor.library, 1, wx.EXPAND | wx.ALL, 4)
    library_sizer.Add(wx.StaticText(library_panel, label=t("journal_studio.inspector")), 0, wx.ALL, 4)
    library_sizer.Add(editor.inspector, 0, wx.EXPAND | wx.ALL, 4)
    library_panel.SetSizer(library_sizer)
    work.SplitVertically(source_panel, library_panel, -310)
    split.SplitVertically(editor.structure_panel, work, 230)
    root.Add(split, 1, wx.EXPAND | wx.ALL, 4)

    editor.results = wx.Notebook(editor.page)
    editor.problems = editor._readonly_tab(editor.results)
    editor.diff = editor._readonly_tab(editor.results)
    editor.validation = editor._readonly_tab(editor.results)
    editor.preview = editor._readonly_tab(editor.results)
    for label, control in (
        ("journal_studio.problems", editor.problems),
        ("journal_studio.diff", editor.diff),
        ("journal_studio.validation", editor.validation),
        ("journal_studio.preview", editor.preview),
    ):
        editor.results.AddPage(control, t(label))
    root.Add(editor.results, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 4)
    editor.status = wx.StaticText(editor.page, label="")
    root.Add(editor.status, 0, wx.EXPAND | wx.ALL, 5)
    editor.page.SetSizer(root)

    editor.structure.Bind(wx.EVT_LISTBOX, editor._select_block)
    try:
        import wx.stc as stc

        editor.source.Bind(stc.EVT_STC_CHANGE, editor._source_changed)
        editor.source.Bind(stc.EVT_STC_UPDATEUI, editor._source_caret_changed)
    except Exception:
        editor.source.Bind(wx.EVT_TEXT, editor._source_changed)
    editor.search.Bind(wx.EVT_TEXT, lambda _event: editor._populate_library())
    editor.library.Bind(wx.EVT_LISTBOX, editor._select_command)
    editor.move_up.Bind(wx.EVT_BUTTON, lambda _event: editor._move(-1))
    editor.move_down.Bind(wx.EVT_BUTTON, lambda _event: editor._move(1))
    editor.duplicate.Bind(wx.EVT_BUTTON, lambda _event: editor._duplicate())
    editor.delete.Bind(wx.EVT_BUTTON, lambda _event: editor._delete())
    editor.mode_choice.Bind(
        wx.EVT_CHOICE,
        lambda _event: setattr(editor, "mode", ("solution", "meshing")[editor.mode_choice.GetSelection()]),
    )
    editor.language_choice.Bind(
        wx.EVT_CHOICE,
        lambda _event: setattr(editor, "language", ("tui", "scheme")[editor.language_choice.GetSelection()]),
    )
    editor._populate_library()
