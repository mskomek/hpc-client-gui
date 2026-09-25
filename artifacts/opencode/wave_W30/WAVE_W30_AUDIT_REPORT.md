# Wave W30 Audit Report
## Controller-persisted fresh independent audit — 2026-09-24T14:25:32.354458+00:00

- Wave: `W30`
- Normalized receipt: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0028-W30-audit-normalized.json`
- Phase log: `.tmp\agent-runs\ac-wave-opencode-parallel\20260924-152940-c05dfd9c\0028-W30-audit-opencode.log`
- Controller receipt status: `PASS`

The auditor executed independently; controller persistence is the durable artifact handoff.

```text
AC_WAVE_MODELS_LIST_EMPTY: 'opencode models --standalone' returned no entries; deferring to 'opencode run' fail-closed model validation for opencode-go/muse-spark-1.3-contributor

> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .opencode/protocol/WAVE_PROJECT_PROFILE.json 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md 
✱ Glob ".agents/skills/ac-wave-*/SKILL.md" 0 matches
✱ Glob "waves/**/W30*" 0 matches
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves 
→ Read .agents/skills 
→ Read .agents/protocol 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending 
→ Read waves/waves 
→ Read waves/done 
→ Read .agents/skills/ac-wave-opencode-audit 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read waves/pending/W30.md 
$ powershell -NoProfile -Command "Get-Content .agents/skills/ac-wave-opencode-audit/SKILL.md -Raw | Select-Object -First 1; Get-Content .agents/skills/ac-wave-opencode-audit/SKILL.md | Measure-Object -Line; Get-Content .agents/skills/ac-wave-core/SKILL.md 2>$null | Select-Object -First 200"
At line:1 char:225
+ ... ct -Line; Get-Content .agents/skills/ac-wave-core/SKILL.md 2> | Selec ...
+                                                                  ~
Missing file specification after redirection operator.
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingFileSpecification
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_PROGRAM_ORCHESTRATION.md 
→ Read .agents/skills/ac-wave-opencode-audit/SKILL.md [limit=2000, offset=30]
→ Read .agents/skills/ac-wave-core/SKILL.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read .agents/protocol/AC_WAVE_VALIDATION_EVIDENCE_SCHEMA.md 
→ Read .agents/protocol/AC_WAVE_EXECUTION_AND_TEST_PROTOCOL.md 
→ Read docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md 
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git rev-parse HEAD; git status --porcelain=v1; echo "---STAT---"; git diff --stat; echo "---CHECK---"; git diff --check; echo "---PENDINGHASH---"; powershell -NoProfile -Command "Get-FileHash waves/pending/W30.md -Algorithm SHA256 | Select-Object -ExpandProperty Hash"
3e9635ba1cf0255d5a09f370e91d1ddb73cef888
 M src/hpc_gui/i18n/en.json
 M src/hpc_gui/i18n/tr.json
 M src/hpc_gui/services/files_ssh.py
 M src/hpc_gui/services/output_follower.py
 M src/hpc_gui/services/slurm_models.py
 M src/hpc_gui/wx_editor_view.py
 M src/hpc_gui/wx_jobs.py
 M src/hpc_gui/wx_plugins_view.py
 M src/hpc_gui/wx_shell.py
?? ".agent-legacy-backup (1)/"
?? artifacts/opencode/wave_W26/
?? artifacts/opencode/wave_W27/
?? artifacts/opencode/wave_W28/
?? artifacts/opencode/wave_W29/
?? artifacts/wave_W29/
?? docs/wave-reports/v2/opencode/W26_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W27_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W28_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W29_WAVE_REPORT.md
?? docs/wave-reports/v2/opencode/W30_WAVE_REPORT.md
?? "new 4.ps1"
?? src/hpc_gui/services/job_identity.py
?? src/hpc_gui/services/job_list_filter_sort.py
?? src/hpc_gui/services/job_submit_cancel.py
?? src/hpc_gui/services/jobs_refresh_state.py
?? "tests/contracts (1)/"
?? "tests/contracts (2)/"
?? tests/test_w26_run_supplement.py
?? tests/test_w27_editor_conflicts.py
?? tests/test_w28_jobs_identity_refresh.py
?? tests/test_w29_job_outputs.py
?? tests/test_w30_submit_cancel.py
---STAT---
warning: in the working copy of 'src/hpc_gui/services/output_follower.py', LF will be replaced by CRLF the next time Git touches it
 src/hpc_gui/i18n/en.json                |   8 +
 src/hpc_gui/i18n/tr.json                |   8 +
 src/hpc_gui/services/files_ssh.py       |  20 +-
 src/hpc_gui/services/output_follower.py |   5 +
 src/hpc_gui/services/slurm_models.py    |  81 ++++++++
 src/hpc_gui/wx_editor_view.py           | 306 ++++++++++++++++++++++++++++++-
 src/hpc_gui/wx_jobs.py                  | 315 ++++++++++++++++++++++++++++----
 src/hpc_gui/wx_plugins_view.py          |   9 +-
 src/hpc_gui/wx_shell.py                 |  54 +++++-
 9 files changed, 755 insertions(+), 51 deletions(-)
