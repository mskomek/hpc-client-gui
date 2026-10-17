from __future__ import annotations

import pathlib
import sys
import pytest
TURKISH_NAMES = [
    "İşler_Çağrı_Ölçüm",
    "Isı_İstanbul_Şehir",
    "Üniversite_Kümesi",
    "çalışma.txt",
    "şğüöçıİ.dat",
    "Ölçüm_Sonucu.txt",
    "O'Brien_Çalışma.txt",
]
JAPANESE_NAMES = [
    "研究_ジョブ",
    "計算_結果",
    "日本語_ディレクトリ",
    "日本語_計算結果.txt",
    "ジョブ結果.slurm",
    "研究_スクリプト.sh",
]
MIXED_NAMES = [
    "Türkçe_日本語",
    "iş_日本語_δ.txt",
    "Çalışma_Sonucu_日本語.txt",
]
SYMBOL_NAMES = [
    "★_Favorites.txt",
    "ΔPressure_ölçüm.txt",
    "🚀_job.txt",
]
ALL_UNICODE_NAMES = TURKISH_NAMES + JAPANESE_NAMES + MIXED_NAMES + SYMBOL_NAMES

__all__ = [
    'pathlib',
    'sys',
    'pytest',
    'TURKISH_NAMES',
    'JAPANESE_NAMES',
    'MIXED_NAMES',
    'SYMBOL_NAMES',
    'ALL_UNICODE_NAMES',
]
