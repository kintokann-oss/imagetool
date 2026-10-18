"""Render placeholder images for the mock marketplace fixtures.

Each image shows its fixture OCR text (Latin only, the default font has no Greek/Cyrillic)
on a background coloured by expected category, so a real OCR engine has something to read.
Run from apps/imagetool:  python scripts/make_fixture_images.py
"""

from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent / "fixtures" / "mock_marketplace"
COLOURS = {
    "yugioh_card": (196, 160, 90),
    "vinyl": (30, 30, 30),
    "board_game": (60, 120, 70),
    "electronics": (70, 90, 140),
    "unknown": (150, 150, 150),
}


def render(text: str, colour: tuple[int, int, int], path: Path) -> None:
    image = Image.new("RGB", (800, 600), colour)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default(size=40)
    printable = "\n".join(line for line in text.splitlines() if line.isascii())
    draw.multiline_text((40, 40), printable, fill=(255, 255, 255), font=font, spacing=16)
    image.save(path, optimize=True)


def main() -> None:
    listings = json.loads((ROOT / "listings.json").read_text("utf-8"))["listings"]
    (ROOT / "images").mkdir(exist_ok=True)
    for listing in listings:
        colour = COLOURS[listing["expected"]["category"]]
        for image in listing["images"]:
            render(image["ocr_text"], colour, ROOT / "images" / image["file"])
    print(f"rendered images for {len(listings)} listings")


if __name__ == "__main__":
    main()
