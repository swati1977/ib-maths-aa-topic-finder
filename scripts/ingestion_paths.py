#!/usr/bin/env python3
"""Safe path construction for manifest-driven ingestion artifacts."""
from __future__ import annotations

import re
from pathlib import Path

PAPER_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


def validate_paper_id(paper_id: str) -> str:
    value = str(paper_id)
    if not PAPER_ID_PATTERN.fullmatch(value):
        raise ValueError(f"Unsafe paper id: {value!r}")
    return value


def safe_output_path(root: Path, paper_id: str, suffix: str = "") -> Path:
    if Path(suffix).name != suffix or any(separator in suffix for separator in ("/", "\\")):
        raise ValueError(f"Unsafe output suffix: {suffix!r}")
    safe_id = validate_paper_id(paper_id)
    resolved_root = root.resolve()
    candidate = (resolved_root / f"{safe_id}{suffix}").resolve()
    try:
        candidate.relative_to(resolved_root)
    except ValueError as error:
        raise ValueError(f"Output path escapes root: {candidate}") from error
    return candidate