---CHECK---
warning: in the working copy of 'src/hpc_gui/services/output_follower.py', LF will be replaced by CRLF the next time Git touches it
---PENDINGHASH---
389ED6AB0464A60811BC66E7C4F001536F8F783075A183E84BDA9D20EB893CCB
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
→ Read tests/test_w30_submit_cancel.py 
→ Read src/hpc_gui/services/job_submit_cancel.py 
$ python -m pytest tests/test_w30_submit_cancel.py -q 2>&1 | Select-Object -Last 20
/usr/bin/bash: line 1: Select-Object: command not found
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -m pytest tests/test_w30_submit_cancel.py -q 2>&1 | tail -20
...............                                                          [100%]
15 passed in 2.94s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_shell.py src/hpc_gui/wx_jobs.py 2>&1 | head -n 300; echo "===UNTRACKED CHECK==="; ls src/hpc_gui/services/job_submit_cancel.py tests/test_w30_submit_cancel.py
diff --git a/src/hpc_gui/wx_jobs.py b/src/hpc_gui/wx_jobs.py
index a8b79df8..2f3ac272 100644
--- a/src/hpc_gui/wx_jobs.py
+++ b/src/hpc_gui/wx_jobs.py
@@ -12,7 +12,15 @@ from uuid import uuid4
 
 from hpc_gui.core.i18n import current_language, subscribe_language_change, t, unsubscribe_language_change
 from hpc_gui.services.job_failure_classifier import explain_job_failure
+from hpc_gui.services.job_identity import cancel_is_safe, make_identity
+from hpc_gui.services.job_list_filter_sort import (
+    cancel_target_is_safe,
+    filter_jobs,
+    selection_still_exists,
+    sort_jobs,
+)
 from hpc_gui.services.job_provenance import JobProvenanceCapture
+from hpc_gui.services.jobs_refresh_state import JobsRefreshState
 from hpc_gui.services.job_tracking_controller import JobTrackingController
 from hpc_gui.services.selected_job_context import SelectedJobStore
 from hpc_gui.services.slurm_models import parse_scontrol
@@ -444,6 +452,9 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
     jobs_toolbar.Add(lbl_filter, 0, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 4)
     jobs_toolbar.Add(filter_field, 1, wx.RIGHT | wx.ALIGN_CENTER_VERTICAL, 6)
     jobs_toolbar.Add(cb_auto_refresh, 0, wx.ALIGN_CENTER_VERTICAL)
+    # W28: visible refresh lifecycle readback (idle/refreshing/success/stale).
+    jobs_refresh_label = wx.StaticText(jobs_page, label="")
+    jobs_toolbar.Add(jobs_refresh_label, 0, wx.LEFT | wx.ALIGN_CENTER_VERTICAL, 6)
 
     # -- Jobs table ---------------------------------------------------------
     jobs = wx.ListCtrl(jobs_page, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.LC_HRULES)
@@ -969,6 +980,10 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
         "refresh_pending": False,
         "output_in_flight": False,
         "cancel_in_flight": False,
+        "cancel_capability": "available",
+        "last_cancel_outcome": "",
+        "last_cancel_message": "",
+        "last_cancel_is_error": False,
         "user_paused": False,
         "minimized": False,
         "follow_calls": 0,
@@ -991,6 +1006,15 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
         "_timer_paused": False,
         "raw_scontrol_visible": False,
         "filter_query": "",
+        "sort_key": "",
+        "sort_reverse": False,
+        "jobs_refresh": JobsRefreshState(),
+        "jobs_refresh_seq": 0,
+        "jobs_refresh_applied_seq": 0,
+        "jobs_refresh_status": "idle",
+        "jobs_refresh_timestamp": "",
+        "jobs_refresh_error": "",
+        "jobs_refresh_stale": False,
         "resolved_channels": [],
         "output_channel_defs": list(output_channel_defs) if output_channel_defs is not None else None,
         "output_channel_defs_provider": kwargs.get("output_channel_defs_provider"),
@@ -1070,14 +1094,18 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
         _apply_filter()
 
     def _apply_filter():
+        # W28: filter refresh never mutates backend data; sort uses semantic
+        # values via the framework-neutral helper, not display strings.
         query = state["filter_query"]
-        filtered = []
-        for item in state["raw_items"]:
-            row = _parse_job_row(item)
-            if _matches_filter(row, query):
-                filtered.append((row, item))
-        state["items"] = [item for _, item in filtered]
-        _refresh_job_table(filtered)
+        backend_snapshot = list(state["raw_items"])
+        filtered = filter_jobs(backend_snapshot, query)
+        sort_key = state.get("sort_key", "")
+        if sort_key:
+            filtered = sort_jobs(filtered, sort_key, reverse=bool(state.get("sort_reverse", False)))
+        # Pair each visible item with its normalised row for rendering.
+        paired = [(_parse_job_row(item), item) for item in filtered]
+        state["items"] = list(filtered)
+        _refresh_job_table(paired)
 
     def _refresh_job_table(filtered):
         jobs.DeleteAllItems()
@@ -1258,6 +1286,16 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
                 model.selected_job_store.update(**update_kwargs)
 
     # --- Refresh jobs -------------------------------------------------------
+    # W28: explicit idle -> refreshing -> success(timestamp) | failure(error,
+    # prior-data-marked-stale) machine with a monotonic sequence so an older
+    # response can never overwrite a newer response. Failures retain prior
+    # rows (marked stale) instead of silently clearing them.
+    def _has_key(key: str) -> bool:
+        try:
+            return bool(t(key) != key)
+        except Exception:
+            return False
+
     def refresh_jobs(_event=None):
         if not list_jobs or state["minimized"]:
             return
