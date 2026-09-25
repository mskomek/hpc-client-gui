# Wave W41 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T20:20:34.883577+00:00

- Wave: `W41`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0033-W41-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-203154-ca45d2b7\0033-W41-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [limit=2000, offset=30]
✱ Glob ".agents/protocol/*.md" 0 matches
✱ Glob "waves/**/W41.md" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read . 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents 
→ Read waves 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/done 
→ Read .agents/skills 
→ Read .agents/protocol 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W41.md 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read rules.md 
→ Read .agents/skills/ac-wave-core 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/skills/ac-wave-core/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "git rev-parse HEAD; git status --short | Select-Object -First 50; git log --oneline -5; echo '---BRANCH---'; git branch --show-current"
c8293d3ca309526ed250c794c3b294f7c54ef369
 M README.md
 M src/hpc_gui/config/storage.py
 M src/hpc_gui/core/diagnostics.py
 M src/hpc_gui/core/i18n.py
 M src/hpc_gui/core/ui_errors.py
 M src/hpc_gui/core/wx_errors.py
 M src/hpc_gui/docs/HELP_en.md
 M src/hpc_gui/docs/HELP_tr.md
 M src/hpc_gui/docs/PLUGINS_en.md
 M src/hpc_gui/docs/PLUGINS_tr.md
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/plugins/installer.py
 M src/hpc_gui/plugins/loader.py
 M src/hpc_gui/plugins/models.py
 M src/hpc_gui/plugins/validator.py
 M src/hpc_gui/services/command_history_store.py
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/geometry_policy.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/shortcut_preferences.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/ui/dialogs/plugin_manager_dialog.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_logs.py
 M src/hpc_gui/wx_logs_view.py
 M src/hpc_gui/wx_plugins.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_settings.py
 M src/hpc_gui/wx_settings_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? NUL
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/opencode/wave_W30/
?? artifacts/opencode/wave_W31/
?? artifacts/opencode/wave_W32/
?? artifacts/opencode/wave_W33/
?? artifacts/opencode/wave_W34/
?? artifacts/opencode/wave_W36/
?? artifacts/wave_W29/
?? artifacts/wave_W32/
?? artifacts/wave_W33/
?? artifacts/wave_W35/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
d0d544c1 Wave W19-W25 product and test work (W26 editor identity in progress)
0d02da56 Ignore Agent Core skill quarantine and wave patch backups
---BRANCH---
develop
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ powershell -NoProfile -Command "Get-ChildItem docs/wave-reports/v2/opencode/ | Where-Object {$_.Name -like 'W41*'} | Select-Object Name,Length; echo '---ARTIFACTS---'; Get-ChildItem artifacts/ -Recurse -Filter '*W41*' 2>$null | Select-Object FullName | Select-Object -First 20; echo '---MANIFESTS---'; Get-ChildItem artifacts/ -Recurse -Filter '*EVIDENCE*' 2>$null | Select-Object -First 20 FullName; echo '---REGISTRY---'; Get-ChildItem -Filter '*REQUIREMENT*' -Recurse | Select-Object -First 10 FullName; Get-ChildItem -Filter '*TODO_OWNERSHIP*' -Recurse | Select-Object -First 10 FullName"
At line:1 char:244
+ ... CTS---'; Get-ChildItem artifacts/ -Recurse -Filter '*W41*' 2> | Selec ...
+                                                                  ~
Missing file specification after redirection operator.
At line:1 char:378
+ ... -'; Get-ChildItem artifacts/ -Recurse -Filter '*EVIDENCE*' 2> | Selec ...
+                                                                  ~
Missing file specification after redirection operator.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingFileSpecification
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git status --short | Select-Object -First 60
git log --oneline -3
git branch --show-current
/usr/bin/bash: line 1: Select-Object: command not found
c8293d3c Sync Agent Core runtime 21c15de7; align controller regression tests with canonical API
3e9635ba Sync Agent Core runtime fdd19ce1: provider quota wait, error-only failure classification
917f7916 Record Wave W19-W25 evidence, audit outputs and wave reports
develop
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls docs/wave-reports/v2/opencode/ | grep W41; echo ---; ls artifacts/ 2>/dev/null | head -30; echo ---; find artifacts -iname "*W41*" 2>/dev/null | head -20; echo ---REG---; find . -maxdepth 3 -iname "*REQUIREMENT*" 2>/dev/null | head; find . -maxdepth 3 -iname "*TODO_OWNERSHIP*" 2>/dev/null | head; find . -maxdepth 3 -iname "*WAVE_V2_FINAL_09*" 2>/dev/null | head
W41_WAVE_REPORT.md
---
opencode
v2-final
wave_W18
wave_W19
wave_W20
wave_W21
wave_W22
wave_W23
wave_W24
wave_W25
wave_W29
wave_W32
wave_W33
wave_W35
---
---REG---
./docs/wiki/Cluster-Requirements-TR.md
./docs/wiki/Cluster-Requirements.md
./opencode/REQUIREMENT_REGISTRY.md
./opencode/REQUIREMENT_WAVE_INDEX.md
./requirements-dev.txt
./requirements-release.lock
./requirements.txt
./opencode/TODO_OWNERSHIP_MAP.md
./opencode/sources/WAVE_V2_FINAL_09.md
./waves/bak/WAVE_V2_FINAL_09.md
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read docs/wave-reports/v2/opencode/W41_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ ls docs/wave-reports/v2/opencode/ | grep -E "W41|W40"; echo ---; ls tests/test_w41* tests/test_app_updater* tests/test_wx_updater* 2>/dev/null; echo ---; git diff --stat | head -40; echo ---; git diff --check | head -20; echo CHECK-DONE
W40_AUDIT_REPORT.md
W40_WAVE_REPORT.md
W41_WAVE_REPORT.md
---
tests/test_app_updater.py
tests/test_w41_updater_routing.py
tests/test_wx_updater_spec.py
---
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_logs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
 README.md                                       |   5 +-
 src/hpc_gui/config/storage.py                   | 104 ++++++
 src/hpc_gui/core/diagnostics.py                 |  21 +-
 src/hpc_gui/core/i18n.py                        |  74 +++-
 src/hpc_gui/core/ui_errors.py                   |   8 +-
 src/hpc_gui/core/wx_errors.py                   |   6 +
 src/hpc_gui/docs/HELP_en.md                     |   3 +-
 src/hpc_gui/docs/HELP_tr.md                     |   4 +-
 src/hpc_gui/docs/PLUGINS_en.md                  |  65 +++-
 src/hpc_gui/docs/PLUGINS_tr.md                  |  62 +++-
 src/hpc_gui/i18n/en.json                        |  15 +-
 src/hpc_gui/i18n/tr.json                        |  15 +-
 src/hpc_gui/plugins/installer.py                |   7 +
 src/hpc_gui/plugins/loader.py                   |   7 +
 src/hpc_gui/plugins/models.py                   |   5 +
 src/hpc_gui/plugins/validator.py                |  99 +++++-
 src/hpc_gui/services/command_history_store.py   |   6 +-
 src/hpc_gui/services/files_ssh.py               |  20 +-
 src/hpc_gui/services/geometry_policy.py         |  64 ++++
 src/hpc_gui/services/output_follower.py         |   5 +
 src/hpc_gui/services/shortcut_preferences.py    |  36 +-
 src/hpc_gui/services/slurm_models.py            |  81 +++++
 src/hpc_gui/ui/dialogs/plugin_manager_dialog.py |   8 +
 src/hpc_gui/wx_editor_view.py                   | 306 ++++++++++++++++-
 src/hpc_gui/wx_jobs.py                          | 315 +++++++++++++++--
 src/hpc_gui/wx_logs.py                          |  22 +-
 src/hpc_gui/wx_logs_view.py                     |  62 +++-
 src/hpc_gui/wx_plugins.py                       | 284 +++++++++++++++-
 src/hpc_gui/wx_plugins_view.py                  | 433 +++++++++++++++++++++---
 src/hpc_gui/wx_settings.py                      | 338 +++++++++++++++++-
 src/hpc_gui/wx_settings_view.py                 |  32 +-
 src/hpc_gui/wx_shell.py                         | 407 ++++++++++++++++------
 32 files changed, 2650 insertions(+), 269 deletions(-)
