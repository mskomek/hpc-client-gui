from __future__ import annotations

from unittest.mock import patch

from PySide6.QtWidgets import QApplication, QCheckBox, QDialog, QDialogButtonBox, QLabel, QLineEdit

from hpc_gui.core.i18n import load_language, t
from hpc_gui.ui.widgets.login_widget import LoginWidget


app = QApplication.instance() or QApplication([])


def _inspect_dialog(owner, result=QDialog.DialogCode.Rejected):
    captured = {}

    def fake_exec():
        dialog = owner.findChildren(QDialog)[-1]
        captured["dialog"] = dialog
        return result

    return captured, fake_exec


def test_master_dialog_is_fully_localized_for_create_and_unlock():
    login = LoginWidget()
    try:
        for language, expected in (
            (
                "en",
                {
                    "create": "Create an encryption password",
                    "unlock": "Unlock saved passwords",
                    "password": "Encryption password",
                    "confirm": "Confirm encryption password",
                    "accept_create": "Save",
                    "accept_unlock": "Unlock",
                    "cancel": "Cancel",
                },
            ),
            (
                "tr",
                {
                    "create": "Şifreleme parolası oluştur",
                    "unlock": "Kayıtlı parolaların kilidini aç",
                    "password": "Şifreleme parolası",
                    "confirm": "Şifreleme parolasını doğrula",
                    "accept_create": "Kaydet",
                    "accept_unlock": "Kilidi aç",
                    "cancel": "İptal",
                },
            ),
        ):
            load_language(language)
            with patch("hpc_gui.ui.widgets.login_widget.os_secret_store_available", return_value=False):
                for confirm, mode in ((True, "create"), (False, "unlock")):
                    captured, fake_exec = _inspect_dialog(login)
                    with patch("hpc_gui.ui.widgets.login_widget.load_settings", return_value={}), patch(
                        "hpc_gui.ui.widgets.login_widget.QDialog.exec", side_effect=fake_exec
                    ):
                        assert login._ask_master_password(confirm=confirm) is None
                    dialog = captured["dialog"]
                    assert dialog.windowTitle() == expected[mode]
                    assert expected["password"] in [label.text() for label in dialog.findChildren(QLabel)]
                    if confirm:
                        assert expected["confirm"] in [label.text() for label in dialog.findChildren(QLabel)]
                    assert len(dialog.findChildren(QLineEdit)) == (2 if confirm else 1)
                    buttons = dialog.findChild(QDialogButtonBox)
                    assert buttons.button(QDialogButtonBox.StandardButton.Ok).text() == expected[f"accept_{mode}"]
                    assert buttons.button(QDialogButtonBox.StandardButton.Cancel).text() == expected["cancel"]
                    assert dialog.findChild(QCheckBox).isHidden()
    finally:
        login.deleteLater()


def test_master_dialog_validates_create_passwords_in_one_form():
    load_language("en")
    login = LoginWidget()
    try:
        captured, fake_exec = _inspect_dialog(login)

        def accept_valid():
            dialog = login.findChildren(QDialog)[-1]
            captured["dialog"] = dialog
            fields = dialog.findChildren(QLineEdit)
            fields[0].setText("correct horse")
            fields[1].setText("correct horse")
            dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
            return dialog.result()

        with (
            patch("hpc_gui.ui.widgets.login_widget.load_settings", return_value={}),
            patch("hpc_gui.ui.widgets.login_widget.os_secret_store_available", return_value=False),
            patch("hpc_gui.ui.widgets.login_widget.QDialog.exec", side_effect=accept_valid),
        ):
            assert login._ask_master_password(confirm=True) == "correct horse"
    finally:
        login.deleteLater()


def test_master_dialog_rejects_empty_and_mismatched_values_without_saving():
    load_language("en")
    login = LoginWidget()
    try:
        for values, expected_message in ((["", ""], t("login.err_master_empty")), ((["one", "two"]), t("login.err_master_mismatch"))):
            captured = {}

            def fake_exec(values=values):
                dialog = login.findChildren(QDialog)[-1]
                captured["dialog"] = dialog
                fields = dialog.findChildren(QLineEdit)
                for field, value in zip(fields, values):
                    field.setText(value)
                with patch("hpc_gui.ui.widgets.login_widget.QMessageBox.warning") as warning:
                    dialog.findChild(QDialogButtonBox).button(QDialogButtonBox.StandardButton.Ok).click()
                    warning.assert_called_once_with(login, t("login.err_title"), expected_message)
                return QDialog.DialogCode.Rejected

            with (
                patch("hpc_gui.ui.widgets.login_widget.load_settings", return_value={}),
                patch("hpc_gui.ui.widgets.login_widget.os_secret_store_available", return_value=False),
                patch("hpc_gui.ui.widgets.login_widget.update_settings") as update_settings,
                patch("hpc_gui.ui.widgets.login_widget.QDialog.exec", side_effect=fake_exec),
            ):
                assert login._ask_master_password(confirm=True) is None
                update_settings.assert_not_called()
    finally:
        login.deleteLater()


def test_windows_remember_option_is_visible_and_unchecked():
    load_language("en")
    login = LoginWidget()
    try:
        captured, fake_exec = _inspect_dialog(login)
        with (
            patch("hpc_gui.ui.widgets.login_widget.load_settings", return_value={}),
            patch("hpc_gui.ui.widgets.login_widget.os_secret_store_available", return_value=True),
            patch("hpc_gui.ui.widgets.login_widget.QDialog.exec", side_effect=fake_exec),
        ):
            assert login._ask_master_password(confirm=False) is None
        remember = captured["dialog"].findChild(QCheckBox)
        assert not remember.isHidden()
        assert not remember.isChecked()
    finally:
        login.deleteLater()
