#!/usr/bin/env python3
"""Merge reviewed paper JSON into the static site's question bank."""
from __future__ import annotations

import json
from pathlib import Path

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

        count = 0
        for raw in payload["questions"]:
            qid = raw["id"]
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
                "pages": pages,
                "displayPages": display_pages,
                "questionImages": question_images,
                "marks": marks,
                "summary": raw["summary"].strip(),
                "accessibleText": accessible_text,
                "labels": labels,
                "solution": raw["solution"].strip(),
                "sourceUrl": paper["source_url"],
                "pdfUrl": paper["pdf_url"],
                "viewerAvailable": bool(paper.get("viewer_available", True)),
                "solutionStatus": paper["solution_status"],
            })
            count += 1
        paper_summaries.append({**paper, "question_count": count})

    questions.sort(key=lambda q: (-q["year"], q["session"], q["paper"], q["zone"], q["number"]))
    output = {"version": 1, "papers": paper_summaries, "questions": questions}
    target = ROOT / "site" / "data" / "questions.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(questions)} questions from {len(paper_summaries)} papers to {target}")


if __name__ == "__main__":
    main()
