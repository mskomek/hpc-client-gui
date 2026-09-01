# Qt Pointer & Gesture Interaction Contract

This contract records behavior observed in the current Qt build so a future
adapter can preserve it without depending on Qt event names. IDs are mapped to
the feature inventory in `GUI_FEATURE_PARITY_BASELINE.md`.

| ID | Surface | Gesture | Contract |
| --- | --- | --- | --- |
| GUI-FILE-010 | Local/remote trees | Single left click | Select one item. Extended-selection trees retain the platform range/toggle semantics: Ctrl toggles an item and Shift extends from the anchor. |
| GUI-FILE-011 | Local/remote trees | Double left click on folder | Navigate into the folder. The parent row is not treated as a normal folder. |
| GUI-FILE-012 | Local tree | Double left click on file | Activate the file for editor/open handling. In the FTP local panel this is the upload action when the remote destination is active. |
| GUI-FILE-013 | Remote tree | Double left click on file | Emit file activation for open/download flow; the FTP adapter downloads the selected remote file to the local side. |
| GUI-FILE-014 | Directory tree | Middle click on folder | Open that folder in a new directory tab. Middle-click on files, parent rows, or empty space is a no-op. |
| GUI-FILE-015 | Directory tree | Right click | The clicked item becomes the effective context target when it was not already selected; otherwise the existing multi-selection is retained. Empty-space menus target the current directory. |
| GUI-FILE-016 | Directory tree | Drag/drop | Drag selected remote entries between remote panels to move; hold Ctrl while dropping to copy. Drop local OS paths on a remote folder to upload. Drop target folder wins, otherwise current directory is used. |
| GUI-FILE-017 | FTP local/remote trees | Ctrl+drag | Remote-to-remote is copy; local-to-remote remains upload. The operation is asynchronous and errors remain visible in transfer state. |
| GUI-FILE-018 | Directory tabs | Middle click tab | No current middle-click tab-close contract. Do not infer one during migration. |
| GUI-XFER-010 | FTP panel | Double-click local file | Queue upload to the active remote destination. |
| GUI-XFER-011 | FTP panel | Double-click remote file | Queue download to the active local destination. |
| GUI-XFER-012 | Transfer lists | Right click Queue item | Actions are queue-specific (cancel/remove/retry where applicable); never report a queued item as completed. |
| GUI-XFER-013 | Transfer lists | Right click Failed item | Actions are failure-specific (inspect/retry/remove where available); preserve the failure reason. |
| GUI-XFER-014 | Transfer lists | Right click Completed item | Actions are completion-specific (open destination/show details/remove where available); no retry is implied. |
| GUI-CONN-010 | Saved profiles | Double-click profile | Connect using the selected saved profile. Single click only changes selection. |
| GUI-JOBS-010 | Directories vs Jobs | Double-click/output click | Directories activates file navigation/open behavior; Jobs activates output/detail behavior. An unsupported target is an intentional no-op, not a guessed action. |
| GUI-JOBS-011 | Job context menus | Right click Queue/Failed/Completed | Menu entries must match the job state; state-changing actions remain explicit and no completed job is silently resubmitted. |
| GUI-EDIT-010 | Editor tabs | Tab close button / Ctrl+W | Close the active document after the existing dirty-state/save decision. The last tab remains usable. |
| GUI-EDIT-011 | Editor tabs | Tab reorder | Follow the native tab drag/reorder behavior where enabled; tab identity and dirty state move with the document. |
| GUI-EDIT-012 | Lint results | Double-click diagnostic | Navigate the editor to the diagnostic line (and preserve the existing column when available). Invalid/missing positions do not crash and remain inspectable. |
| GUI-EDIT-013 | Editor tabs | Middle click | No current middle-click editor-tab close feature. This is a documented non-feature. |

## Selection and safety rules

- Selection is never silently normalized from multi-selection to one item except
  when the context click lands on an unselected item, in which case that item
  is the explicit target.
- Destructive file actions remain behind the existing confirmation and transfer
  gates. A drag gesture does not bypass conflict handling or local-transfer
  safety checks.
- Ctrl modifies the operation only where the current target supports it; it is
  not a generic “force” or “skip confirmation” modifier.
- Keyboard-only operation remains required; every pointer action has an
  equivalent button, menu action, or keyboard navigation path where the Qt
  surface currently provides one.

## Intentional V2 decisions and known differences

- Preserve the current Directories/Jobs distinction and current no-op cases;
  do not add speculative double-click actions.
- Preserve platform-native Ctrl/Shift selection and drag conventions, while
  expressing the resulting operation through framework-neutral gesture IDs.
- Preserve the absence of middle-click editor-tab close. Adding it would be a
  V2 feature decision, not parity work.
- Context menus are owned by the local tree, remote tree, FTP transfer views,
  and connection/profile controls. They must be verified independently because
  no single Qt menu covers all surfaces.

## Verification checklist

- [x] Single/Ctrl/Shift selection, folder/file double-click, middle-click folder,
      right-click selection and drag/Ctrl+drag are recorded.
- [x] Local double-click upload and FTP remote double-click download are recorded.
- [x] Directories/Jobs differences and intentional no-op behavior are recorded.
- [x] Queue, Failed and Completed context-menu contracts are recorded.
- [x] Editor close/reorder and lint diagnostic navigation are recorded.
- [x] IDs use feature-baseline families and are checked for uniqueness.
