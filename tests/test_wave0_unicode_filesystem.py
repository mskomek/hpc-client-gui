"""Filesystem boundary checks for the shared Unicode path fixtures."""

import pytest

from support.unicode_golden_fixtures import (
    JAPANESE_FILES,
    MIXED_FILES,
    SYMBOL_FILES,
    TURKISH_CASING,
    TURKISH_FILES,
    nfc_nfd_names,
)


pytestmark = [pytest.mark.contract, pytest.mark.semantic, pytest.mark.regression]


def _round_trip_names(tmp_path, names, content):
    for name in names:
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        assert path.exists()
        assert path.read_text(encoding="utf-8") == content


def test_turkish_file_create_and_read(tmp_path):
    _round_trip_names(tmp_path, TURKISH_FILES, "test content")


def test_japanese_file_create_and_read(tmp_path):
    _round_trip_names(tmp_path, JAPANESE_FILES, "テスト内容")


def test_mixed_file_create_and_read(tmp_path):
    _round_trip_names(tmp_path, MIXED_FILES, "mixed content 日本語")


def test_symbol_file_create_and_read(tmp_path):
    _round_trip_names(tmp_path, SYMBOL_FILES, "symbol content")


def test_turkish_casing_file_create_and_read(tmp_path):
    _round_trip_names(tmp_path, TURKISH_CASING, "casing test")


def test_nfc_nfd_file_create_and_read(tmp_path):
    nfc_name, nfd_name = nfc_nfd_names()
    nfc_path, nfd_path = tmp_path / nfc_name, tmp_path / nfd_name
    nfc_path.write_text("NFC content", encoding="utf-8")
    nfd_path.write_text("NFD content", encoding="utf-8")
    assert nfc_path.read_text(encoding="utf-8") == "NFC content"
    assert nfd_path.read_text(encoding="utf-8") == "NFD content"


def test_star_file_create_and_read(tmp_path):
    _round_trip_names(tmp_path, ["★ Favorites.txt"], "star content")
