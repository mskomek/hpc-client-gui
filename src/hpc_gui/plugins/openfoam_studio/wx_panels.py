"""Inspector / selector / diff / validation / results panel data + lazy wx builders.

(W65 UI-012, G33/G35.) Data functions are headless-testable and carry
TR/EN labels; wx builders import wx lazily and bind every control to a
callback or disable it with a tooltip. Diff data comes from
:mod:`patch_plan` previews; validation data from the lint engine; results
data from :mod:`post` + :mod:`plot_export` (MISSING, never zero).
"""

from __future__ import annotations

LABELS = {
    "inspector": {"en": "Inspector", "tr": "Denetçi"},
    "selector": {"en": "Configuration", "tr": "Yapılandırma"},
    "diff": {"en": "Source Diff", "tr": "Kaynak Farkı"},
    "validation": {"en": "Validation", "tr": "Doğrulama"},
    "results": {"en": "Results", "tr": "Sonuçlar"},
    "apply": {"en": "Apply (confirm)", "tr": "Uygula (onayla)"},
    "revert": {"en": "Revert", "tr": "Geri Al"},
    "refresh": {"en": "Refresh", "tr": "Yenile"},
    "no_handler": {"en": " (unavailable: no handler bound)",
                   "tr": " (kullanılamaz: işleyici bağlı değil)"},
    "nav_no_handler": {"en": "navigation unavailable: no handler bound",
                       "tr": "gezinme kullanılamaz: işleyici bağlı değil"},
    "missing_linter": {"en": "Linter unavailable; static checks only",
                       "tr": "Denetleyici yok; yalnızca statik denetim"},
}


def inspector_rows(tool: str, params: dict, lang: str = "en") -> list[dict]:
    """Typed inspector rows from the command schema (conditional fields kept)."""
    from hpc_gui.plugins.openfoam_studio.command_schemas import SCHEMAS
    if tool not in SCHEMAS:
        return [{"name": tool, "type": "raw", "required": False,
                 "detail": "RAW-ADVANCED: no typed inspector (safe raw view)"}]
    rows = []
    for decl in SCHEMAS[tool]["params"]:
        rows.append({"name": decl["name"], "type": decl["type"],
                     "required": bool(decl.get("required")),
                     "default": decl.get("default"), "units": decl.get("units"),
                     "choices": decl.get("choices"), "value": params.get(decl["name"]),
                     "lang": lang})
    return rows


def selector_state(edition: str = "OpenFOAM.com / ESI (OpenCFD)", version: str = "v2312",
                   solver: str = "simpleFoam", mode: str = "serial",
                   profile: str = "local") -> dict:
    from hpc_gui.plugins.openfoam_studio.selection import select
    sel = select(edition, version, solver, mode, profile)
    return {"edition": sel.edition, "version": sel.version, "solver": sel.solver,
            "mode": sel.mode, "profile": sel.profile,
            "unsupported_disabled": True}


def diff_rows(preview_text: str) -> list[dict]:
    rows = []
    current: dict | None = None
    for line in preview_text.splitlines():
        if line.startswith("--- verify-only") or line.startswith("--- no change"):
            rows.append({"kind": "info", "text": line})
            current = None
        elif line.startswith("--- ") or line.startswith("+++ ") or line.startswith("@@"):
            continue
        elif line.startswith("+") and not line.startswith("+++"):
            rows.append({"kind": "add", "text": line[1:]})
        elif line.startswith("-") and not line.startswith("---"):
            rows.append({"kind": "del", "text": line[1:]})
        else:
            rows.append({"kind": "ctx", "text": line[1:] if line.startswith(" ") else line})
    return rows


def validation_rows(diagnostics: list, lang: str = "en") -> list[dict]:
    header = LABELS["validation"][lang]
    return [{"header": header, "rule": getattr(d, "rule", d.get("rule") if isinstance(d, dict) else "?"),
             "severity": getattr(d, "severity", d.get("severity") if isinstance(d, dict) else "?"),
             "file": getattr(d, "file", d.get("file") if isinstance(d, dict) else "?"),
             "line": getattr(d, "line", d.get("line") if isinstance(d, dict) else 0),
             "message": getattr(d, "message", d.get("message") if isinstance(d, dict) else str(d))}
            for d in diagnostics]


