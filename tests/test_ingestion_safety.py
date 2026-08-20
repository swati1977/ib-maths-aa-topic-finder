import sys
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ingestion_paths import safe_output_path, validate_paper_id
import acquire_manifest


def test_manifest_paper_ids_use_a_conservative_filename_pattern():
    assert validate_paper_id("2025-may-p2-tz3") == "2025-may-p2-tz3"
    for unsafe in ("../escape", "/tmp/escape", "paper/child", "paper..escape", "Paper 1", ""):
        with pytest.raises(ValueError):
            validate_paper_id(unsafe)


def test_manifest_output_paths_cannot_escape_the_output_root(tmp_path):
    target = safe_output_path(tmp_path, "2025-may-p2-tz3", "-question.pdf")
    assert target == tmp_path / "2025-may-p2-tz3-question.pdf"
    with pytest.raises(ValueError):
        safe_output_path(tmp_path, "../escape", "-question.pdf")


def test_page_preparation_cli_accepts_manifest_raw_and_output_paths():
    result = subprocess.run(
        [sys.executable, "scripts/prepare_manifest_pages.py", "--help"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    for flag in ("--manifest", "--raw", "--output"):
        assert flag in result.stdout


def test_pdf_acquisition_falls_back_to_verified_alternate_url(tmp_path, monkeypatch):
    calls = []

    def fake_download(url, target):
        calls.append(url)
        if url == "https://primary.invalid/paper.pdf":
            raise OSError("primary unavailable")
        return {"path": str(target), "pages": 1, "bytes": 4, "sha256": "test"}

    monkeypatch.setattr(acquire_manifest, "download", fake_download)
    result = acquire_manifest.download_first(
        ["https://primary.invalid/paper.pdf", "https://alternate.example/paper.pdf"],
        tmp_path / "paper.pdf",
    )
    assert calls == ["https://primary.invalid/paper.pdf", "https://alternate.example/paper.pdf"]
    assert result["source_url"] == "https://alternate.example/paper.pdf"