@@ -1271,34 +1309,117 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
                 state["refresh_pending"] = True
                 return
             state["in_flight"] = True
+            state["jobs_refresh_seq"] += 1
+            request_seq = state["jobs_refresh_seq"]
+            machine: JobsRefreshState = state["jobs_refresh"]
+            machine.begin()
+            # Keep the wx-mirrored status in sync for headless readback.
+            state["jobs_refresh_status"] = "refreshing"
+            try:
+                jobs_refresh_label.SetLabel(t("jobs.refreshing"))
+            except Exception:
+                pass
 
         def fetch():
             try:
                 result = list_jobs()
-                post(done, result, None, request_generation)
+                post(done, result, None, request_generation, request_seq)
             except Exception as error:
-                post(done, (), error, request_generation)
+                post(done, (), error, request_generation, request_seq)
 
-        def done(result, error, req_gen=None):
+        def done(result, error, req_gen=None, req_seq=None):
             with state_lock:
                 state["in_flight"] = False
                 refresh_pending = state.pop("refresh_pending", False)
+            if req_seq is not None and req_seq != state["jobs_refresh_seq"]:
+                # Older overlapping response: never overwrite newer context.
+                if refresh_pending and not state["closed"]:
+                    post(refresh_jobs)
+                return
             if not state["closed"] and (generation is None or req_gen == generation()):
+                machine2: JobsRefreshState = state["jobs_refresh"]
                 if error:
-                    pass  # Job listing errors are logged, not shown in accounting
+                    # Retain prior rows; mark them stale for visible readback.
+                    from datetime import datetime, timezone as _tz
+
+                    applied = machine2.complete_failure(req_seq if req_seq is not None else machine2.sequence, error)
+                    if applied:
+                        state["jobs_refresh_applied_seq"] = machine2.applied_sequence
+                        state["jobs_refresh_status"] = "failure"
+                        state["jobs_refresh_error"] = machine2.last_error
+                        state["jobs_refresh_stale"] = machine2.stale
+                        try:
+                            if machine2.stale:
+                                jobs_refresh_label.SetLabel(
+                                    f"{t('jobs.refresh_failed_stale')}: {machine2.last_error}"
+                                    if _has_key("jobs.refresh_failed_stale")
+                                    else f"Refresh failed (stale): {machine2.last_error}"
+                                )
+                            else:
+                                jobs_refresh_label.SetLabel(
+                                    f"{t('jobs.refresh_failed')}: {machine2.last_error}"
+                                    if _has_key("jobs.refresh_failed")
+                                    else f"Refresh failed: {machine2.last_error}"
+                                )
+                        except Exception:
+                            pass
                 else:
                     items = tuple(result or ())
-                    render_items(items)
-                    for item in items:
-                        if isinstance(item, dict):
-                            job_id = str(item.get("id", item.get("job_id", ""))).strip()
-                            model._job_states.setdefault(job_id, str(item.get("state", "")).strip().upper())
-                    model.poll_active_jobs(items, final_state, generation=req_gen)
+                    from datetime import datetime, timezone as _tz
+
+                    applied = machine2.complete_success(
+                        req_seq if req_seq is not None else machine2.sequence,
+                        list(items),
+                        timestamp=datetime.now(_tz.utc).isoformat(),
+                    )
+                    if applied:
+                        state["jobs_refresh_applied_seq"] = machine2.applied_sequence
+                        state["jobs_refresh_status"] = "success"
+                        state["jobs_refresh_timestamp"] = machine2.last_success_ts
+                        state["jobs_refresh_error"] = ""
+                        state["jobs_refresh_stale"] = False
+                        try:
+                            jobs_refresh_label.SetLabel(
+                                f"{t('jobs.refresh_updated')}: {machine2.last_success_ts}"
+                                if _has_key("jobs.refresh_updated")
+                                else f"Updated: {machine2.last_success_ts}"
+                            )
+                        except Exception:
+                            pass
+                        render_items(items)
+                        for item in items:
+                            if isinstance(item, dict):
+                                job_id = str(item.get("id", item.get("job_id", ""))).strip()
+                                model._job_states.setdefault(job_id, str(item.get("state", "")).strip().upper())
+                        model.poll_active_jobs(items, final_state, generation=req_gen)
+                        # W28: selection survives refresh only when the
+                        # identity still exists; otherwise drop it so a stale
+                        # selection cannot cancel a different row.
+                        if state["selected_job"] and not selection_still_exists(
+                            state["selected_job"], list(items)
+                        ):
+                            _clear_job_selection()
             if refresh_pending and not state["closed"]:
                 post(refresh_jobs)
 
         Thread(target=fetch, daemon=True).start()
 
+    # --- Column sorting (semantic values) ------------------------------------
+    def _on_column_click(event):
+        col = event.GetColumn()
+        if 0 <= col < len(_JOB_TABLE_COLUMNS):
+            key = _JOB_TABLE_COLUMNS[col]
+            if state.get("sort_key") == key:
+                state["sort_reverse"] = not bool(state.get("sort_reverse", False))
+            else:
+                state["sort_key"] = key
+                state["sort_reverse"] = False
+            _apply_filter()
+        try:
+            event.Skip()
+        except Exception:
+            pass
+
     # --- Filter handling ----------------------------------------------------
     def _on_filter_changed(_event=None):
         state["filter_query"] = filter_field.GetValue().strip()
@@ -2102,8 +2223,16 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
                     if follower is None:
                         continue
                     if callable(readers) and channel.path:
