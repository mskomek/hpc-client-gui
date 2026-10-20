"""Shared Unicode path fixtures used by baseline and filesystem tests."""

import unicodedata


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
JAPANESE_DIRS = ["研究_ジョブ", "計算_結果", "日本語_ディレクトリ"]
JAPANESE_FILES = [
    "日本語_計算結果.txt",
    "ジョブ結果.slurm",
    "研究_スクリプト.sh",
]
MIXED_DIRS = ["Türkçe_日本語"]
MIXED_FILES = ["iş_日本語_δ.txt", "Çalışma_Sonucu_日本語.txt"]
SYMBOL_FILES = ["★_Favorites.txt", "ΔPressure_ölçüm.txt", "🚀_job.txt"]
TURKISH_CASING = ["I_upper.txt", "İ_upper.txt", "ı_lower.txt", "i_lower.txt"]
MOJIBAKE_STAR = "â˜…"
CORRECT_STAR = "★"


def nfc_nfd_names() -> tuple[str, str]:
    """Return canonically equivalent NFC and NFD sample names."""
    value = "café.txt"
    return unicodedata.normalize("NFC", value), unicodedata.normalize("NFD", value)
