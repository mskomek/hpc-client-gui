import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.generate_qt_lgpl_sources import write_sources


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


if __name__ == "__main__":
    unittest.main()
