"""FTP activity-table leaf for the file-manager FTP widget.

Owns ``ActivityTableMixin``: activity table construction, row rendering and
reconciliation, and retranslation. (The concrete ``TransferActivityPanel``
class shell and ``__init__`` stay in the facade, following the established
facade-owns-the-class pattern.) Controller sync/record/controls live in
``_ftp_activity_sync`` and menus in ``_ftp_activity_menus``; both reach panel
state via ``self``.

Imports Qt and the lower-level i18n helper only — never panels, FTP internals
of other leaves, controllers, or other branches.
"""

from __future__ import annotations

from hpc_gui.core.i18n import t

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QProgressBar,
    QTreeWidget,
    QTreeWidgetItem,
)

from hpc_gui.core.i18n import tr as _tr


class ActivityTableMixin:
    """Transfer-table view/render ownership (mixed into ``TransferActivityPanel``)."""

    _MAX_VISIBLE_TRANSFER_ROWS: int
    _PROGRESS_COLUMN: int
    _COLUMNS: list
    queue_list: object
    failed_list: object
    completed_list: object
    tabs: object
    status_label: object
    summary_label: object
    btn_stop: object
    btn_cancel: object
    btn_clear_pending: object

    def _make_transfer_table(self) -> QTreeWidget:
        view = QTreeWidget()
        view.setColumnCount(len(self._COLUMNS))
        view.setHeaderLabels(self._COLUMNS)
        view.setRootIsDecorated(True)
        view.setAlternatingRowColors(True)
        view.setUniformRowHeights(False)
        view.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        return view

    def retranslate_ui(self) -> None:
        self.setTitle(_tr("transfer.ftp_activity_title", "Transfers"))
        labels = (
            self._tab_label(_tr("transfer.queue_tab", "Queue"), self._tab_counts["queue"]),
            self._tab_label(_tr("transfer.failed_tab", "Failed"), self._tab_counts["failed"]),
            self._tab_label(_tr("transfer.completed_tab", "Completed"), self._tab_counts["completed"]),
        )
        for index, label in enumerate(labels):
            self.tabs.setTabText(index, label)
        self.btn_stop.setText(_tr("transfer.stop", "Stop"))
        self.btn_cancel.setText(_tr("transfer.cancel", "Cancel"))
        self.btn_clear_pending.setText(_tr("transfer.clear_pending", "Clear queued"))

    @staticmethod
    def _item_label(item) -> str:
        try:
            return item.label()
        except Exception:
            dst = getattr(item, "dst", "") or getattr(item, "src", "")
            op = getattr(item, "op", "transfer")
            name = dst.rstrip("/").split("/")[-1] if dst else ""
            return f"{op}: {name or dst}"

    @staticmethod
    def _format_size(size: int) -> str:
        try:
            value = float(size)
        except Exception:
            return ""
        units = ("bytes", "KB", "MB", "GB", "TB")
        index = 0
        while value >= 1024 and index < len(units) - 1:
            value /= 1024.0
            index += 1
        if index == 0:
            return f"{int(value):,} bytes"
        return f"{value:.1f} {units[index]}"

    @classmethod
    def _item_size(cls, item) -> int:
        cached = getattr(item, "cached_size", None)
        if cached is not None:
            try:
                return max(0, int(cached))
            except (TypeError, ValueError):
                pass
        path = getattr(item, "src", "") if getattr(item, "op", "") == "upload" else getattr(item, "dst", "")
        try:
            from pathlib import Path

            local = Path(path)
            return local.stat().st_size if local.exists() and local.is_file() else 0
        except Exception:
            return 0

    @classmethod
    def _item_columns(cls, item, status: str) -> list[str]:
        op = getattr(item, "op", "transfer")
        src = str(getattr(item, "src", "") or "")
        dst = str(getattr(item, "dst", "") or "")
        if op == "upload":
            local_file, remote_file, direction = src, dst, "-->"
        elif op == "download":
            local_file, remote_file, direction = dst, src, "<--"
        else:
            local_file, remote_file, direction = src, dst, "->"
        return [
            local_file,
            direction,
            remote_file,
            cls._format_size(cls._item_size(item)),
            "",
            str(getattr(item, "priority", "Normal") or "Normal"),
            status,
        ]

    @staticmethod
    def _visible_transfer_items(items) -> list:
        return [
            item
            for item in list(items or [])
            if getattr(item, "op", "") in {"upload", "download"}
        ]

    @staticmethod
    def _tab_label(label: str, count: int) -> str:
        return f"{label} ({count})"

    def _update_summary(self, items: list) -> None:
        total_size = sum(self._item_size(item) for item in items)
        self.summary_label.setText(
            t("ftp.summary").format(files=len(items), size=f"{total_size:,}")
        )

    def _progress_value(self, item, status: str) -> int:
        if status == "Successful":
            return 100
        return max(0, min(100, int(self._progress_by_item.get(id(item), 0))))

    def _install_progress_bar(
        self,
        view: QTreeWidget,
        row: QTreeWidgetItem,
        item,
        status: str,
    ) -> None:
        bar = QProgressBar(view)
        bar.setRange(0, 100)
        bar.setTextVisible(True)
        bar.setFormat("%p%")
        bar.setValue(self._progress_value(item, status))
        view.setItemWidget(row, self._PROGRESS_COLUMN, bar)
        if view is self.queue_list:
            self._progress_bar_by_item_id[id(item)] = bar

    def _reconcile_visible_rows(
        self,
        view: QTreeWidget,
        rows,
        hidden_count: int,
    ) -> None:
        """Make a transfer tree show exactly ``rows`` plus its Remaining row.

        ``rows`` is an ordered sequence of ``(item, status, detail)`` tuples
        for the capped visible transfers.  Rows that are already displayed for
        the same item are reused (preserving the progress bar and the item
        identity the context menu relies on); rows are moved, inserted, or
        removed only when membership or ordering changes.  The trailing
        "Remaining: N" row is kept in sync.
        """
        desired = []
        seen_ids: set[int] = set()
        for row in rows:
            item_id = id(row[0])
            if item_id not in seen_ids:
                desired.append(row)
                seen_ids.add(item_id)
        desired_ids = {id(item) for item, _status, _detail in desired}

        existing: dict[int, QTreeWidgetItem] = {}
        info_row = None
        for index in range(view.topLevelItemCount()):
            row = view.topLevelItem(index)
            item = row.data(0, Qt.ItemDataRole.UserRole)
            if item is not None:
                existing[id(item)] = row
            else:
                info_row = row

        for item_id, row in list(existing.items()):
            if item_id not in desired_ids:
                view.takeTopLevelItem(view.indexOfTopLevelItem(row))
                if view is self.queue_list:
                    self._row_by_item_id.pop(item_id, None)
                    self._progress_bar_by_item_id.pop(item_id, None)
                    self._progress_by_item.pop(item_id, None)
                del existing[item_id]

        for index, (item, status, detail) in enumerate(desired):
            item_id = id(item)
            row = existing.get(item_id)
            if row is None:
                row = QTreeWidgetItem(self._item_columns(item, status))
                row.setData(0, Qt.ItemDataRole.UserRole, item)
                view.insertTopLevelItem(index, row)
                self._install_progress_bar(view, row, item, status)
                existing[item_id] = row
            else:
                current = view.indexOfTopLevelItem(row)
                if current != index:
                    view.takeTopLevelItem(current)
                    view.insertTopLevelItem(index, row)
                    self._reinstall_progress_bar(view, row, item, status)
            self._update_row_content(view, row, item, status, detail)
            if view is self.queue_list:
                self._row_by_item_id[item_id] = row

        if hidden_count > 0:
            text = f"Remaining: {hidden_count}"
            if info_row is None:
                info_row = QTreeWidgetItem(["", "", text, "", "", "", ""])
                view.addTopLevelItem(info_row)
            else:
                info_row.setText(2, text)
                current = view.indexOfTopLevelItem(info_row)
                if current != len(desired):
                    view.takeTopLevelItem(current)
                    view.insertTopLevelItem(len(desired), info_row)
        elif info_row is not None:
            view.takeTopLevelItem(view.indexOfTopLevelItem(info_row))

    def _reinstall_progress_bar(
        self,
        view: QTreeWidget,
        row: QTreeWidgetItem,
        item,
        status: str,
    ) -> None:
        bar = (
            self._progress_bar_by_item_id.get(id(item))
            if view is self.queue_list
            else None
        )
        if bar is None:
            bar = QProgressBar(view)
            bar.setRange(0, 100)
            bar.setTextVisible(True)
            bar.setFormat("%p%")
            bar.setValue(self._progress_value(item, status))
        view.setItemWidget(row, self._PROGRESS_COLUMN, bar)
        if view is self.queue_list:
            self._progress_bar_by_item_id[id(item)] = bar

    def _update_row_content(
        self,
        view: QTreeWidget,
        row: QTreeWidgetItem,
        item,
        status: str,
        detail: str,
    ) -> None:
        for column, text in enumerate(self._item_columns(item, status)):
            if row.text(column) != text:
                row.setText(column, text)
        if detail:
            if row.childCount() == 0:
                row.addChild(QTreeWidgetItem(["", "", detail, "", "", "", ""]))
                row.setExpanded(True)
            elif row.child(0).text(2) != detail:
                row.child(0).setText(2, detail)
                row.setExpanded(True)
        elif row.childCount() > 0:
            while row.childCount() > 0:
                row.takeChild(0)

    def _render_full_list(
        self,
        view: QTreeWidget,
        items,
        status: str,
        detail: str = "",
    ) -> list:
        """Render a whole transfer list at once while keeping row identity."""
        visible = self._visible_transfer_items(items)
        rows = [
            (item, status, detail)
            for item in visible[: self._MAX_VISIBLE_TRANSFER_ROWS]
        ]
        hidden = len(visible) - self._MAX_VISIBLE_TRANSFER_ROWS
        self._reconcile_visible_rows(view, rows, hidden)
        return visible


__all__ = [
    "ActivityTableMixin",
]