def results_rows(time_dirs: list[str], postprocessing: list[str],
                 residual_series: dict | None = None, lang: str = "en") -> dict:
    from hpc_gui.plugins.openfoam_studio.post import result_status
    status = result_status(time_dirs, postprocessing)
    return {"header": LABELS["results"][lang], "status": status["status"],
            "detail": status.get("detail", ""),
            "series": sorted((residual_series or {}).keys()),
            "note": "MISSING means no result bytes; never plotted as zero"}


def _wire(parent, button, callback: object, tip: str, lang: str = "en"):
    import wx
    if callback is None:
        button.Disable()
        button.SetToolTip(f"{tip}{LABELS['no_handler'][lang]}")
    else:
        button.SetToolTip(tip)
        button.Bind(wx.EVT_BUTTON, lambda _e: callback())


def build_inspector_panel(parent, tool: str, params: dict, *,
                          on_apply=None, lang: str = "en"):
    import wx
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    for row in inspector_rows(tool, params, lang):
        text = wx.StaticText(panel, label=f"{row['name']} [{row['type']}]"
                             + (" *" if row.get("required") else ""))
        text.SetToolTip(str(row.get("default", "")) or row.get("detail", ""))
        sizer.Add(text, 0, wx.ALL, 2)
    apply_btn = wx.Button(panel, label=LABELS["apply"][lang])
    _wire(panel, apply_btn, on_apply, "apply typed params to patch plan", lang)
    sizer.Add(apply_btn, 0, wx.ALL, 4)
    panel.SetSizer(sizer)
    return panel


def build_diff_panel(parent, preview_text: str, *, on_revert=None, lang: str = "en"):
    import wx
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    view = wx.TextCtrl(panel, value=preview_text,
                       style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_DONTWRAP)
    sizer.Add(view, 1, wx.EXPAND | wx.ALL, 4)
    revert_btn = wx.Button(panel, label=LABELS["revert"][lang])
    _wire(panel, revert_btn, on_revert, "revert to pre-preview case bytes", lang)
    sizer.Add(revert_btn, 0, wx.ALL, 4)
    panel.SetSizer(sizer)
    return panel


def build_validation_panel(parent, diagnostics: list, *, linter_available: bool = True,
                            on_navigate=None, lang: str = "en"):
    import wx
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    if not linter_available:
        note = wx.StaticText(panel, label=LABELS["missing_linter"][lang])
        sizer.Add(note, 0, wx.ALL, 4)
    rows = validation_rows(diagnostics, lang)
    listing = wx.ListBox(panel, choices=[f"{r['severity']} {r['rule']} "
                                         f"{r['file']}:{r['line']}" for r in rows])
    if on_navigate is not None:
        listing.Bind(wx.EVT_LISTBOX,
                     lambda _e: on_navigate(listing.GetSelection()))
    else:
        listing.Disable()
        listing.SetToolTip(LABELS["nav_no_handler"][lang])
    sizer.Add(listing, 1, wx.EXPAND | wx.ALL, 4)
    panel.SetSizer(sizer)
    return panel


def build_results_panel(parent, time_dirs: list[str], postprocessing: list[str], *,
                        residual_series: dict | None = None, on_refresh=None,
                        lang: str = "en"):
    import wx
    panel = wx.Panel(parent)
    sizer = wx.BoxSizer(wx.VERTICAL)
    data = results_rows(time_dirs, postprocessing, residual_series, lang)
    status = wx.StaticText(panel, label=f"{data['header']}: {data['status']}")
    status.SetToolTip(data["detail"] or data["note"])
    sizer.Add(status, 0, wx.ALL, 4)
    refresh_btn = wx.Button(panel, label=LABELS["refresh"][lang])
    _wire(panel, refresh_btn, on_refresh, "rescan time dirs + postProcessing", lang)
    sizer.Add(refresh_btn, 0, wx.ALL, 4)
    panel.SetSizer(sizer)
    return panel