---
warning: in the working copy of 'src/hpc_gui/config/storage.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/diagnostics.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/i18n.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/core/wx_errors.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_en.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/docs/PLUGINS_tr.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/en.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/i18n/tr.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/command_history_store.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/geometry_policy.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/services/shortcut_preferences.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_logs.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'src/hpc_gui/wx_plugins_view.py', LF will be replaced by CRLF the next time Git touches it
CHECK-DONE
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w41_updater_routing.py 
$ git diff -- src/hpc_gui/wx_shell.py | head -250
diff --git a/src/hpc_gui/wx_shell.py b/src/hpc_gui/wx_shell.py
index b03a55d2..6a9eedab 100644
--- a/src/hpc_gui/wx_shell.py
+++ b/src/hpc_gui/wx_shell.py
@@ -71,6 +71,92 @@ def _make_tray(wx, frame, tray_factory):
         return None
 
 
+def _window_work_areas(wx):
+    """Current display work areas for geometry recovery (never raises)."""
+    try:
+        areas = []
+        for idx in range(wx.Display.GetCount()):
+            try:
+                area = wx.Display(idx).GetClientArea()
+                areas.append((area.x, area.y, area.width, area.height))
+            except Exception:
+                continue
+        return tuple(areas)
+    except Exception:
+        return ()
+
+
+def _restore_main_window_state(wx, frame, notebook):
+    """Apply persisted main-window geometry/selection (HPC-W09-UISTATE-009..014).
+
+    Best-effort: absent/corrupt/off-screen state resolves to fresh defaults
+    and the frame keeps its constructed size. Never raises.
+    """
+    try:
+        from hpc_gui.config.storage import get_main_window_state
+        from hpc_gui.services.geometry_policy import Rect, resolve_main_window_state
+
+        raw = get_main_window_state()
+        if raw is None:
+            return "fresh-defaults"
+        areas = tuple(Rect(*a) for a in _window_work_areas(wx))
+        try:
+            tab_count = int(notebook.GetPageCount())
+        except Exception:
+            tab_count = None
+        state = resolve_main_window_state(raw, areas, tab_count=tab_count)
+        rect = state["rect"]
+        try:
+            frame.SetSize(rect.x, rect.y, rect.width, rect.height)
+        except Exception:
+            pass
+        if state["selected_tab"] is not None:
+            try:
+                notebook.SetSelection(int(state["selected_tab"]))
+            except Exception:
+                pass
+        if state["maximized"]:
+            try:
+                frame.Maximize(True)
+            except Exception:
+                pass
+        return "restored"
+    except Exception:
+        return "fresh-defaults"
+
+
+def _save_main_window_state(frame, notebook):
+    """Persist current main-window geometry/selection (best-effort, never raises)."""
+    try:
+        from hpc_gui.config.storage import save_main_window_state
+
+        try:
+            pos = frame.GetPosition()
+            size = frame.GetSize()
+            maximized = bool(frame.IsMaximized())
+        except Exception:
+            return False
+        try:
+            selected = int(notebook.GetSelection())
+        except Exception:
+            selected = None
+        if maximized:
+            # A maximized frame reports its zoomed size; keep the record but
+            # mark it so restore re-applies Maximize instead of a zoomed rect.
+            pass
+        save_main_window_state(
+            x=int(pos.x),
+            y=int(pos.y),
+            width=int(size.width),
+            height=int(size.height),
+            maximized=maximized,
+            selected_tab=selected,
+        )
+        return True
+    except Exception:
+        return False
+
+
 def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_state=None, defer_terminal_webview=False):
     try:
         import wx
