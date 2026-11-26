from __future__ import annotations

from unittest import mock

import pytest

@pytest.mark.unit
@pytest.mark.semantic
def test_application_identity_uses_product_name():
    from hpc_gui.wx_application import configure_application_identity

    app = mock.Mock()
    configure_application_identity(app)

    app.SetAppName.assert_called_once_with("HPC Client GUI")
    app.SetAppDisplayName.assert_called_once_with("HPC Client GUI")
    app.SetVendorName.assert_called_once_with("mskomek")
