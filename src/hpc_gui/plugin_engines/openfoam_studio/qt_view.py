"""Qt widget construction for the OpenFOAM Case Studio page.

Pure layout only: every hosted widget is created here and exposed as a
page attribute, mirroring ``wx_view.WxCaseStudioView`` names so the
controller and action helpers read the same on both frameworks. No
business logic, no workspace access, no network.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QSplitter,
    QTabWidget,
    QTextEdit,
    QTreeWidget,
    QVBoxLayout,
    QWidget,
)


class QtCaseStudioView:
    """Builds the three-column Case Studio layout on a QWidget page."""

    def _build(self) -> None:
        outer = QVBoxLayout(self)
        toolbar = QHBoxLayout()
        self.new_button = QPushButton("New Case")
        self.open_button = QPushButton("Open Case")
        self.snapshot_button = QPushButton("Open Snapshot")
        self.save_button = QPushButton("Save Case")
        self.recover_button = QPushButton("Recover Save")
        self.recover_button.setEnabled(False)
        self.validate_button = QPushButton("Validate")
        self.allrun_button = QPushButton("Create Allrun")
        self.undo_button = QPushButton("Undo")
        self.redo_button = QPushButton("Redo")
        for button in (
            self.new_button,
            self.open_button,
            self.snapshot_button,
            self.save_button,
            self.recover_button,
            self.validate_button,
            self.allrun_button,
            self.undo_button,
            self.redo_button,
        ):
            toolbar.addWidget(button)
        toolbar.addWidget(QLabel("Edition"))
        self.product = QComboBox()
        self.product.addItem("OpenFOAM.com / ESI")
        self.product.setEnabled(False)
        self.version = QComboBox()
        self.version.addItem("v2312")
        self.version.setEnabled(False)
        toolbar.addWidget(self.product)
        toolbar.addWidget(self.version)
        outer.addLayout(toolbar)

        self.status = QLabel("No case open")
        outer.addWidget(self.status)
        main = QSplitter()
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Case structure"))
        left_layout.addWidget(QLabel("Search case"))
        self.case_search = QLineEdit()
        self.case_search.setPlaceholderText("Search dictionaries")
        left_layout.addWidget(self.case_search)
        self.case_search_results = QListWidget()
        self.case_search_results.setMaximumHeight(96)
        left_layout.addWidget(self.case_search_results)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Case")
        left_layout.addWidget(self.tree)
        main.addWidget(left)

        center = QWidget()
        center_layout = QVBoxLayout(center)
        center_layout.addWidget(QLabel("Visual Flow"))
        self.flow = QListWidget()
        center_layout.addWidget(self.flow)
        flow_actions = QHBoxLayout()
        self.move_step_up = QPushButton("Move Up")
        self.move_step_down = QPushButton("Move Down")
        self.remove_step = QPushButton("Remove Step")
        for button in (self.move_step_up, self.move_step_down, self.remove_step):
            flow_actions.addWidget(button)
        center_layout.addLayout(flow_actions)
        self.bottom = QTabWidget()
        self.source_tabs = QTabWidget()
        self.source_tabs.setTabsClosable(True)
        self.problems = QListWidget()
        self.diff = QTextEdit()
        self.diff.setReadOnly(True)
        self.validation = QTextEdit()
        self.validation.setReadOnly(True)
        self.preview = QTextEdit()
        self.preview.setReadOnly(True)
        self.bottom.addTab(self.source_tabs, "Source")
        self.bottom.addTab(self.problems, "Problems")
        self.bottom.addTab(self.diff, "Diff")
        self.bottom.addTab(self.validation, "Validation")
        self.bottom.addTab(self.preview, "Preview")
        center_layout.addWidget(self.bottom)
        main.addWidget(center)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(QLabel("Command library"))
        self.command_filter = QLineEdit()
        self.command_filter.setPlaceholderText("Filter commands")
        right_layout.addWidget(self.command_filter)
        self.commands = QListWidget()
        right_layout.addWidget(self.commands)
        self.add_step = QPushButton("Add Workflow Step")
        right_layout.addWidget(self.add_step)
        right_layout.addWidget(QLabel("Inspector"))
        self.command_details = QTextEdit()
        self.command_details.setReadOnly(True)
        self.command_details.setMaximumHeight(110)
        right_layout.addWidget(self.command_details)
        self.key_list = QListWidget()
        right_layout.addWidget(self.key_list)
        self.parameter_type = QLabel("Parameter type: unknown")
        right_layout.addWidget(self.parameter_type)
        self.value_editor_panel = QWidget()
        self.value_editor_layout = QVBoxLayout(self.value_editor_panel)
        self.value_editor_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self.value_editor_panel)
        self.apply_value = QPushButton("Apply (confirm)")
        right_layout.addWidget(self.apply_value)
        main.addWidget(right)
        main.setSizes([250, 560, 360])
        outer.addWidget(main)

    def _take_item_text(self, item: QListWidgetItem | None) -> str:
        return item.text() if item is not None else ""
