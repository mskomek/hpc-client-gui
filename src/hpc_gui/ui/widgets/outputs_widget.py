from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from hpc_gui.core.i18n import t

class OutputsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.session = None
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(t("files.placeholder")))
        lay.addStretch(1)

    def set_session(self, session):
        self.session = session