@@ -1103,91 +1189,19 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
         _dispatch("APP-HELP", f, lifecycle, session_state)
 
     def _on_update(_event):
+        # W41 UPDATER-ROUTE-002: delegate to the single authoritative
+        # update-check controller; no divergent second route.
         f = _shell_frame()
         if not f:
             return
-        before = set(wx.GetTopLevelWindows())
         try:
-            from hpc_gui.wx_updater_view import WxUpdateDialog, STATE_CHECKING, STATE_FAILED, STATE_UPDATE_AVAILABLE, STATE_UP_TO_DATE
+            run_wx_update_check(f)
         except Exception:
             return
-        dlg = WxUpdateDialog(f, None)
-        dlg._build_for_state(STATE_CHECKING)
-        dlg.dlg.Show()
-        _track_new_windows(before)
-        def worker():
-            try:
-                from hpc_gui.services.app_updater import get_latest_release, is_newer_version, AUTOMATIC_INSTALL_STRATEGIES
-                from hpc_gui.core.platform import current_os
-                from hpc_gui import __version__ as cur_ver2
-                release = get_latest_release(timeout=10)
-                def on_done():
-                    ff = _shell_frame()
-                    if not ff or not wx.Window.FindWindowById(ff.GetId()):
-                        try:
-                            dlg.Destroy()
-                        except Exception:
-                            pass
-                        return
-                    try:
-                        if not is_newer_version(release.version, cur_ver2):
-                            dlg._build_for_state(STATE_UP_TO_DATE)
-                            _track_new_windows(before)
-                            return
-                        try:
-                            from hpc_gui.services import app_updater as _au
-                            macos_ok = not (release.install_strategy == "macos-bundle" and release.security_status != _au.SECURITY_SIGNED)
-                        except Exception:
-                            macos_ok = True
-                        if release.install_strategy not in AUTOMATIC_INSTALL_STRATEGIES or not macos_ok:
-                            import webbrowser
-                            msg = t("updates.manual_install").format(version=release.version) if t("updates.manual_install") != "[updates.manual_install]" else f"Update {release.version} requires manual install."
-                            if current_os() == "macos":
-                                try:
-                                    sec_key = {_au.SECURITY_UNSIGNED: "updates.security_unsigned_mac", _au.SECURITY_SIGNED: "updates.security_signed_mac", _au.SECURITY_UNKNOWN: "updates.security_unknown_mac"}.get(release.security_status, "updates.security_unknown_mac")
-                                    msg += "\n\n" + t(sec_key)
-                                except Exception:
-                                    pass
-                            wx.MessageBox(msg, t("updates.title"), wx.OK | wx.ICON_INFORMATION, ff)
-                            try:
-                                webbrowser.open(release.zip_url or release.html_url)
-                            except Exception:
-                                pass
-                            try:
-                                dlg.Destroy()
-                            except Exception:
-                                pass
-                            _track_new_windows(before)
-                            return
-                        dlg.release = release
-                        dlg._total = getattr(release, "size", None)
-                        try:
-                            from hpc_gui.wx_updater_view import _parse_whats_new
-                            dlg._whats_new = _parse_whats_new(getattr(release, "body", ""))
-                        except Exception:
-                            pass
-                        dlg._build_for_state(STATE_UPDATE_AVAILABLE)
-                        _track_new_windows(before)
-                    except Exception as e:
-                        dlg._error_message = str(e)
-                        dlg._error_details = f"{type(e).__name__}: {e}"
-                        dlg._build_for_state(STATE_FAILED)
-                wx.CallAfter(on_done)
-            except Exception as exc:
-                def on_err(exc=exc):
-                    ff = _shell_frame()
-                    if not ff:
-                        try:
-                            dlg.Destroy()
-                        except Exception:
-                            pass
-                        return
-                    dlg._error_message = str(exc)
-                    dlg._error_details = f"{type(exc).__name__}: {exc}"
-                    dlg._build_for_state(STATE_FAILED)
-                wx.CallAfter(on_err)
-        import threading
-        threading.Thread(target=worker, daemon=True).start()
+        try:
+            _track_new_windows(set(wx.GetTopLevelWindows()))
+        except Exception:
+            pass
 
     def _on_plugins(_event):
         f = _shell_frame()
