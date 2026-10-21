from __future__ import annotations

import json
import string
import subprocess
import sys
from pathlib import Path

from hpc_gui.core.i18n import current_language, load_language, t
from hpc_gui.services.updater_helper import _localized_progress_text
from hpc_gui.wx_terminal_webview_bridge import TerminalBridgeMixin

ROOT = Path(__file__).resolve().parents[1]


def test_dynamic_ui_messages_follow_selected_language():
    previous = current_language()
    try:
        load_language("en")
        assert t("dirs.submit_success").format(jobid="42") == "Submitted with sbatch. Job ID: 42"
        assert t("transfer.remaining").format(hidden=3) == "Remaining: 3"
        assert t("updates.downloaded_bytes").format(bytes="1 MB") == "1 MB downloaded"
        assert t("ftp.summary").format(files=2, size="1,024") == "2 files. Total size: 1,024 bytes."

        load_language("tr")
        assert t("dirs.submit_success").format(jobid="42") == "İş sbatch ile gönderildi. İş kimliği: 42"
        assert t("transfer.remaining").format(hidden=3) == "Kalan: 3"
        assert t("updates.downloaded_bytes").format(bytes="1 MB") == "1 MB indirildi"
        assert t("ftp.summary").format(files=2, size="1.024") == "2 dosya. Toplam boyut: 1.024 bayt."
    finally:
        load_language(previous)


def test_wx_terminal_accessible_label_tracks_live_language_changes():
    class FakeWebView:
        def __init__(self):
            self.name = ""
            self.script = ""

        def SetName(self, value):
            self.name = value

        def SetAccessibleName(self, value):
            self.name = value

        def RunScript(self, value):
            self.script = value

    class Harness(TerminalBridgeMixin):
        def __init__(self):
            self._webview = FakeWebView()

    previous = current_language()
    try:
        harness = Harness()
        load_language("en")
        harness._update_accessibility_label()
        assert harness._webview.name == "Remote terminal"
        assert "Remote terminal" in harness._webview.script

        load_language("tr")
        harness._update_accessibility_label()
        assert harness._webview.name == "Uzak terminal"
        assert "Uzak terminal" in harness._webview.script
    finally:
        load_language(previous)


def test_independent_updater_progress_uses_saved_language_catalog():
    previous = current_language()
    try:
        load_language("en")
        assert _localized_progress_text("Starting application...", t) == "Starting application..."
        assert _localized_progress_text("Copying: package.dmg", t) == "Copying: package.dmg"

        load_language("tr")
        assert _localized_progress_text("Starting application...", t) == "Uygulama başlatılıyor..."
        assert _localized_progress_text("Copying: package.dmg", t) == "Kopyalanıyor: package.dmg"
    finally:
        load_language(previous)


def test_catalog_keys_and_placeholders_are_consistent():
    catalogs = {
        language: json.loads((ROOT / "src" / "hpc_gui" / "i18n" / f"{language}.json").read_text(encoding="utf-8"))
        for language in ("en", "tr")
    }

    def flatten(value, prefix=""):
        result = {}
        for key, item in value.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(item, dict):
                result.update(flatten(item, path))
            else:
                result[path] = item
        return result

    en, tr = map(flatten, (catalogs["en"], catalogs["tr"]))
    assert set(en) == set(tr)
    for key in en:
        fields = []
        for value in (en[key], tr[key]):
            fields.append({name for _, name, _, _ in string.Formatter().parse(value) if name})
        assert fields[0] == fields[1], key


def test_i18n_static_gate_passes():
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_i18n.py")],
        cwd=ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
