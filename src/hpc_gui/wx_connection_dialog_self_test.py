"""ConnectionDialogSelfTestMixin owns the self test portion of the wx connection dialog."""

from __future__ import annotations

from typing import Any

from hpc_gui.core.i18n import t

# Extracted dialog responsibility; behavior stays on the public dialog facade.

class ConnectionDialogSelfTestMixin:
    def _test_cluster(self) -> None:
        collected = self._collect_profile()
        if collected is None:
            return
        if not self.btn_test_cluster.IsEnabled():
            return
        # Resolve credentials on GUI thread before starting worker
        # collected contains typed password in collected["password"] and no saved
        # secret fields (they were popped). For editing an existing profile we
        # must reuse the persisted secure secret when no typed password was
        # entered, without mutating storage or copying the secret into the UI.
        typed_password = str(collected.get("password", "") or "")
        # Determine original persisted profile identity for saved-secret lookup
        original: dict[str, Any] | None = None
        orig_name = str((self._initial_profile or {}).get("name") or "").strip()
        if orig_name:
            try:
                from hpc_gui.config.storage import load_profiles as _load_profiles

                original = next((p for p in _load_profiles() if p.get("name") == orig_name), None)
            except Exception:
                original = None
            if original is None:
                original = dict(self._initial_profile) if isinstance(self._initial_profile, dict) else None
        # Use shared resolver: typed password takes precedence, otherwise reuse
        # persisted secret (keychain/DPAPI/master via prompt). This matches the
        # required resolution order and never persists plaintext.
        # Build a profile dict for resolver that has the stored secret fields
        # plus the typed transient – we keep them separate to avoid carrying
        # secret fields through _collect_profile().
        resolve_profile: dict[str, Any] = dict(original) if isinstance(original, dict) else {}
        # Overlay collected non-secret fields for host/port etc, but keep
        # original's secret fields for resolver. Typed password is passed
        # explicitly, not via profile["password"] to avoid confusion.
        for key in ("name", "host", "port", "username", "host_key_policy", "save_password"):
            if key in collected:
                resolve_profile[key] = collected[key]
        # Ensure save_password reflects original when editing but typed override still works
        if original is not None and "save_password" not in collected:
            resolve_profile["save_password"] = original.get("save_password", False)
        # If original had save_password true, resolver will look at its secret fields
        # Build master ask callback for wx (GUI thread only)
        def _make_master_ask():
            cache: dict[str, str] = {"value": ""}

            def _load_cached():
                try:
                    from hpc_gui.config.storage import load_settings
                    from hpc_gui.core.secret_store import is_available, unprotect_secret

                    if cache["value"]:
                        return cache["value"]
                    st = load_settings()
                    token = st.get("master_password_dpapi")
                    if token and is_available():
                        try:
                            cache["value"] = unprotect_secret(str(token))
                            return cache["value"]
                        except Exception:
                            from hpc_gui.config.storage import update_settings

                            update_settings({"master_password_dpapi": ""})
                except Exception:
                    pass
                return ""

            def ask_master(confirm: bool) -> str | None:
                cached = _load_cached()
                if cached:
                    return cached
                dlg = self._wx.Dialog(self.dlg, title=t("login.master_create_title") if confirm else t("login.master_unlock_title"))
                sizer = self._wx.BoxSizer(self._wx.VERTICAL)
                prompt = self._wx.StaticText(dlg, label=t("login.master_create_prompt") if confirm else t("login.master_unlock_prompt"))
                try:
                    prompt.Wrap(400)
                except Exception:
                    pass
                sizer.Add(prompt, 0, self._wx.EXPAND | self._wx.ALL, 12)
                form = self._wx.FlexGridSizer(cols=2, vgap=8, hgap=12)
                form.AddGrowableCol(1, 1)
                pwd_label = self._wx.StaticText(dlg, label=t("login.master_password_label"))
                pwd_ctrl = self._wx.TextCtrl(dlg, style=self._wx.TE_PASSWORD)
                form.Add(pwd_label, 0, self._wx.ALIGN_CENTER_VERTICAL)
                form.Add(pwd_ctrl, 1, self._wx.EXPAND)
                confirm_ctrl = None
                if confirm:
                    confirm_label = self._wx.StaticText(dlg, label=t("login.master_confirm_label"))
                    confirm_ctrl = self._wx.TextCtrl(dlg, style=self._wx.TE_PASSWORD)
                    form.Add(confirm_label, 0, self._wx.ALIGN_CENTER_VERTICAL)
                    form.Add(confirm_ctrl, 1, self._wx.EXPAND)
                sizer.Add(form, 0, self._wx.EXPAND | self._wx.LEFT | self._wx.RIGHT, 12)
                remember_cb = self._wx.CheckBox(dlg, label=t("connection.remember_master_password"))
                try:
                    from hpc_gui.core.secret_store import is_available

                    remember_cb.Show(is_available())
                except Exception:
                    try:
                        remember_cb.Hide()
                    except Exception:
                        pass
                sizer.Add(remember_cb, 0, self._wx.ALL, 12)
                btns = dlg.CreateStdDialogButtonSizer(self._wx.OK | self._wx.CANCEL)
                sizer.Add(btns, 0, self._wx.EXPAND | self._wx.ALL, 12)
                dlg.SetSizer(sizer)
                dlg.Fit()
                try:
                    pwd_ctrl.SetFocus()
                except Exception:
                    pass
                result = dlg.ShowModal()
                pwd_val = pwd_ctrl.GetValue().strip()
                confirm_val = confirm_ctrl.GetValue().strip() if confirm_ctrl else ""
                dlg.Destroy()
                if result != self._wx.ID_OK:
                    return None
                if not pwd_val:
                    self._wx.MessageBox(t("login.err_master_empty"), t("login.err_title"), self._wx.OK | self._wx.ICON_WARNING)
                    return None
                if confirm and confirm_val != pwd_val:
                    self._wx.MessageBox(t("login.err_master_mismatch"), t("login.err_title"), self._wx.OK | self._wx.ICON_WARNING)
                    return None
                cache["value"] = pwd_val
                if remember_cb.GetValue():
                    try:
                        from hpc_gui.core.secret_store import protect_secret
                        from hpc_gui.config.storage import update_settings

                        update_settings({"master_password_dpapi": protect_secret(pwd_val)})
                    except Exception as exc:
                        self._wx.MessageBox(t("connection.master_password_store_failed").format(error=exc), t("login.err_title"), self._wx.OK | self._wx.ICON_WARNING)
                return pwd_val

            ask_master._cache = cache  # type: ignore
            return ask_master

        ask_master_cb = _make_master_ask()
        resolved_password: str | None
        try:
            from hpc_gui.services.connection_profile_service import resolve_password_for_connect

            # Pass typed_password explicitly; resolver will use it if non-empty,
            # otherwise will attempt to decrypt original's saved secret. For
            # master-encrypted secrets this will prompt via ask_master_cb on the
            # GUI thread (never from the worker).
            resolved_password = resolve_password_for_connect(
                resolve_profile if resolve_profile else collected,
                typed_password=typed_password,
                ask_master=ask_master_cb,
            )
        except RuntimeError as exc:
            msg = str(exc)
            self._wx.MessageBox(
                t("login.err_master_wrong") if "master_wrong" in msg else t("connection.saved_password_unavailable") if "saved_password_unavailable" in msg else t("connection.test_credential_error") if "test_credential" not in msg else msg,
                t("login.err_title") if "master_wrong" in msg or "saved_password_unavailable" in msg else t("common.error"),
                self._wx.OK | (self._wx.ICON_WARNING if "master_cancelled" in msg else self._wx.ICON_ERROR),
            )
            if "master_cancelled" in msg:
                # Cancel aborts cleanly – re-enable button and return without starting worker
                self.btn_test_cluster.Enable(True)
                self.btn_test_cluster.SetLabel(t("connection.test_cluster"))
                return
            # For other credential errors, also re-enable and surface safe error
            self.btn_test_cluster.Enable(True)
            self.btn_test_cluster.SetLabel(t("connection.test_cluster"))
            if "saved_password_unavailable" in msg or "master_wrong" in msg:
                # Surface as test credential error without secret
                self._wx.CallAfter(self._show_self_test_error, "credential_unavailable")
                return
            self._wx.CallAfter(self._show_self_test_error, type(exc).__name__)
            return
        except Exception as exc:
            self.btn_test_cluster.Enable(True)
            self.btn_test_cluster.SetLabel(t("connection.test_cluster"))
            self._wx.CallAfter(self._show_self_test_error, type(exc).__name__)
            return
        if resolved_password is None:
            self.btn_test_cluster.Enable(True)
            self.btn_test_cluster.SetLabel(t("connection.test_cluster"))
            self._wx.MessageBox(t("connection.saved_password_unavailable"), t("login.err_title"), self._wx.OK | self._wx.ICON_ERROR)
            self._wx.CallAfter(self._show_self_test_error, "credential_unavailable")
            return
        # Build transient profile for the test – use collected fields plus resolved password
        # Never copy password into visible field, never persist, never mutate storage.
        transient = dict(collected)
        transient["password"] = resolved_password
        # Ensure we do not accidentally persist secret fields – they were already popped
        for sk in ("password_dpapi", "password_enc", "password_salt", "password_keychain_ref"):
            transient.pop(sk, None)
        self.btn_test_cluster.Enable(False)
        self.btn_test_cluster.SetLabel(t("connection.cluster_test_running"))

        def worker() -> None:
            try:
                from hpc_gui.services.cluster_self_test import run_cluster_self_test
                from hpc_gui.wx_connection import WxConnectionModel, ssh_info_from_profile

                info = ssh_info_from_profile(transient, WxConnectionModel())
                result = run_cluster_self_test(
                    info,
                    provider=self._provider_template,
                    project=str(transient.get("project", "")),
                    account=str(transient.get("account", "")),
                )
                self._wx.CallAfter(self._show_self_test_result, result)
            except Exception as exc:
                self._wx.CallAfter(self._show_self_test_error, type(exc).__name__)
            finally:
                # Best-effort wipe transient password from memory
                try:
                    transient["password"] = ""
                except Exception:
                    pass

        import threading

        threading.Thread(target=worker, daemon=True).start()
    def _show_self_test_error(self, error_type: str) -> None:
        self.btn_test_cluster.Enable(True)
        self.btn_test_cluster.SetLabel(t("connection.test_cluster"))
        self._wx.MessageBox(
            t("connection.cluster_test_failed").format(error=error_type),
            t("common.error"),
            self._wx.OK | self._wx.ICON_ERROR,
        )
    def _show_self_test_result(self, result) -> None:
        wx = self._wx
        self.btn_test_cluster.Enable(True)
        self.btn_test_cluster.SetLabel(t("connection.test_cluster"))
        dlg = wx.Dialog(self.dlg, title=t("cluster_self_test.title"), style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        dlg.SetMinSize(wx.Size(500, 400))
        sizer = wx.BoxSizer(wx.VERTICAL)
        # Summary
        status_label = wx.StaticText(dlg, label=t("cluster_self_test.summary").format(status=result.status))
        status_label.Wrap(480)
        sizer.Add(status_label, 0, wx.EXPAND | wx.ALL, 12)
        # Sections
        text = wx.TextCtrl(dlg, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.HSCROLL)
        lines = []
        for sec in getattr(result, "sections", []):
            lines.append(f"[{sec.id}]")
            for item in sec.items:
                lines.append(f"  {item.id}: {item.status} {item.detail}")
        text.SetValue("\n".join(lines))
        sizer.Add(text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        btns = dlg.CreateStdDialogButtonSizer(wx.OK)
        sizer.Add(btns, 0, wx.EXPAND | wx.ALL, 12)
        dlg.SetSizer(sizer)
        dlg.Fit()
        dlg.ShowModal()
        dlg.Destroy()