-                        _chunk, retained, waiting = follower.poll(readers, _remote_statter)
-                        results[channel.id] = (retained, waiting, False, False)
+                        try:
+                            _chunk, retained, waiting = follower.poll(readers, _remote_statter)
+                        except PermissionError as error:
+                            # W29 OUT-010: permission denied is a per-channel
+                            # error, not a missing-file wait and not a
+                            # whole-tab failure. Sibling channels keep
+                            # their own waiting/following state.
+                            results[channel.id] = (str(error), False, False, False, True)
+                            continue
+                        results[channel.id] = (retained, waiting, False, False, False)
                         continue
                     # Legacy test/adaptor compatibility is restricted to semantic
                     # stdout/stderr channels; arbitrary paths always use readers.
@@ -2117,11 +2246,13 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
                                 content = legacy[0 if "stdout" in channel.roles else 1] if legacy else ""
                             else:
                                 content = legacy
-                            results[channel.id] = (content, False, True, False)
+                            results[channel.id] = (content, False, True, False, False)
+                        except PermissionError as error:
+                            results[channel.id] = (str(error), False, False, False, True)
                         except (FileNotFoundError, OSError):
-                            results[channel.id] = (None, True, False, True)
+                            results[channel.id] = (None, True, False, True, False)
                     else:
-                        results[channel.id] = (follower.text, True, False, False)
+                        results[channel.id] = (follower.text, True, False, False, False)
             except Exception as error:
                 post(_done_outputs, results, error, req_id, g, channels, active_owner)
             else:
@@ -2146,13 +2277,25 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
                         text_ctrl = output_channels.get(channel.id)
                         if not text_ctrl:
                             continue
-                        retained, waiting, snapshot, missing = result.get(channel.id, ("", False, False, False))
+                        entry = result.get(channel.id, ("", False, False, False))
+                        if len(entry) == 5:
+                            retained, waiting, snapshot, missing, channel_error = entry
+                        else:
+                            retained, waiting, snapshot, missing = entry
+                            channel_error = False
                         follower = state.get("followers", {}).get(channel.id)
                         if follower is not None and snapshot:
                             retained = follower.replace_snapshot(retained)
                         elif follower is not None and missing:
                             follower.state.waiting_state = min(follower.state.waiting_state + 1, 5)
                             retained = follower.text
+                        if channel_error:
+                            try:
+                                text_ctrl.SetValue(str(retained or "Permission denied"))
+                            except RuntimeError:
+                                pass
+                            _set_output_channel_status(channel.id, "jobs_outputs.status_error")
+                            continue
                         if output_channel_paused.get(channel.id, False):
                             _set_output_channel_status(channel.id, "jobs_outputs.status_paused")
                             continue
