"""File type and safe text decoding rules shared by file browser surfaces."""

from __future__ import annotations

import codecs
import mimetypes
from dataclasses import dataclass
from pathlib import Path

TEXT_EXTENSIONS = frozenset(
    ".txt .text .md .rst .log .json .jsonl .yaml .yml .toml .ini .cfg .conf "
    ".py .pyw .sh .bash .zsh .fish .slurm .sbatch .csh .tcsh .js .ts .tsx .jsx "
    ".html .htm .css .xml .sql .r .m .c .h .cc .cpp .hpp .java .go "
    ".rs .rb .pl .pm .lua .make .mk .cmake .dockerfile .properties .env .gitignore"
    .split()
)
EXECUTABLE_EXTENSIONS = frozenset(".exe .com .bat .cmd .ps1 .sh .bash .zsh .msi .scr".split())
IMAGE_EXTENSIONS = frozenset(".png .jpg .jpeg .webp .gif .bmp .tif .tiff .ico".split())
DOCUMENT_EXTENSIONS = frozenset(".pdf".split())
ARRAY_EXTENSIONS = frozenset(".csv .tsv .npy .npz .h5 .hdf5".split())
ARCHIVE_EXTENSIONS = frozenset(".zip .tar .gz .tgz .bz2 .xz .7z .rar".split())
BINARY_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS | ARRAY_EXTENSIONS | ARCHIVE_EXTENSIONS
LARGE_REMOTE_THRESHOLD = 25 * 1024 * 1024


@dataclass(frozen=True)
class FileType:
    category: str
    extension: str
    mime_type: str
    editable: bool
    executable: bool


def _looks_binary(prefix: bytes) -> bool:
    if not prefix:
        return False
    if prefix.startswith((codecs.BOM_UTF8, codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE, codecs.BOM_UTF32_LE, codecs.BOM_UTF32_BE)):
        return False
    if prefix.startswith((b"\x89PNG\r\n\x1a\n", b"%PDF-", b"PK\x03\x04", b"\x7fELF")):
        return True
    if b"\0" in prefix:
        return True
    controls = sum(byte < 9 or 13 < byte < 32 for byte in prefix)
    return controls / len(prefix) > 0.08


def detect_file_type(name: str | Path, prefix: bytes = b"") -> FileType:
    """Classify by suffix, with signatures able to veto an unsafe text suffix."""
    suffix = Path(str(name)).suffix.lower()
    mime = mimetypes.guess_type(str(name))[0] or "application/octet-stream"
    executable = suffix in EXECUTABLE_EXTENSIONS
    if suffix in TEXT_EXTENSIONS and not _looks_binary(prefix):
        category, editable = "text", True
    elif suffix in IMAGE_EXTENSIONS:
        category, editable = "image", False
    elif suffix in DOCUMENT_EXTENSIONS:
        category, editable = "document", False
    elif suffix in ARRAY_EXTENSIONS:
        category, editable = "data", suffix in {".csv", ".tsv"}
    elif suffix in ARCHIVE_EXTENSIONS:
        category, editable = "archive", False
    elif executable:
        category, editable = "executable", False
    elif _looks_binary(prefix):
        category, editable = "binary", False
    else:
        category, editable = "unknown", bool(prefix) and not _looks_binary(prefix)
    if _looks_binary(prefix) and category == "text":
        category, editable = "binary", False
    return FileType(category, suffix, mime, editable, executable)


def decode_text(data: bytes, *, name: str = "") -> str:
    return decode_text_with_encoding(data, name=name)[0]


def decode_text_with_encoding(data: bytes, *, name: str = "") -> tuple[str, str]:
    """Decode confirmed text with BOM handling and conservative legacy fallback."""
    if _looks_binary(data[:8192]):
        raise ValueError("This file contains binary data and cannot be opened as text.")
    bom_encodings = (
        (codecs.BOM_UTF32_LE, "utf-32"),
        (codecs.BOM_UTF32_BE, "utf-32"),
        (codecs.BOM_UTF16_LE, "utf-16"),
        (codecs.BOM_UTF16_BE, "utf-16"),
        (codecs.BOM_UTF8, "utf-8-sig"),
    )
    for marker, encoding in bom_encodings:
        if data.startswith(marker):
            return data.decode(encoding), encoding
    for encoding in ("utf-8",):
        try:
            return data.decode(encoding), encoding
        except UnicodeError:
            continue
    for encoding in ("cp1252", "latin-1"):
        try:
            decoded = data.decode(encoding)
            controls = sum(ord(ch) < 9 or 13 < ord(ch) < 32 for ch in decoded)
            if decoded and controls / len(decoded) > 0.02:
                break
            return decoded, encoding
        except UnicodeError:
            continue
    raise ValueError(f"{name or 'File'} is not a supported text file.")


def smart_open_preferences() -> dict[str, str]:
    from hpc_gui.config.storage import load_settings

    value = load_settings().get("smart_open_preferences", {})
    if not isinstance(value, dict):
        return {}
    return {
        str(ext).lower(): str(action)
        for ext, action in value.items()
        if str(ext).startswith(".") and action in {"system", "editor"}
    }


def remember_smart_open(extension: str, action: str) -> None:
    from hpc_gui.config.storage import update_settings

    ext = str(extension or "").lower()
    if ext and not ext.startswith("."):
        ext = "." + ext
    if not ext.startswith(".") or action not in {"system", "editor"}:
        raise ValueError("Invalid file-open preference.")
    values = smart_open_preferences()
    values[ext] = action
    update_settings({"smart_open_preferences": values})


def reset_smart_open_preferences() -> None:
    from hpc_gui.config.storage import load_config, save_config

    config = load_config()
    settings = config.get("settings")
    if isinstance(settings, dict):
        settings.pop("smart_open_preferences", None)
        config["settings"] = settings
        save_config(config)
