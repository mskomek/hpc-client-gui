"""Shared file-type icon metadata for directory browser surfaces."""

from __future__ import annotations

from pathlib import PurePath


_EXTENSION_GROUPS = (
    ({"pdf"}, "PDF", "#d64a4a"),
    ({"doc", "docx", "odt", "rtf"}, "DOC", "#3577c8"),
    ({"xls", "xlsx", "csv", "tsv", "ods"}, "XLS", "#2f9a69"),
    ({"ppt", "pptx", "odp"}, "PPT", "#d47b36"),
    (
        {"png", "jpg", "jpeg", "gif", "bmp", "svg", "webp", "tif", "tiff"},
        "IMG",
        "#8b62c8",
    ),
    ({"zip", "tar", "gz", "bz2", "xz", "7z", "rar", "tgz"}, "ZIP", "#bc842d"),
    (
        {
            "py", "js", "ts", "tsx", "jsx", "html", "css", "json", "xml",
            "yaml", "yml", "sh", "ps1", "c", "cpp", "h", "java", "go",
            "rs", "ipynb",
        },
        "<>",
        "#7359bd",
    ),
    ({"mp4", "mkv", "mov", "avi", "webm"}, "▶", "#ce5d78"),
    ({"mp3", "wav", "flac", "ogg", "m4a"}, "♪", "#368b9b"),
    ({"txt", "md", "log", "ini", "cfg", "conf", "out", "err"}, "TXT", "#617c9b"),
)
_EXTENSION_LOOKUP = {
    extension: (label, color)
    for extensions, label, color in _EXTENSION_GROUPS
    for extension in extensions
}

DIRECTORY_FILE_ICON_SPECS = (
    ("folder", "#f7c957"),
    *((label, color) for _, label, color in _EXTENSION_GROUPS),
    ("FILE", "#718096"),
)


def directory_file_icon_key(name: str, is_directory: bool) -> tuple[str, str]:
    """Return the shared icon label and accent color for a directory entry."""
    if is_directory:
        return "folder", "#f7c957"
    extension = PurePath(name).suffix.lower().lstrip(".")
    return _EXTENSION_LOOKUP.get(extension, ("FILE", "#718096"))
