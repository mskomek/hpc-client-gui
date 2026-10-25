import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError, URLError
from unittest.mock import patch

import pytest

from scripts.generate_qt_lgpl_sources import write_sources

pytestmark = [pytest.mark.release, pytest.mark.license]


class QtLgplSourcesTests(unittest.TestCase):
    def test_writes_records_only_after_urls_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            versions = root / "versions.txt"
            output = root / "QT_LGPL_SOURCES.json"
            versions.write_text(
                "PySide6: 6.11.2\nShiboken6: 6.11.2\n"
                "PySide6-Essentials: 6.11.2\nPySide6-Addons: 6.11.2\n",
                encoding="utf-8",
            )

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *_):
                    return False

                def read(self, _size):
                    return b"ok"

            with patch("scripts.generate_qt_lgpl_sources.urlopen", return_value=Response()) as opened:
                write_sources(versions, output)
            data = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(len(data["records"]), 5)
            self.assertEqual(opened.call_count, 2)
            self.assertIn("v6.11.2", data["records"][-1]["source_tag_url"])

    def test_retries_transient_url_error_without_skipping_verification(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            versions = root / "versions.txt"
            output = root / "QT_LGPL_SOURCES.json"
            versions.write_text(
                "PySide6: 6.11.2\nShiboken6: 6.11.2\n"
                "PySide6-Essentials: 6.11.2\nPySide6-Addons: 6.11.2\n",
                encoding="utf-8",
            )

            class Response:
                def __enter__(self):
                    return self

                def __exit__(self, *_):
                    return False

                def read(self, _size):
                    return b"ok"

            with (
                patch(
                    "scripts.generate_qt_lgpl_sources.urlopen",
                    side_effect=[URLError("temporary"), Response(), Response()],
                ) as opened,
                patch("scripts.generate_qt_lgpl_sources.time.sleep") as sleep,
            ):
                write_sources(versions, output)

            self.assertEqual(opened.call_count, 3)
            self.assertEqual([call.args[0] for call in sleep.call_args_list], [0.5])
            self.assertEqual(len(json.loads(output.read_text(encoding="utf-8"))["records"]), 5)

    def test_does_not_retry_permanent_http_error(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            versions = root / "versions.txt"
            output = root / "QT_LGPL_SOURCES.json"
            versions.write_text(
                "PySide6: 6.11.2\nShiboken6: 6.11.2\n"
                "PySide6-Essentials: 6.11.2\nPySide6-Addons: 6.11.2\n",
                encoding="utf-8",
            )
            error = HTTPError("https://code.qt.io/tag", 404, "not found", {}, None)
            with (
                patch("scripts.generate_qt_lgpl_sources.urlopen", side_effect=error) as opened,
                patch("scripts.generate_qt_lgpl_sources.time.sleep") as sleep,
                self.assertRaisesRegex(RuntimeError, "Unable to verify source URL"),
            ):
                write_sources(versions, output)

            self.assertEqual(opened.call_count, 1)
            sleep.assert_not_called()
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
