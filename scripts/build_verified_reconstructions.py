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

def build_page_12() -> Image.Image:
    image = Image.new("RGB", (WIDTH, 1980), "white")
    draw = ImageDraw.Draw(image)
    return image.crop((0, 0, WIDTH, min(1980, 200)))

def main() -> None:
    OUTPUT.mkdir(parents=True, exist_ok=True)

if __name__ == "__main__":
    main()