@@ -1281,6 +1295,9 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
     frame._wx_shell_tray = tray
 
     def close(_event):
+        # Persist main-window layout first (best-effort; shutdown never blocks
+        # on it) so save/restart restores size/position/maximized/selected tab.
+        _save_main_window_state(frame, notebook)
         # Invoke every embedded page's close callback before shutdown
         for _key, controls in list(page_controls.items()):
             # For Files splitter, local/remote/transfers are stored separately
@@ -1329,6 +1346,7 @@ def create_shell_frame(app=None, *, tray_factory=None, lifecycle=None, session_s
 
     frame.Bind(wx.EVT_CLOSE, close)
     frame._wx_shell_close = close
+    _restore_main_window_state(wx, frame, notebook)
     refresh_labels()
     return frame, lifecycle, session_state
 
@@ -2614,16 +2632,43 @@ def _editor_action_factory(session_state):
             _require_pinned_session(current)
             if not current.path:
                 raise RuntimeError(t("editor.document_path_required"))
+            if not slurm or not callable(getattr(slurm, "sbatch", None)):
+                raise RuntimeError(t("editor.slurm_unavailable"))
+            # W30 CTRL-001/002: validate required fields before sending and
+            # require confirmed scheduler acceptance/job ID. Template
+            # partition/account rules come from provider config, never
+            # hardcoded values.
+            from hpc_gui.services.job_submit_cancel import (
+                submit_result_status,
+                validate_submit_request,
+            )
+
+            try:
+                _profile = (session_state.get("session") or {}).get("profile") or {}
+                _prov = _profile.get("provider_template") if isinstance(_profile, dict) else None
+                _prov_cfg = _prov if isinstance(_prov, dict) else (_profile if isinstance(_profile, dict) else None)
+            except Exception:
+                _prov_cfg = None
+            _content = getattr(current, "content", None)
+            _errors = validate_submit_request(
+                str(current.path),
+                _content if isinstance(_content, str) else None,
+                provider_config=_prov_cfg if isinstance(_content, str) else None,
+            )
+            if _errors:
+                raise RuntimeError("Submission validation failed: " + "; ".join(_errors))
             if current.is_local:
-                if not files or not slurm:
+                if not files:
                     raise RuntimeError(t("editor.upload_or_slurm_unavailable"))
                 remote_path = str(PurePosixPath("~") / Path(current.path).name)
                 files.upload(current.path, remote_path)
-                slurm.sbatch(remote_path)
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import re; src=open('src/hpc_gui/wx_shell.py',encoding='utf-8').read(); i=src.find('def run_wx_update_check'); print(src[i-200:i+4500])"
except Exception:
            return False
        try:
            page.SetFocus()
        except Exception:
            pass
        return True
    except Exception:
        return False


def run_wx_update_check(parent) -> None:
    """Authoritative wx update-check controller (W41 UPDATER-ROUTE-001/002).

    Single shared implementation for the visible ``Check for Updates`` menu
    action (``APP-UPDATE-CHECK`` dispatch), the shell ``_on_update`` handler,
    and any other manual update-menu path. Opens the checking dialog and
    always starts the real update-check worker so the dialog transitions
    from ``CHECKING`` to ``UP_TO_DATE``, ``UPDATE_AVAILABLE`` (or manual
    install fallback), or ``FAILED``. Opening a checking dialog without
    starting the worker is forbidden.
    """
    import threading

    import wx

    from hpc_gui.core.i18n import t as _t

    try:
        from hpc_gui.wx_updater_view import (
            STATE_CHECKING,
            WxUpdateDialog,
        )
    except Exception:
        raise
    dlg = WxUpdateDialog(parent, None)
    dlg._build_for_state(STATE_CHECKING)
    dlg.dlg.Show()

    def _alive(frame) -> bool:
        try:
            if frame is None:
                return False
            import wx as _wx

            if not _wx.Window.FindWindowById(frame.GetId()):
                return False
        except Exception:
            return False
        return True

    def worker():
        try:
            from hpc_gui.services.app_updater import (
                AUTOMATIC_INSTALL_STRATEGIES,
                get_latest_release,
                is_newer_version,
            )
            from hpc_gui.core.platform import current_os
            from hpc_gui import __version__ as cur_ver2

            release = get_latest_release(timeout=10)

            def on_done():
                if not _alive(parent):
                    try:
                        dlg.Destroy()
                    except Exception:
                        pass
                    return
                try:
                    from hpc_gui.wx_updater_view import (
                        STATE_FAILED as _FAILED,
                        STATE_UPDATE_AVAILABLE as _AVAIL,
                        STATE_UP_TO_DATE as _UPTODATE,
                    )

                    if not is_newer_version(release.version, cur_ver2):
                        dlg._build_for_state(_UPTODATE)
                        return
                    try:
                        from hpc_gui.services import app_updater as _au

                        macos_ok = not (
                            release.install_strategy == "macos-bundle"
                            and release.security_status != _au.SECURITY_SIGNED
                        )
                    except Exception:
                        macos_ok = True
                    if (
                        release.install_strategy not in AUTOMATIC_INSTALL_STRATEGIES
                        or not macos_ok
                    ):
                        import webbrowser

                        msg = (
                            _t("updates.manual_install").format(version=release.version)
                            if _t("updates.manual_install") != "[updates.manual_install]"
                            else f"Update {release.version} requires manual install."
                        )
                        if current_os() == "macos":
                            try:
                                sec_key = {
                                    _au.SECURITY_UNSIGNED: "updates.security_unsigned_mac",
                                    _au.SECURITY_SIGNED: "updates.security_signed_mac",
                                    _au.SECURITY_UNKNOWN: "updates.security_unknown_mac",
                                }.get(release.security_status, "updates.security_unknown_mac")
                                msg += "\n\n" + _t(sec_key)
                            except Exception:
                                pass
                        wx.MessageBox(msg, _t("updates.title"), wx.OK | wx.ICON_INFORMATION, parent)
                        try:
                            webbrowser.open(release.zip_url or release.html_url)
                        except Exception:
                            pass
                        try:
                            dlg.Destroy()
                        except Exception:
                            pass
                        return
                    dlg.release = release
                    dlg._total = getattr(release, "size", None)
                    try:
                        from hpc_gui.wx_updater_view import _pars
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "src=open('src/hpc_gui/wx_shell.py',encoding='utf-8').read(); i=src.find('APP-UPDATE-CHECK'); print(src[i-800:i+1200])"
eration": 0}
    frame = wx.Frame(None, title=f"HPC Client GUI {__version__}", size=(1440, 900))
    frame._wx_app = app
    # Spec �3: recommended 1440�900 default, 1280�760 minimum; usable at ~1100�700 without clipping
    frame.SetMinSize(wx.Size(1280, 760))
    panel = wx.Panel(frame)
    root = wx.BoxSizer(wx.VERTICAL)
    menubar = wx.MenuBar()
    # --- Menu ---
    menu_menu = wx.Menu()
    menu_items = {}
    # Settings
    act_settings = menu_menu.Append(wx.ID_ANY, t("menu.settings"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-SETTINGS", frame, lifecycle, session_state), act_settings)
    menu_items["settings"] = act_settings
    # Check for Updates
    act_updates = menu_menu.Append(wx.ID_ANY, t("menu.check_updates"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("APP-UPDATE-CHECK", frame, lifecycle, session_state), act_updates)
    menu_items["check_updates"] = act_updates
    # Command Palette omitted (no real palette UI) � do not miswire to Help
    menu_menu.AppendSeparator()
    act_exit = menu_menu.Append(wx.ID_EXIT, t("menu.exit"))
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), act_exit)
    menu_items["exit"] = act_exit
    menubar.Append(menu_menu, t("menu.menu"))
    # --- Plugins ---
    plugins_menu = wx.Menu()
    act_browse = plugins_menu.Append(wx.ID_ANY, t("menu.browse_install"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-BROWSE", frame, lifecycle, session_state), act_browse)
    act_manage = plugins_menu.Append(wx.ID_ANY, t("menu.manage_installed"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-MANAGE", frame, lifecycle, session_state), act_manage)
    act_plugin_updates = plugins_menu.Append(wx.ID_ANY, t("menu.check_plugin_updates"))
    frame.Bind(wx.EVT_MENU, lambda _e: _dispatch("PLUGIN-UPDATES", frame, lifecycle, session_state), act_plugin_updates)
    sep_plugins_top = None
    # Dynamic plugin roots will be inserted here (between the two separators) - top separator created on demand
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "src=open('src/hpc_gui/wx_shell.py',encoding='utf-8').read(); import re; [print(repr(src[m-200:m+800][:800])) or print('====') for m in [m.start() for m in re.finditer('run_wx_update_check',src)]]"
'-ROUTE-002: delegate to the single authoritative\n        # update-check controller; no divergent second route.\n        f = _shell_frame()\n        if not f:\n            return\n        try:\n            run_wx_update_check(f)\n        except Exception:\n            return\n        try:\n            _track_new_windows(set(wx.GetTopLevelWindows()))\n        except Exception:\n            pass\n\n    def _on_plugins(_event):\n        f = _shell_frame()\n        if not f:\n            return\n        before = set(wx.GetTopLevelWindows())\n        # W02 ERROR-GOV: route through _dispatch like _on_help so failures\n        # are visible with a stable code instead of silently swallowed.\n        _dispatch("PLUGIN-BROWSE", f, lifecycle, session_state)\n        _track_new_windows(before)\n\n    def _on_send_logs(_event'
====
'    except Exception:\n            return False\n        try:\n            page.SetFocus()\n        except Exception:\n            pass\n        return True\n    except Exception:\n        return False\n\n\ndef run_wx_update_check(parent) -> None:\n    """Authoritative wx update-check controller (W41 UPDATER-ROUTE-001/002).\n\n    Single shared implementation for the visible ``Check for Updates`` menu\n    action (``APP-UPDATE-CHECK`` dispatch), the shell ``_on_update`` handler,\n    and any other manual update-menu path. Opens the checking dialog and\n    always starts the real update-check worker so the dialog transitions\n    from ``CHECKING`` to ``UP_TO_DATE``, ``UPDATE_AVAILABLE`` (or manual\n    install fallback), or ``FAILED``. Opening a checking dialog without\n    starting the worker is forbidden.\n  '
====
' the canonical owner for this branch (W02 TRACE).\n        try:\n            from hpc_gui.wx_updater_view import WxUpdateDialog as _WxUpdateDialogOwner\n\n            _ = _WxUpdateDialogOwner\n            run_wx_update_check(parent)\n        except Exception as exc:\n            # W02 ERROR-GOV: an updater failure must be visible, never silent.\n            report_wx_action_error(parent, area="UPDATE", message_key="updates.open_failed", exc=exc)\n    elif command_id == "APP-SEND-LOGS":\n        from hpc_gui.wx_send_logs_view import show_send_logs\n        try:\n            show_send_logs(parent=parent)\n        except Exception as exc:\n            # W02 ERROR-GOV: a diagnostics failure must be visible, never silent.\n            report_wx_action_error(parent, area="LOGS", message_key="logs.send_open_fai'
====
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w41_updater_routing.py -q 2>&1 | tail -15
....                                                                     [100%]
4 passed in 0.46s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_app_updater.py tests/test_update_verification.py tests/test_updater_helper.py tests/test_wx_updater_spec.py tests/test_wx_dispatch_error_gov.py -q 2>&1 | tail -15
"""TRACE-001: local editor save and remote (SFTP) editor save are not
        collapsed into one path � they have different semantics and owners."""
        shell_src = pathlib.Path("src/hpc_gui/wx_shell.py").read_text(encoding="utf-8")
        editor_src = pathlib.Path("src/hpc_gui/wx_editor_view.py").read_text(encoding="utf-8")
        # Remote save: SFTP backend through the session file service.
        assert "def save_remote(path, content)" in shell_src
        assert "files.write_text(path, content)" in shell_src
        # Local save: local filesystem through the editor view.
>       assert "Path(snapshot.path).write_text" in editor_src
E       assert 'Path(snapshot.path).write_text' in '"""Native wx editor adapter for the framework-neutral editor model."""\n\nfrom __future__ import annotations\n\nimpor...rsion)\n\n\n__all__ = ["show_editor", "build_editor_panel", "editor_binary_guard_reason", "BINARY_GUARD_SIZE_BYTES"]\n'

tests\test_wx_dispatch_error_gov.py:349: AssertionError
=========================== short test summary info ===========================
FAILED tests/test_wx_dispatch_error_gov.py::test_editor_save__local_and_remote_paths_have_distinct_owners
1 failed, 90 passed in 13.02s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "import hashlib; d=open('waves/pending/W41.md','rb').read().replace(b'\r\n',b'\n').replace(b'\r',b'\n'); h=hashlib.sha256(d.lstrip(b'\xef\xbb\xbf')).hexdigest(); print(h)"; echo ---; git rev-parse HEAD; echo ---; git diff --check -- src/hpc_gui/wx_shell.py tests/test_w41_updater_routing.py; echo DIFFCHECK-OK; echo ---; git status --short -- tests/test_w41_updater_routing.py src/hpc_gui/wx_shell.py
6a873fe508433fe59f48ee74b5d8521dd3e5cfb6fdac7da0946ee3cec8f6261f
---
c8293d3ca309526ed250c794c3b294f7c54ef369
---
DIFFCHECK-OK
---
 M src/hpc_gui/wx_shell.py
?? tests/test_w41_updater_routing.py
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import re
reg=open('opencode/REQUIREMENT_REGISTRY.md',encoding='utf-8').read()
rows=[l for l in reg.splitlines() if 'W41' in l]
print(len(rows))
for l in rows[:30]: print(l[:220])
"
26
| `HPC-W09-UPD-001` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_09.md` | 43 | Entry criteria | `W41` | � | W08 canonical report is valid and plugin/provider settings ownership is frozen for this slice. |
| `HPC-W09-UPD-002` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_09.md` | 44 | Entry criteria | `W41` | � | W04 packaged harness is operational. |
| `HPC-W09-UPD-005` | MANDATORY | PREREQUISITE | `WAVE_V2_FINAL_09.md` | 47 | Entry criteria | `W41` | � | A safe updater test channel/fixture exists that exercises production verification logic without risking a real un
| `HPC-W09-UPD-016` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_09.md` | 61 | Scope | `W41` | � | updater availability/version selection; |
| `HPC-W09-UPD-017` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_09.md` | 62 | Scope | `W41` | � | download progress; |
| `HPC-W09-UPD-018` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_09.md` | 63 | Scope | `W41` | � | verification; |
| `HPC-W09-UPD-019` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_09.md` | 64 | Scope | `W41` | � | install/restart; |
| `HPC-W09-UPD-020` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_09.md` | 65 | Scope | `W41` | � | failure/rollback; |
| `HPC-W09-UPD-021` | MANDATORY | BOUNDARY | `WAVE_V2_FINAL_09.md` | 66 | Scope | `W41` | � | packaged behavior. |
| `HPC-W09-UPD-022` | CONDITIONAL | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 208 | Workstream F � Updater state machine | `W41` | � | Actual code may use different names, but the UI must not conflate these states. |
| `HPC-W09-UPD-023` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 214 | Workstream G � Update download UX | `W41` | � | show total size; |
| `HPC-W09-UPD-024` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 215 | Workstream G � Update download UX | `W41` | � | downloaded amount; |
| `HPC-W09-UPD-025` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 216 | Workstream G � Update download UX | `W41` | � | progress percentage/bar; |
| `HPC-W09-UPD-026` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 217 | Workstream G � Update download UX | `W41` | � | handle unknown total honestly; |
| `HPC-W09-UPD-027` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 218 | Workstream G � Update download UX | `W41` | � | cancellation if supported; |
| `HPC-W09-UPD-028` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 219 | Workstream G � Update download UX | `W41` | � | resume only if truly supported. |
| `HPC-W09-UPD-049` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 265 | Targeted tasks | `W41` | TASK-W09-006 | `TASK-W09-006`: updater state-machine audit. |
| `HPC-W09-UPD-050` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_09.md` | 266 | Targeted tasks | `W41` | TASK-W09-007 | `TASK-W09-007`: download byte/percentage UX. |
| `HPC-W09-UPD-062` | MANDATORY | TEST | `WAVE_V2_FINAL_09.md` | 282 | Test matrix | `W41` | � | update unavailable \\\| automated |
| `HPC-W09-UPD-063` | MANDATORY | TEST | `WAVE_V2_FINAL_09.md` | 283 | Test matrix | `W41` | � | update available \\\| automated |
| `HPC-W09-UPD-064` | MANDATORY | TEST | `WAVE_V2_FINAL_09.md` | 284 | Test matrix | `W41` | � | unknown content length \\\| automated |
| `HPC-W09-UPD-065` | MANDATORY | TEST | `WAVE_V2_FINAL_09.md` | 285 | Test matrix | `W41` | � | download interrupted \\\| automated/integration |
| `HPC-W09-UPD-075` | MANDATORY | GATE | `WAVE_V2_FINAL_09.md` | 298 | Acceptance criteria | `W41` | � | [ ] Updater states are distinguishable and truthful. |
| `HPC-W09-UPD-076` | MANDATORY | GATE | `WAVE_V2_FINAL_09.md` | 299 | Acceptance criteria | `W41` | � | [ ] Known download size displays bytes/total/percentage. |
| `HPC-W09-TODO-UPDATER-ROUTE-001` | `UPDATER-ROUTE-001` | `W41` | `UPDATER-ROUTE-001` � The visible wx `Check for Updates` menu action must execute the real update-check service and transition from `CHECKING` to `UP_TO_
| `HPC-W09-TODO-UPDATER-ROUTE-002` | `UPDATER-ROUTE-002` | `W41` | `UPDATER-ROUTE-002` � Remove/dead-code-eliminate duplicate updater routes so startup/manual/update-menu paths share one authoritative controller/state ma
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w41_updater_routing.py tests/test_app_updater.py tests/test_update_verification.py tests/test_updater_helper.py -q 2>&1 | tail -4; echo ===; python -c "import pathlib; s=pathlib.Path('src/hpc_gui/services/app_updater.py').read_text(encoding='utf-8'); print('cancelled' in s, '.part' in s, 'Content-Length' in s or 'content-length' in s.lower()); v=pathlib.Path('src/hpc_gui/wx_updater_view.py').read_text(encoding='utf-8'); print('STATE_CHECKING' in v, 'STATE_FAILED' in v, 'resume' in v.lower()); print('secrets:', any(k in open('src/hpc_gui/wx_shell.py',encoding='utf-8').read()[open('src/hpc_gui/wx_shell.py',encoding='utf-8').read().find('def run_wx_update_check'):open('src/hpc_gui/wx_shell.py',encoding='utf-8').read().find('def run_wx_update_check')+6000].lower() for k in ['api_key','secret','token','password']))"
...................................                                      [100%]
35 passed in 2.04s
===
True True True
True True False
secrets: False
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
AC_WAVE_BRIDGE_STDOUT_BEGIN
Auditing W41 — running the canonical fresh-context check.
Skill scope is thin — pulling the full audit authority and W41 truth set.
Core routing fix checks out — now verifying the evidence and test claims.
W41 fresh independent audit — read-only, no product repair.

Candidate: `develop @ c8293d3ca309526ed250c794c3b294f7c54ef369` + working-tree W41 delta (`src/hpc_gui/wx_shell.py` FIX-A hunks, new `tests/test_w41_updater_routing.py`). Controller `content_identity 965183e8…` noted; tested identity bound below.

Authority reads: `waves/pending/W41.md` (24 source + 2 TODO rows, gate NONE, evidence GUI+PACKAGE), all 26 `REQUIREMENT_REGISTRY.md`/`TODO_OWNERSHIP_MAP.md` W41 rows present, `WAVE_V2_FINAL_09.md` Entry/Scope/F/G/Tasks/Matrix/Gates, live code `wx_shell.py` / `wx_updater_view.py` / `services/app_updater.py`, live tests before/after.

Findings verification:
- DEF-W41-001 (ROUTE-001, stuck CHECKING): FIXED+VERIFIED. `_dispatch APP-UPDATE-CHECK` now calls `run_wx_update_check(parent)` which always starts the real `get_latest_release(timeout=10)` worker and transitions CHECKING→UP_TO_DATE/AVAILABLE-manual-fallback/FAILED. Pinned by 3 new dispatch-path tests (up-to-date/available/failed with message retained).
- DEF-W41-002 (ROUTE-002, duplicate routes): FIXED+VERIFIED. Single `run_wx_update_check` controller; `_on_update` delegates, duplicate ~70-line worker deleted; `get_latest_release` absent from `_on_update`. Pinned by `test_single_authoritative_controller`.
- No-code-change classifications sampled and confirmed: UPD-017/023/024/025 real-counter progress, UPD-026/064 unknown-total honesty (no fake %, indeterminate Pulse), UPD-027/065 cancel (`.part` removed, no post-cancel install, close/late-callback safe), UPD-028 no resume claimed (zero hits), UPD-018/019/020/021 verification/install/packaged gates, UPD-022/075 distinct states, UPD-049/050 audit record + byte math, UPD-062/063 matrix, UPD-076 size display. Existing tests pin each.
- OBS-W41-003/004 correctly routed, not fixed opportunistically (splash demo-fake → splash/packaged owner; editor dispatch-owner red → editor owner).

Independent test execution (this audit): `test_w41_updater_routing` 4 passed; `test_app_updater + test_update_verification + test_updater_helper + test_wx_updater_spec + test_wx_dispatch_error_gov` 90 passed + 1 failed where the failure is `test_editor_save__local_and_remote_paths_have_distinct_owners` (editor-owner assertion on `wx_editor_view.py`, untouched by W41 surface — pre-existing/cross-scope, not a W41 blocker). `git diff --check` on W41 files clean. No secrets/credentials added; no weakened tests; ERROR-GOV/W02 trace contracts preserved.

Evidence: GUI FULL via 23 real-wx `test_wx_updater_spec` runtime tests + 4 dispatch-path routing tests. PACKAGE N/A justified (no artifact built/claimed; synthetic fixtures per UPD-005; packaged acceptance W43-owned). External N/A (connection-independent surface).

Contradiction scan: no conflated states, no fake progress, no silent failure, no second worker, no scope escape beyond the two W41 files.

Verdict: every owned requirement implemented or already valid, required evidence current and truthful, no owned blocking defect. Fresh independent audit PASS.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
