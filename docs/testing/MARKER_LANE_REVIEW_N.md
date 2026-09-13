# Packet N: Marker Lane Review

Captured at `ea1002bc`. Exact old and candidate node sets are archived in
`audit/archive/ea1002bc/test-suite-baseline/marker-lane-reconciliation.json`.
The comparison uses pytest's collected nodeids and actual markers; it does not
edit or enable an automatic workflow.

| Lane | Existing selected | Marker candidate | Exact | Decision |
| --- | ---: | ---: | :---: | --- |
| Release suite (`not packaging`) | 2,683 | 2,683 | yes | Already uses the registered packaging qualifier; retain the shared runner. |
| Packaging (`test_wheel_packaging.py -m packaging`) | 1 | 2 | no | The global marker also selects the artifact-dependent wx smoke node. |
| Explicit macOS file set | 55 | 0 | no | No tests currently carry the `macos` qualifier. |
| Compat file set | 202 | 1,504 | no | The category union selects 1,334 nodes outside the existing files and omits 32 in-set nodes. |
| CLI file set | 164 | 1,540 | no | The category union selects unrelated tests and omits six in-set nodes. |
| SSH file set | 45 | 870 | no | The category union selects unrelated tests and omits nine in-set nodes. |
| Windows pytest file set | 6 | 0 | no | No tests carry the `windows` qualifier; the selector also runs separate unittest discovery. |
| Plugin contract file | 10 | 576 | no | The global contract marker selects tests outside the existing plugin contract module. |

No selector migration has exact parity beyond the release suite, which already
uses `-m "not packaging"`. The packaging lane already uses its qualifier but
cannot drop its file restriction because another node also carries
`packaging`. All other selectors remain unchanged. In particular,
`.github/workflows/ci.yml` remains absent, `docs/ci-disabled/ci.yml` remains
archival, and the manual release workflow remains the only active workflow.

## Reconciled v4 recheck (2026-09-13)

This section supersedes the earlier 2,683-node snapshot above. The final governance test tree is `fe1943dbf18c3fb46f8510f1c5667cb5204361ba`, collected at 2,649 nodes. Exact selected nodeids are archived at `audit/archive/794226e/test-suite-final/marker-lane-reconciliation.json`.

| Lane | Existing selector | Marker candidate | Added / removed | Exact | Decision |
| --- | ---: | ---: | ---: | :---: | --- |
| Release suite | 2,599 | 2,599 | 0 / 0 | yes | Keep current runner selector. |
| Packaging | 3 | 50 | 47 / 0 | no | Keep file restriction plus marker. |
| macOS explicit | 55 | 52 | 28 / 31 | no | Keep explicit selection. |
| Compat | 202 | 1,667 | 1,470 / 5 | no | Keep file-based selection. |
| CLI | 164 | 1,671 | 1,510 / 3 | no | Keep file-based selection. |
| SSH | 45 | 1,008 | 975 / 12 | no | Keep file-based selection. |
| Windows pytest | 6 | 13 | 13 / 6 | no | Keep file selection and separate unittest discovery. |
| Contract | 10 | 621 | 618 / 7 | no | Keep explicit module selector. |

Only the existing release suite has exact marker parity. No selector or workflow was changed. Automatic GitHub CI remains disabled; `docs/ci-disabled/ci.yml` remains archival.