@@ -2179,13 +2322,79 @@ def _build_jobs(parent, model: WxJobsModel | None, *, list_jobs, read_output, ca
             _done_outputs({}, error, output_request_id, gen, resolved, owner)
 
     # --- Cancel with confirmation -------------------------------------------
-    def cancel_job(_event):
+    # W28: identity-safe cancel. The requested target must equal the current
+    # selection and still exist in the latest backend rows; otherwise a stale
+    # selection (reorder/filter/refresh drift) must not cancel another job.
+    # W30 CTRL-003..010: before-cancel identity/cluster/profile wording +
===UNTRACKED CHECK===
src/hpc_gui/services/job_submit_cancel.py
tests/test_w30_submit_cancel.py
$ python -m pytest tests/test_w28_jobs_identity_refresh.py tests/test_w29_job_outputs.py tests/test_wx_jobs_behavior.py tests/test_slurm_models.py -q 2>&1 | tail -5; echo "---REG2---"; python -m pytest tests/test_output_follower.py tests/test_output_channel_resolver.py tests/test_wx_editor.py -q 2>&1 | tail -5
.....................................................                    [100%]
53 passed in 12.88s
---REG2---
............................................                             [100%]
44 passed in 4.49s
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ git diff -- src/hpc_gui/wx_shell.py 2>&1 | head -n 150; echo "===WXJOBS-W30-TAIL==="; git diff -- src/hpc_gui/wx_jobs.py 2>&1 | grep -n "cancel_capability\|last_cancel\|build_cancel\|classify_cancel\|reflect_cancel\|cancel_confirmation\|CANCELLED\|ALREADY_GONE\|_wx_jobs_cancel" | head -n 60
diff --git a/src/hpc_gui/wx_shell.py b/src/hpc_gui/wx_shell.py
index b03a55d2..9fb25f32 100644
--- a/src/hpc_gui/wx_shell.py
+++ b/src/hpc_gui/wx_shell.py
@@ -2614,16 +2614,43 @@ def _editor_action_factory(session_state):
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
-            elif not slurm:
-                raise RuntimeError(t("editor.slurm_unavailable"))
+                _output = slurm.sbatch(remote_path)
             else:
-                slurm.sbatch(current.path)
+                _output = slurm.sbatch(current.path)
+            _status, _detail = submit_result_status(str(_output or ""))
+            if _status != "SUCCESS":
+                raise RuntimeError(f"Submission failed: {_detail}")
+            return _output
 
         def run(current):
             _require_pinned_session(current)
@@ -3122,7 +3149,22 @@ def _remote_files_callbacks(session_state, parent, lifecycle):
         slurm = _resolve_slurm()
         if not slurm or not callable(getattr(slurm, "sbatch", None)):
             raise RuntimeError(t("jobs.slurm_unavailable"))
-        return slurm.sbatch(path)
+        # W30 CTRL-001/002: required-field validation before sending and
+        # confirmed scheduler acceptance afterwards. Provider template rules
+        # are capability/config driven via _resolve_provider_config().
+        from hpc_gui.services.job_submit_cancel import (
+            submit_result_status,
+            validate_submit_request,
+        )
+
+        _errors = validate_submit_request(str(path or ""), None, provider_config=None)
+        if _errors:
+            raise RuntimeError("Submission validation failed: " + "; ".join(_errors))
+        _output = slurm.sbatch(path)
+        _status, _detail = submit_result_status(str(_output or ""))
+        if _status != "SUCCESS":
+            raise RuntimeError(f"Submission failed: {_detail}")
+        return _output
 
     def _editor(path, content="", request_id=None):
         try:
===WXJOBS-W30-TAIL===
35:+        "cancel_capability": "available",
36:+        "last_cancel_outcome": "",
37:+        "last_cancel_message": "",
38:+        "last_cancel_is_error": False,
305:+            build_cancel_confirmation,
306:+            cancel_capability_available,
307:+            reflect_cancel_result,
322:+            if not cancel_capability_available(_slurm_probe):
323:+                state["cancel_capability"] = "unavailable"
324:+                state["last_cancel_outcome"] = "UNAVAILABLE"
325:+                state["last_cancel_message"] = "Cancel is unavailable for this provider."
331:+        state["cancel_capability"] = "available"
361:+            expected_wording = build_cancel_confirmation(job_id, ctx.name or "")
401:+            _reflection = reflect_cancel_result(
404:+            state["last_cancel_outcome"] = _reflection.outcome
405:+            state["last_cancel_message"] = _reflection.message
406:+            state["last_cancel_is_error"] = _reflection.is_error
458:+    host._wx_jobs_cancel = cancel_job
$ python -c "import pathlib; print([p.name for p in pathlib.Path('docs/wave-reports/v2/opencode').glob('W30*')]); print([p.name for p in pathlib.Path('artifacts').rglob('*W30*')])"; git diff --check 2>&1 | head -n 20; echo CHECK_DONE
['W30_WAVE_REPORT.md']
[]
warning: in the working copy of 'src/hpc_gui/services/output_follower.py', LF will be replaced by CRLF the next time Git touches it
CHECK_DONE
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import pathlib
for f in [pathlib.Path('opencode/REQUIREMENT_REGISTRY.md'), pathlib.Path('REQUIREMENT_REGISTRY.md')]:
    print(f, f.exists())
"
opencode\REQUIREMENT_REGISTRY.md True
REQUIREMENT_REGISTRY.md False
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
import re
text = open('opencode/REQUIREMENT_REGISTRY.md', encoding='utf-8').read()
# find W30 rows
for i,line in enumerate(text.splitlines()):
    if 'HPC-W07-CTRL-00' in line or ('W30' in line and 'CTRL' in line):
        print(f'{i+1}: {line[:600]}')
print('---')
print('total lines', len(text.splitlines()))
"
704: | `HPC-W07-CTRL-001` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 163 | Workstream F � Submission | `W30` | � | Validate required fields before sending. Do not mark submission successful without confirmed scheduler acceptance/job ID or equivalent provider result. |
705: | `HPC-W07-CTRL-002` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 165 | Workstream F � Submission | `W30` | � | If submission uses templates, provider-specific partition/account/directive rules must be capability/config driven. |
706: | `HPC-W07-CTRL-003` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 171 | Workstream G � Cancellation | `W30` | � | selected job identity; |
707: | `HPC-W07-CTRL-004` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 172 | Workstream G � Cancellation | `W30` | � | cluster/profile; |
708: | `HPC-W07-CTRL-005` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 173 | Workstream G � Cancellation | `W30` | � | confirmation wording; |
709: | `HPC-W07-CTRL-006` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 174 | Workstream G � Cancellation | `W30` | � | capability availability. |
710: | `HPC-W07-CTRL-007` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 178 | Workstream G � Cancellation | `W30` | � | reflect command result; |
711: | `HPC-W07-CTRL-008` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 179 | Workstream G � Cancellation | `W30` | � | refresh; |
712: | `HPC-W07-CTRL-009` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 180 | Workstream G � Cancellation | `W30` | � | tolerate race where job already ended; |
713: | `HPC-W07-CTRL-010` | MANDATORY | REQUIREMENT | `WAVE_V2_FINAL_07.md` | 181 | Workstream G � Cancellation | `W30` | � | do not treat �already gone� identically to unauthorized/error unless semantics justify it. |
---
total lines 1551
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
text = open('opencode/sources/WAVE_V2_FINAL_07.md', encoding='utf-8').read()
lines = text.splitlines()
for n in [160,161,162,163,164,165,166,167,168,169,170,171,172,173,174,175,176,177,178,179,180,181,182,183]:
    if 1 <= n <= len(lines):
        print(f'{n}: {lines[n-1][:500]}')
"
160:  -> UI refresh/status
161: ```
162: 
163: Validate required fields before sending. Do not mark submission successful without confirmed scheduler acceptance/job ID or equivalent provider result.
164: 
165: If submission uses templates, provider-specific partition/account/directive rules must be capability/config driven.
166: 
167: ## Workstream G � Cancellation
168: 
169: Before cancel:
170: 
171: - selected job identity;
172: - cluster/profile;
173: - confirmation wording;
174: - capability availability.
175: 
176: After cancel:
177: 
178: - reflect command result;
179: - refresh;
180: - tolerate race where job already ended;
181: - do not treat �already gone� identically to unauthorized/error unless semantics justify it.
182: 
183: P0: cancelling the wrong job because selection changed or profile context drifted.
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
text = open('src/hpc_gui/wx_jobs.py', encoding='utf-8').read()
i = text.find('def cancel_job')
print(text[i:i+6000])
"
def cancel_job(self, cancel: Callable[[str], Any], job_id: str) -> Any:
        return cancel(str(job_id)) if str(job_id).strip() else None

    def explain_failure(self, job: Any):
        self.failure = explain_job_failure(job)
        return self.failure

    def submitted(self, job_id: str, script_text: str, **kwargs: Any) -> None:
        if self.provenance:
            self.provenance.submitted(job_id, script_text, **kwargs)
        if self.notify:
            self.notify(str(job_id))

    def update_job_state(self, job_id: str, state: str, message: str = "") -> bool:
        """Publish one completion event per observed terminal state transition."""
        job_id, state = str(job_id).strip(), str(state).strip().upper()
        if not job_id:
            return False
        previous = self._job_states.get(job_id)
        self._job_states[job_id] = state
        if state not in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
            return False
        if previous == state or not self.completion_notify:
            return False
        if message:
            notification = message
        elif state == "COMPLETED":
            notification = t("login.job_completed").format(jobid=job_id)
        else:
            notification = t("login.job_failed").format(jobid=job_id, state=state)
        self.completion_notify(job_id, notification)
        return True

    def set_monitor_generation(self, generation: int) -> None:
        generation = int(generation)
        if generation == self._monitor_generation:
            return
        self._monitor_generation = generation
        self._active_job_ids.clear()
        self._monitor_initialized = False

    def poll_active_jobs(self, items, final_state=None, *, generation: int | None = None) -> bool:
        """Track squeue membership and query final states for disappeared jobs."""
        if generation is not None and int(generation) != self._monitor_generation:
            return False
        rows = tuple(items or ())
        current = {
            str(item.get("id", item.get("job_id", ""))).strip()
            for item in rows
            if isinstance(item, dict) and str(item.get("id", item.get("job_id", ""))).strip()
        }
        if not self._monitor_initialized:
            self._active_job_ids = current
            self._monitor_initialized = True
            for item in rows:
                if isinstance(item, dict):
                    self._job_states[str(item.get("id", item.get("job_id", "")))] = str(item.get("state", "")).strip().upper()
            return True
        for job_id in sorted(self._active_job_ids - current):
            state = str(final_state(job_id) if final_state else "").strip().upper()
            if state in {"COMPLETED", "FAILED", "CANCELLED", "TIMEOUT", "OUT_OF_MEMORY"}:
                self.update_job_state(job_id, state)
            elif self.completion_notify:
                self.completion_notify(job_id, t("login.job_finished").format(jobid=job_id))
        for item in rows:
            if isinstance(item, dict):
                self.update_job_state(item.get("id", item.get("job_id", "")), item.get("state", ""), "")
        self._active_job_ids = current
        return True


def show_job_output(parent, model: WxJobsModel, view_id: str, *, read_output=None, read_path=None, stat_path=None, follower=None, interval_ms: int = 1000, lifecycle=None, on_closed=None) -> int:
    """Show a live detached follower; late callbacks are ignored after close."""
    try:
        import wx
    except ImportError as exc:
        raise RuntimeError("wxPython is not installed") from exc
    view = next((item for item in model.detached if item.id == str(view_id)), None)
    frame = wx.Frame(parent, title=f"{t('jobs.open_output')} {view.id if view else view_id}", size=(800, 500))
    root = wx.BoxSizer(wx.VERTICAL)
    if follower is not None:
        root.Add(wx.StaticText(frame, label=follower.state.path), 0, wx.EXPAND | wx.ALL, 6)
    output = wx.TextCtrl(frame, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
    root.Add(output, 1, wx.EXPAND | wx.ALL, 6)
    controls = wx.BoxSizer(wx.HORIZONTAL)
    pause = wx.Button(frame, label=t("jobs.pause_output"))
    auto_scroll = wx.CheckBox(frame, label=t("files.auto_scroll"))
    auto_scroll.SetValue(True)
    controls.Add(pause, 0, wx.RIGHT, 6)
    controls.Add(auto_scroll, 0, wx.ALIGN_CENTER_VERTICAL)
    root.Add(controls, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 6)
    frame.SetSizer(root)
    frame._wx_output_controls = {"output": output, "pause": pause, "auto_scroll": auto_scroll, "follower": follower}
    timer = wx.Timer(frame)
    state = {"closed": False, "in_flight": False, "at_bottom": True}
    state_lock = Lock()

    def toggle_pause(_event=None):
        paused = follower is not None and follower.state.paused
        if follower is not None:
            follower.state.paused = not paused
        pause.SetLabel(
            t("jobs.resume_output") if follower is not None and follower.state.paused
            else t("jobs.pause_output")
        )

    def refresh(_event=None):
        if follower is None and not read_output:
            return
        state["at_bottom"] = _output_at_bottom(output)
        with state_lock:
            if state["closed"] or state["in_flight"]:
                return
            state["in_flight"] = True
            if follower is not None:
                follower.state.paused = pause.GetLabel() == t("jobs.resume_output")
                follower.state.auto_scroll = auto_scroll.GetValue()

        def fetch() -> None:
            try:
                if follower is not None:
                    if not callable(read_path):
                        raise RuntimeError(t("jobs_outputs.remote_reader_unavailable"))
                    _chunk, text, _waiting = follower.poll(read_path, stat_path)
                else:
                    text = model.update_detached(view.id, read_output())
                wx.C
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
$ python -c "
text = open('src/hpc_gui/wx_jobs.py', encoding='utf-8').read()
i = text.find('# --- Cancel with confirmation')
print(text[i:i+8000])
"
# --- Cancel with confirmation -------------------------------------------
    # W28: identity-safe cancel. The requested target must equal the current
    # selection and still exist in the latest backend rows; otherwise a stale
    # selection (reorder/filter/refresh drift) must not cancel another job.
    # W30 CTRL-003..010: before-cancel identity/cluster/profile wording +
    # capability gate; after-cancel result reflection, refresh, already-gone
    # tolerance with unauthorized/error kept distinct.
    def cancel_job(_event=None):
        from hpc_gui.services.job_submit_cancel import (
            build_cancel_confirmation,
            cancel_capability_available,
            reflect_cancel_result,
        )

        job_id = model.tracking.selected_job_id
        if not job_id or state["cancel_in_flight"]:
            return
        # CTRL-006: capability availability is an explicit visible state,
        # not a silent no-op. The button is disabled with a recorded reason.
        _cancel_backend = cancel
        if not callable(_cancel_backend):
            try:
                _slurm_probe = kwargs.get("slurm_backend", None)
            except Exception:
                _slurm_probe = None
            if not cancel_capability_available(_slurm_probe):
                state["cancel_capability"] = "unavailable"
                state["last_cancel_outcome"] = "UNAVAILABLE"
                state["last_cancel_message"] = "Cancel is unavailable for this provider."
                try:
                    btn_cancel.Enable(False)
                except Exception:
                    pass
                return
        state["cancel_capability"] = "available"
        if not cancel or not job_id:
            return
        if not cancel_target_is_safe(
            state.get("selected_job", ""), list(state.get("raw_items", [])), job_id
        ):
            btn_cancel.Enable(False)
            return
        # Full identity tuple guard (profile/cluster/provider/session/array).
        selected_identity = make_identity(
            state.get("selected_job", ""),
            profile_id=str(kwargs.get("profile_id", "")),
            cluster_id=str(kwargs.get("cluster_id", "")),
            provider_id=str(kwargs.get("provider_id", "")),
            session_generation=int(state.get("provider_generation", 0)),
        )
        requested_identity = make_identity(
            job_id,
            profile_id=str(kwargs.get("profile_id", "")),
            cluster_id=str(kwargs.get("cluster_id", "")),
            provider_id=str(kwargs.get("provider_id", "")),
            session_generation=int(state.get("provider_generation", 0)),
        )
        if not cancel_is_safe(selected_identity, requested_identity):
            btn_cancel.Enable(False)
            return
        # CTRL-003/004/005: selected identity + cluster/profile scope are the
        # guarded identities above; the confirmation names the exact target.
        ctx = model.selected_job_store.context
        try:
            expected_wording = build_cancel_confirmation(job_id, ctx.name or "")
        except Exception:
            expected_wording = ""
        name_part = f" ({ctx.name})" if ctx.name else ""
        try:
            msg = t("jobs.cancel_confirm").format(job_id=job_id + name_part)
        except Exception:
            msg = expected_wording or f"Cancel job {job_id}?"
        if expected_wording and expected_wording not in msg and job_id not in msg:
            msg = expected_wording
        if wx.MessageBox(msg, t("jobs.cancel"), wx.YES_NO | wx.ICON_WARNING) != wx.YES:
            return
        state["cancel_in_flight"] = True
        btn_cancel.Enable(False)

        def worker():
            try:
                _out = cancel(job_id)
                post(cancel_done, None, str(_out or ""))
            except Exception as error:
                post(cancel_done, error, "")

        def cancel_done(error, output_text=""):
            state["cancel_in_flight"] = False
            if state["closed"]:
                return
            # CTRL-009/010: consult the post-cancel scheduler state so an
            # already-ended race is confirmed, never conflated with refusal.
            _final = ""
            try:
                if callable(final_state):
                    _final = str(final_state(job_id) or "")
            except Exception:
                _final = ""
            _reflection = reflect_cancel_result(
                error, output_text, job_id=job_id, final_state=_final
            )
            state["last_cancel_outcome"] = _reflection.outcome
            state["last_cancel_message"] = _reflection.message
            state["last_cancel_is_error"] = _reflection.is_error
            # CTRL-007: reflect the command result visibly (dialog for
            # operators + state mirror for headless readback).
            try:
                if _reflection.is_error:
                    wx.MessageBox(
                        _reflection.message, t("jobs.cancel"), wx.OK | wx.ICON_ERROR
                    )
                else:
                    wx.MessageBox(
                        _reflection.message, t("jobs.cancel"), wx.OK | wx.ICON_INFORMATION
                    )
            except Exception:
                pass
            try:
                btn_cancel.Enable(True)
            except Exception:
                pass
            # CTRL-008: accepted and already-gone outcomes refresh the listing
            # so the GUI agrees with the scheduler.
            if _reflection.should_refresh:
                try:
                    refresh_jobs()
                except Exception:
                    pass

        Thread(target=worker, daemon=True).start()

    # --- Pause/Resume -------------------------------------------------------
    def toggle_outputs_pause(_event=None):
        state["outputs_paused"] = not state["outputs_paused"]
        state["user_paused"] = state["outputs_paused"]
        state["_timer_paused"] = state["outputs_paused"]
        outputs_pause_btn.SetLabel(t("jobs_outputs.resume_all" if state["outputs_paused"] else "jobs_outputs.pause_all"))
        for cid, button in output_channel_pause_buttons.items():
            output_channel_paused[cid] = state["outputs_paused"]
            button.SetLabel(t("jobs.resume_output" if state["outputs_paused"] else "jobs.pause_output"))
            _set_output_channel_status(
                cid,
                "jobs_outputs.status_paused" if state["outputs_paused"] else "jobs_outputs.status_following",
            )

    def open_detached(_event):
        job_id = state["selected_job"]
        if not read_output or not job_id:
            return
        view = model.open_detached()

        def read_stdout():
            result = read_output(job_id)
            if isinstance(result, dict):
                return result.get("stdout", "")
            if isinstance(result, (tuple, list)):
                return result[0] if result else ""
            return result

        show_job_output(host, model, view.id, read_output=read_stdout, lifecycle=lifecycle)

    # --- Shutdown -----------------------------------------------------------
    def _close_files_browser():
        if state["files_browser_closed"]:
            return
        state["files_browser_closed"] = True
        close_browser = getattr(files_browser, "_wx_host_close", None)
        if callable(close_browser):
            close_browser()

    def close(_event=None):
        with state_lock:
            if state["closed"]:
                return
            state["closed"] = True
            state["outputs_pending_generations"].clear()
        _close_files_browser()
        timer.Stop()
        unsubscribe_language_change(refresh_labels)
        host.Hide()
        host.Destroy()

    def on_destroy(event):
        # Embedded hosts can be destroyed directly by their parent without
        # going through the synthetic close callback.
        if
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
> ac-wave-opencode-auditor · muse-spark-1.3-contributor
Auditing W30 — loading canonical skill and evidence.
Report and requirements mapped — now verifying implementation and test evidence.
Core checks pass — now confirming requirement coverage and external evidence.
Fresh independent audit for W30 (read-only, no repairs).

**Authority read:** `waves/pending/W30.md` frontmatter (W30, execution, 10 owned IDs HPC-W07-CTRL-001..010, wave-local, fresh-independent), `REQUIREMENT_REGISTRY.md` W30 rows, `WAVE_V2_FINAL_07.md` Workstream F/G + P0 guard, live code, report `W30_WAVE_REPORT.md`.

**Identity binding:**
- HEAD `3e9635ba1cf0255d5a09f370e91d1ddb73cef888` matches report baseline.
- Spec bytes SHA-256 `389ED6AB0464A60811BC66E7C4F001536F8F783075A183E84BDA9D20EB893CCB` matches report observed hash; 10 IDs + policies verified.
- Candidate = working tree at HEAD + W30 hunks (`job_submit_cancel.py` new, `wx_shell.py` submit hunks, `wx_jobs.py` cancel hunks, `test_w30_submit_cancel.py` new). Sibling dirty/untracked hunks preserved, disclosed.

**Claim-to-source verification (all 10 CTRLs):**
- CTRL-001/002: `validate_submit_request`/`extract_sbatch_job_id`/`submit_result_status` + both `wx_shell.py` submit paths validate then require `Submitted batch job <id>` token; provider partition/account rules config-driven. Verified in source.
- CTRL-003/004: `cancel_target_is_safe` row-list gate + `make_identity`/`cancel_is_safe` full-tuple guard preserved in `cancel_job`. Verified.
- CTRL-005: `build_cancel_confirmation` always names job ID; `cancel_job` wording fallback guarantees ID. Verified.
- CTRL-006: `cancel_capability_available` probe + explicit `UNAVAILABLE` state/disabled button. Verified.
- CTRL-007/008: `reflect_cancel_result` mirrors `last_cancel_*`, dialogs reflection, refreshes only on `CANCELLED`/`ALREADY_GONE`. Verified.
- CTRL-009/010: `classify_cancel_outcome` with gone/unauthorized lexicons, race precedence, `final_state` terminal confirmation. Verified. Lexicon breadth is implementation choice; required distinctions pinned by tests, no owned-semantics violation.

**Fresh test execution on current candidate:**
- `tests/test_w30_submit_cancel.py`: 15 passed (12 unit + 3 wx GUI with select-event → cancel-handler → CallAfter → state + MessageBox + refresh-count readback).
- Regression `test_w28 + test_w29 + test_wx_jobs_behavior + test_slurm_models`: 53 passed.
- Regression `test_output_follower + test_output_channel_resolver + test_wx_editor`: 44 passed.
- `git diff --check`: clean. No secrets/generated noise/weakened tests observed. No skip/xfail added.

**Evidence classes:** GUI satisfied via exact runtime action/test/readback. EXTERNAL truthfully `EXTERNAL_BLOCKED` (no invented creds, no mock substitution); owned rows impose no live-cluster acceptance text, so residual does not block. PACKAGE N/A justified (no artifact claim).

**Verdict:** No owned blocking defect. No routing/reopen. No human deferral.

AC_WAVE_MACHINE_RESULT_BEGIN
WAVE_PHASE_STATUS: PASS
AC_WAVE_MACHINE_RESULT_END
```

WAVE_PHASE_STATUS: PASS
