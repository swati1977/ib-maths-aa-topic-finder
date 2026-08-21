#!/usr/bin/env python3
"""Merge reviewed paper JSON into the static site's question bank."""
from __future__ import annotations

import json
from pathlib import Path

from ingestion_paths import validate_paper_id

ROOT = Path(__file__).resolve().parents[1]
TOPICS = {
    "Functions - Roots", "Quadratics", "Exponentials - Logarithms", "Graphs",
    "Sequences - Series", "Complex Numbers", "Permutation - Combination",
    "Binomial Theorem", "Remainder & Factor Theorem", "Mathematical Induction",
    "Radian", "Trigonometry", "Matrices", "Vectors - Lines - Planes",
    "Statistics", "Probability", "Differentiation", "Integration",
    "Differential Equations", "Kinematics",
}


def main() -> None:
    questions: list[dict] = []
    paper_summaries: list[dict] = []
    ids: set[str] = set()
    markscheme_manifest_path = ROOT / "data" / "official-markscheme-images.json"
    if markscheme_manifest_path.is_file():
        markscheme_payload = json.loads(markscheme_manifest_path.read_text(encoding="utf-8"))
        markscheme_manifest = markscheme_payload.get("questions", markscheme_payload)
    else:
        markscheme_manifest = {}

    legacy_names = ("p1-a", "p1-c", "p2-a", "p2-c")
    paper_paths = [ROOT / "data" / f"{name}.json" for name in legacy_names]
    paper_paths.extend(sorted((ROOT / "data" / "papers").glob("*.json")))
    if not paper_paths:
        raise ValueError("No paper data files found")

    for path in paper_paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        paper = payload["paper"]
        required_paper = {"id", "title", "paper", "zone", "year", "source_url", "pdf_url", "solution_status"}
        missing = required_paper - paper.keys()
        if missing:
            raise ValueError(f"{path.name}: missing paper fields {sorted(missing)}")
        session = str(paper.get("session", "May"))
        subject = str(paper.get("subject", "Mathematics: analysis and approaches SL"))

        count = 0
        for raw in payload["questions"]:
            qid = validate_paper_id(raw["id"])
            if qid in ids:
                raise ValueError(f"Duplicate question id: {qid}")
            ids.add(qid)
            labels = raw["labels"]
            unknown = set(labels) - TOPICS
            if unknown:
                raise ValueError(f"{qid}: unknown labels {sorted(unknown)}")
            if not labels:
                raise ValueError(f"{qid}: at least one topic label is required")
            if not raw["solution"].strip():
                raise ValueError(f"{qid}: solution is empty")
            official_markscheme = markscheme_manifest.get(qid)
            if int(paper["year"]) <= 2025:
                if not isinstance(official_markscheme, dict):
                    raise ValueError(f"{qid}: official markscheme image manifest entry is required")
                markscheme_pages = [int(page) for page in official_markscheme.get("pages", [])]
                markscheme_images = [str(image) for image in official_markscheme.get("images", [])]
                if not markscheme_pages or len(markscheme_images) != len(markscheme_pages):
                    raise ValueError(f"{qid}: official markscheme pages/images are incomplete")
                expected_markscheme_images = [
                    f"markschemes/{qid}-page-{page}.webp" for page in markscheme_pages
                ]
                if markscheme_images != expected_markscheme_images:
                    raise ValueError(f"{qid}: unsafe or unexpected official markscheme image paths")
                site_root = (ROOT / "site").resolve()
                for image in markscheme_images:
                    try:
                        (site_root / image).resolve().relative_to(site_root / "markschemes")
                    except ValueError as error:
                        raise ValueError(f"{qid}: official markscheme image escapes asset root") from error
                missing_markscheme_images = [
                    image for image in markscheme_images if not (ROOT / "site" / image).is_file()
                ]
                if missing_markscheme_images:
                    raise ValueError(f"{qid}: missing official markscheme images {missing_markscheme_images}")
                official_markscheme = {"pages": markscheme_pages, "images": markscheme_images}
            else:
                official_markscheme = None
            accessible_text = raw.get("accessible_text", "").strip()
            if len(accessible_text) < 30:
                raise ValueError(f"{qid}: accessible_text is missing or implausibly short")
            marks = int(raw["marks"])
            pages = raw["pages"] if isinstance(raw["pages"], list) else [raw["pages"]]
            pages = [int(page) for page in pages]
            display_pages_raw = raw.get("display_pages", pages)
            display_pages = [int(page) for page in display_pages_raw]
            if not display_pages or not set(display_pages).issubset(pages):
                raise ValueError(f"{qid}: display_pages must be a non-empty subset of pages")
            question_images = (
                [f"questions/{qid}-page-{page}.webp" for page in display_pages]
                if paper.get("host_question_images", True)
                else []
            )
            missing_images = [image for image in question_images if not (ROOT / "site" / image).is_file()]
            if missing_images:
                raise ValueError(f"{qid}: missing generated question images {missing_images}")
            questions.append({
                "id": qid,
                "number": int(raw["number"]),
                "paper": int(paper["paper"]),
                "zone": str(paper["zone"]),
                "year": int(paper["year"]),
                "session": session,
                "subject": subject,
                "pages": pages,
                "displayPages": display_pages,
                "questionImages": question_images,
                "imageStatus": raw.get("image_status", "original"),
                "marks": marks,
                "summary": raw["summary"].strip(),
                "accessibleText": accessible_text,
                "labels": labels,
                "solution": raw["solution"].strip(),
                "independentSolution": raw["solution"].strip(),
                "officialMarkscheme": official_markscheme,
                "markschemeUrl": paper.get("markscheme_url") or paper.get("alternate_markscheme_url"),
                "sourceUrl": raw.get("source_url", paper["source_url"]),
                "pdfUrl": raw.get("pdf_url", paper["pdf_url"]),
                "viewerAvailable": bool(paper.get("viewer_available", True)),
                "solutionStatus": paper["solution_status"],
            })
            count += 1
        paper_summaries.append({**paper, "subject": subject, "question_count": count})

    questions.sort(key=lambda q: (-q["year"], q["session"], q["paper"], q["zone"], q["number"]))
    output = {"version": 1, "papers": paper_summaries, "questions": questions}
    target = ROOT / "site" / "data" / "questions.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions)} questions from {len(paper_summaries)} papers to {target}")


if __name__ == "__main__":
    main()
