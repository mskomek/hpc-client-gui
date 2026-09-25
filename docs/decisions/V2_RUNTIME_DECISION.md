# V2 production GUI runtime decision (product owner)

Status: DECIDED — 2026-09-25, by the product owner (repository owner).
Answers: `RUNTIME-CUTOVER-001`, `RUNTIME-DEPENDENCY-001` (owner Wave `W56`); feeds `RUNTIME-CUTOVER-002/003` (`W57`).

## Decision

1. **wx is the V2 production GUI runtime.** `DEFAULT_GUI_RUNTIME` becomes `"wx"`; the production launch
   path (`python -m hpc_gui`, packaged executable) starts wx.
2. **Qt is legacy only.** The Qt/PySide6 implementation stays in the source tree as legacy code, but it is
   not a supported V2 runtime and is not shipped: no PySide6/QtWebEngine in the V2 production package,
   dependencies, support text or public documentation claims. It may remain reachable only as an explicit,
   unadvertised developer opt-in (e.g. an optional `legacy-qt` extra), never as a fallback the release relies on.
3. **wx must not depend on Qt.** wx runtime code must not import Qt UI modules; shared constants/behavior move
   to framework-neutral modules (V2 spec §7.2).

## Acceptance prerequisite

The mandatory wx acceptance prerequisite for the cutover is the controller-accepted wx Waves
`W26`–`W55` (in `waves/done/`, committed at `bb8ac6b3`). W56 verifies that state from repository truth
rather than waiting for a separate verdict artifact.

## Consequences (V2 spec §7.2)

- Tests that pin Qt as the default (e.g. `tests/test_wave0_unicode_baseline.py::test_qt_is_default_runtime`)
  encode the superseded decision and are updated to assert the wx default; Qt-only tests move under the
  existing `qt` marker as legacy coverage.
- Packaging (`build/windows/hpc-client-gui.spec` hidden imports, `pyproject.toml` dependencies), README/support
  text and third-party notices are re-audited to match this decision.
- The runtime-default/packaging change invalidates pre-cutover final evidence: a new clean candidate is built,
  hashed and replayed (W56 build, W57 `RUNTIME-CUTOVER-002/003`).
