from __future__ import annotations

import json
import pathlib
import sys
import unicodedata
import pytest
TURKISH_DIRS = [
    "İşler_Çağrı_Ölçüm",
    "Isı_İstanbul_Şehir",
    "Üniversite_Kümesi",
]
TURKISH_FILES = [
    "ısı_ölçümü_İstanbul.txt",
    "şğüöçıİ.dat",
    "Çalışma_Sonucu.txt",
    "O'Brien_Çalışma.txt",
]
JAPANESE_DIRS = [
    "研究_ジョブ",
    "計算_結果",
    "日本語_ディレクトリ",
]
JAPANESE_FILES = [
    "日本語_計算結果.txt",
    "ジョブ結果.slurm",
    "研究_スクリプト.sh",
]
MIXED_DIRS = [
    "Türkçe_日本語",
]
MIXED_FILES = [
    "iş_日本語_δ.txt",
    "Çalışma_Sonucu_日本語.txt",
]
SYMBOL_FILES = [
    "★_Favorites.txt",
    "ΔPressure_ölçüm.txt",
    "🚀_job.txt",
]
TURKISH_CASING = [
    "I_upper.txt",
    "İ_upper.txt",
    "ı_lower.txt",
    "i_lower.txt",
]
NFC_PATH = pathlib.PurePosixPath("café.txt")  # NFC: é = U+00E9
NFD_PATH = pathlib.PurePosixPath(unicodedata.normalize("NFD", "café.txt"))  # NFD: e + combining acute
MOJIBAKE_STAR = "â˜…"
CORRECT_STAR = "★"
def _norm(p: str) -> str:
    """NFC-normalize a path string for comparison."""
    return unicodedata.normalize("NFC", p)

__all__ = [
    'json',
    'pathlib',
    'sys',
    'unicodedata',
    'pytest',
    'TURKISH_DIRS',
    'TURKISH_FILES',
    'JAPANESE_DIRS',
    'JAPANESE_FILES',
    'MIXED_DIRS',
    'MIXED_FILES',
    'SYMBOL_FILES',
    'TURKISH_CASING',
    'NFC_PATH',
    'NFD_PATH',
    'MOJIBAKE_STAR',
    'CORRECT_STAR',
    '_norm',
]
