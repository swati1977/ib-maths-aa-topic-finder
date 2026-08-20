#!/usr/bin/env python3
"""Build clearly labelled visual reconstructions when original page scans are unavailable."""
from __future__ import annotations

from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "site" / "questions"
FONT = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
WIDTH = 1400
MARGIN = 90


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_BOLD if bold else FONT), size)


def lines_for(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if current and draw.textbbox((0, 0), candidate, font=face)[2] > width:
            lines.append(current)
            current = word
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def paragraph(draw: ImageDraw.ImageDraw, y: int, text: str, *, size: int = 30, bold: bool = False, gap: int = 18) -> int:
    face = font(size, bold=bold)
    for line in lines_for(draw, text, face, WIDTH - 2 * MARGIN):
        draw.text((MARGIN, y), line, fill="black", font=face)
        y += size + 11
    return y + gap


def table(draw: ImageDraw.ImageDraw, y: int, rows: list[list[str]], widths: list[int]) -> int:
    row_height = 74
    x0 = MARGIN
    for row_index, row in enumerate(rows):
        x = x0
        for value, cell_width in zip(row, widths):
            draw.rectangle((x, y, x + cell_width, y + row_height), outline="black", width=2)
            face = font(24, bold=row_index == 0)
            box = draw.textbbox((0, 0), value, font=face)
            draw.text((x + (cell_width - (box[2] - box[0])) / 2, y + 20), value, fill="black", font=face)
            x += cell_width
        y += row_height
    return y + 26


def page_header(draw: ImageDraw.ImageDraw, page: int) -> int:
    y = 54
    draw.text((MARGIN, y), "VERIFIED RECONSTRUCTION — ORIGINAL SCAN UNAVAILABLE", fill="#8a3b00", font=font(25, bold=True))
    draw.text((WIDTH - MARGIN - 190, y), f"Page {page}", fill="#555", font=font(22))
    return y + 62


def build_page_12() -> Image.Image:
    image = Image.new("RGB", (WIDTH, 1980), "white")
    draw = ImageDraw.Draw(image)
    y = page_header(draw, 12)
    y = paragraph(draw, y, "9. [Maximum mark: 15]", size=34, bold=True)
    y = paragraph(draw, y, "Jacinta has a bag of counters which are coloured either red, blue or yellow.")
    y = paragraph(draw, y, "The bag contains exactly 12 yellow counters. The number of red counters is the same as the number of blue counters.")
    y = paragraph(draw, y, "Jacinta plays a game where she takes 10 counters out of the bag, one at a time. She notes the colour of each counter and returns it to the bag before taking the next counter out of the bag.")
    y = paragraph(draw, y, "The probability that the first counter is yellow is 0.4.")
    y = paragraph(draw, y, "(a) Show that there are 9 red counters in the bag.  [2]")
    y = paragraph(draw, y, "(b) Find the probability that at least 6 of the 10 counters that Jacinta takes are yellow. Give your answer correct to five significant figures.  [3]")
    y = paragraph(draw, y, "Jacinta has to pay $5 to take part in the game. If she takes at least 6 counters of the same colour, she wins a prize. If she does not take at least 6 counters of the same colour, then she does not win a prize. There is a different prize for each colour, as shown below, where B ∈ ℕ.")
    y = table(draw, y, [
        ["Outcome", "≥6 red", "≥6 blue", "≥6 yellow"],
        ["Prize", "$40", "$B", "$10"],
    ], [280, 300, 300, 300])
    y = paragraph(draw, y, "Let X represent Jacinta's net gain in dollars when she plays once. For example, at least 6 red counters gives a net gain of $40 − $5 = $35.")
    y = table(draw, y, [
        ["x", "35", "B − 5", "A", "−5"],
        ["P(X = x)", "0.0473", "0.0473", "0.1662", "p"],
    ], [280, 225, 225, 225, 225])
    y = paragraph(draw, y, "(c) Write down the value of A.  [1]")
    y = paragraph(draw, y, "(d) (i) Use the probabilities in the table to find p.  (ii) Determine the smallest integer B for which Jacinta could expect a positive net gain.  [5]")
    return image.crop((0, 0, WIDTH, min(1980, y + 70)))


def build_page_13() -> Image.Image:
    image = Image.new("RGB", (WIDTH, 740), "white")
    draw = ImageDraw.Draw(image)
    y = page_header(draw, 13)
    y = paragraph(draw, y, "Question 9 continued", size=32, bold=True)
    y = paragraph(draw, y, "Jacinta wants to play the game until she wins a prize.")
    y = paragraph(draw, y, "(e) Find the minimum number of times Jacinta needs to play the game in order that the probability of winning at least one prize is greater than 0.99.  [4]")
    return image.crop((0, 0, WIDTH, y + 60))


def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for page_number, image in ((12, build_page_12()), (13, build_page_13())):
        target = OUTPUT / f"m26-math-aasl-p2-tza-q9-page-{page_number}.webp"
        image.save(target, "WEBP", quality=90, method=6)
        print(target, image.size, target.stat().st_size)


if __name__ == "__main__":
    main()
