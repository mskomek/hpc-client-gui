# R13 Qt-free SSH credential migration

The legacy `test_ssh_credential_flow*` modules instantiated Qt `LoginWidget` and
`ConnectionDialog` objects through one shared fixture. Their active-runtime
contracts are now exercised by the wx connection surface and toolkit-free
service tests:

| Contract | Replacement coverage |
| --- | --- |
| Typed password precedence, transient use, and no plaintext persistence | `tests/test_wx_connection_hardening.py::test_typed_password_precedence`; wx Save & Connect coverage in the same module |
| Keychain and DPAPI credential resolution | `tests/test_wx_connection_hardening.py::test_keychain_connect_resolves`; `test_wx_connection_profiles_ssh_auth.py::test_ssh_info_resolves_secure_password` |
| Provider auth metadata and SSH info mapping | `tests/test_wx_connection_profiles_ssh_auth.py::test_saved_profile_to_sshinfo_mapping`; `test_mfa_order_and_no_log`; `tests/test_ssh_auth_method_negotiation.py` |
| Master password prompt, cache, cancel, and protected persistence | `tests/test_wx_connection_71_3_master_password.py`; `tests/test_wx_connection_71_5_master_persistence.py` |
| Secret redaction from logs and representations | `tests/test_wx_connection_hardening_security_contracts.py::test_error_redaction_no_secret_in_logs`; `tests/test_ssh_credential_contracts_headless.py` |

The new headless tests import only SSH contracts and authentication policy
services. No Qt test doubles, lazy imports, or collection skips are used.
