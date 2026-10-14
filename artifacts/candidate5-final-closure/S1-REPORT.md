# S1 — W19 Process Isolation

Verdict: `S1_ISOLATION_JUSTIFIED`

## Findings

1. **W19 was in the broad partition.** `ISOLATED_FILES` was the concatenation of the wire and native GUI lists; `tests/test_w19_connection_lifecycle.py` appeared in neither. `build_commands()` therefore ran it as part of the bulk `tests` selector.
2. **W19 uses real wx lifecycle.** The module imports wx and marks the suite `gui`/`wx`. Its `wx_app` fixture obtains or creates a real `wx.App`; tests create real frames, connection panels, shell frames, and terminal panels. `_build_shell()` calls `create_shell_frame()` and shows the frame. Shell/terminal paths instantiate WebView-backed terminal controls where the platform supports them.
3. **The fixture deliberately leaves `wx.App` alive.** Teardown closes/destroys top-level windows and pumps deferred events, then intentionally avoids `app.Destroy()`. Its comment identifies a concrete native failure mode: destroying the shared app while shell frames with WebView-backed terminal panels are draining deferred deletes can crash the interpreter with `0xC0000374`. Process exit owns final reclamation.
4. **Existing policy already isolates the same lifecycle class.** `ISOLATED_NATIVE_GUI_FILES` includes the WebView terminal suite and wx Jobs/layout suites. The release-runner comment documents real `wx.App` create/destroy ordering, native toolkit teardown failures, WebView heap corruption after mixed-GUI tests, and Jobs-cluster native termination. Those files remain executed in dedicated pytest subprocesses; they are ignored only by the bulk selector, not skipped.
5. **W19 meets that policy.** It combines real wx app/frame lifecycle with shell terminal/WebView creation and a fixture that explicitly relies on process exit to avoid unsafe shared-app teardown. Keeping W19 in the broad mixed-GUI interpreter is inconsistent with the established native isolation boundary.

## Change

Added `tests/test_w19_connection_lifecycle.py` to `ISOLATED_NATIVE_GUI_FILES`. The existing command builder consequently adds `--ignore tests/test_w19_connection_lifecycle.py` to the broad pytest command and adds the file itself as a dedicated pytest selector. No tests are skipped or deselected, and no product source changed.

Extended `tests/test_release_test_suite.py`'s native-boundary regression to require W19 in the canonical list. The existing generic assertions prove that every listed file is ignored by the bulk command and occurs exactly once as an isolated selector.

## Evidence limits

The paired repair evidence at `D:\Projeler\.tmp\hpc-client-gui\candidate5-repair-ab\differential-final.json` reports no access violations in three controls and access-violation markers in PATCHED-1 and PATCHED-3. It also identifies W19 teardown-adjacent failures in the broad pytest block. This is consistent with process contamination, but does not by itself prove W19 is the necessary causal predecessor or assign every WER event to W19. The change is justified as native test-process boundary enforcement, not as proof of a product runtime fix. Supervisor PID/WER ownership and isolated W19 runs remain necessary for causal confirmation.

## Validation

Ran the source-level partition regression only:

```text
python -m pytest -q tests/test_release_test_suite.py
3 passed in 0.82s
```

No wx/WebView/native GUI test was run by S1.
