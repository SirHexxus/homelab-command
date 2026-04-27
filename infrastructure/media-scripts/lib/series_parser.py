"""Manga series name extraction from archive filenames.

Filenames in the zip/ directory follow patterns like:
    07-Ghost v02 c06-11.zip
    0 no Soukoushi (Complete).zip
    #000000 - Ultra Black v01 c02.zip
    Ai Yori Aoshi v01 c01-06.zip

The series name is everything before the first volume (v##), chapter (c##),
or trailing qualifier ((Complete), (Ongoing), etc.).
"""

import re
from pathlib import Path


# Patterns that mark the end of a series name in a filename stem.
# Ordered from most specific to least specific.
_SERIES_END_PATTERNS = [
    r"\s+v\d+",          # volume: v01, v02
    r"\s+vol\.?\s*\d+",  # volume: vol. 1, vol1
    r"\s+c\d+",          # chapter: c001, c01
    r"\s+ch\.?\s*\d+",   # chapter: ch. 1
    r"\s*\([^)]*\)\s*$", # trailing qualifier: (Complete), (Ongoing)
    r"\s+-\s*$",         # trailing dash with nothing after
]

_COMBINED_PATTERN = re.compile(
    "(" + "|".join(_SERIES_END_PATTERNS) + ")",
    flags=re.IGNORECASE,
)


def extract_series_name(filename: str | Path) -> str:
    """Extract a series name from a manga archive filename.

    Args:
        filename: Filename or Path (stem or full name with extension).

    Returns:
        Cleaned series name string, or the original stem if nothing matched.
    """
    stem = Path(filename).stem

    match = _COMBINED_PATTERN.search(stem)
    if match:
        series = stem[: match.start()].strip()
    else:
        series = stem.strip()

    # Strip leading/trailing punctuation that looks like a sort prefix.
    series = series.strip(" \t-_")
    return series if series else stem


def safe_dirname(series: str) -> str:
    """Convert a series name to a filesystem-safe directory name.

    Removes or replaces characters that are problematic on Linux/NTFS/NFS.
    Does NOT lower-case — preserves original capitalisation for readability.
    """
    # Replace path separators and null bytes.
    safe = series.replace("/", "-").replace("\\", "-").replace("\x00", "")
    # Collapse multiple spaces/dashes.
    safe = re.sub(r"\s{2,}", " ", safe)
    safe = re.sub(r"-{2,}", "-", safe)
    return safe.strip(" -")
