"""Legacy Qt dialog presentation; diagnostic content is shared with wx."""
from __future__ import annotations

from PySide6.QtWidgets import QMessageBox

from hpc_gui.core.ui_errors import prepare_exception


def show_exception(parent, *, title=None, user_message=None, exc=None, area="GEN"):
    caption, message = prepare_exception(
        title=title, user_message=user_message, exc=exc, area=area,
    )
    QMessageBox.critical(parent, caption, message)
