# Adaptive Layout, DPI, and Geometry Contract

Stable IDs in this contract are product behavior IDs, independent of Qt or wx.

| ID | Contract |
|---|---|
| GUI-LAYOUT-001 | Major windows resize without overlap; primary actions remain reachable through layout, tabs, collapse, or scrolling. |
| GUI-DPI-001 | Layout uses logical/font metrics, not fixed physical pixels; labels wrap and buttons grow with translated text. |
| GUI-SCROLL-001 | Long Settings, Connection, Help, Plugin, ANSYS, and diagnostic content scrolls while primary actions remain reachable. |
| GUI-GEOMETRY-001 | Restored geometry is validated against current display work areas and recovered when a monitor is missing. |
| GUI-GEOMETRY-002 | Splitters, tables, trees, editor panes, and terminal surfaces expand usefully and retain minimum usable regions. |
| GUI-DPI-002 | Mixed 100/150/200% displays do not create an extreme size jump; dialogs stay near their active parent display. |
| GUI-TABLE-001 | Name/path columns stretch or scroll; bounded metadata columns keep readable minimum widths and full values remain inspectable. |
| GUI-MODAL-001 | Long errors and diagnostics wrap or scroll within the display work area; primary buttons stay visible. |

The acceptance matrix is: 1280×720 @100%, 1366×768 @100%, 1920×1080
@150%, 2560×1440 @200%, and 3840×2160 @200% or higher. Manual packaged
checks cover Windows per-monitor DPI and monitor removal; Linux X11/Wayland
and macOS Retina/mixed displays remain platform-specific manual checks.

The current Qt implementation is the compatibility baseline. Its existing
scrollable forms, screen-height clamping, splitter behavior, and terminal PTY
resize behavior are preserved. This wave adds a reusable geometry recovery
policy; it does not redesign screens or implement wx screens.

Geometry stores only window coordinates and dimensions, never profiles,
remote paths, credentials, or other connection data. Invalid values fall back
to a safe default. Every downstream wx screen wave must verify resize,
1366×768, 150/200% DPI, scrolling, primary-action reachability, clipping,
on-screen restore, keyboard focus, and translated-label growth.
