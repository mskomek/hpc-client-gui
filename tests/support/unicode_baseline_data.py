"""Golden unicode fixtures for the Wave 0 baseline tests (W65 architecture split)."""

from __future__ import annotations

import pathlib
import unicodedata

# Turkish characters
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

# Japanese characters
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

# Mixed scripts
MIXED_DIRS = [
    "Türkçe_日本語",
]
MIXED_FILES = [
    "iş_日本語_δ.txt",
    "Çalışma_Sonucu_日本語.txt",
]

# Symbol/special fixtures
SYMBOL_FILES = [
    "★_Favorites.txt",
    "ΔPressure_ölçüm.txt",
    "🚀_job.txt",
]

# Turkish I/i casing variants
TURKISH_CASING = [
    "I_upper.txt",
    "İ_upper.txt",
    "ı_lower.txt",
    "i_lower.txt",
]

# NFC/NFD normalization variants
NFC_PATH = pathlib.PurePosixPath("café.txt")  # NFC: é = U+00E9
NFD_PATH = pathlib.PurePosixPath(unicodedata.normalize("NFD", "café.txt"))  # NFD: e + combining acute

# Mojibake reference
MOJIBAKE_STAR = "â˜…"
CORRECT_STAR = "★"
