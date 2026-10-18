"""Tesseract OCR engine (optional dependency: `pip install pytesseract` + the Tesseract binary).

On Windows install Tesseract from the UB Mannheim build and either put it on PATH or set
IMAGETOOL_TESSERACT_CMD to tesseract.exe. Needed language packs: ell bul hrv ron est eng,
plus deu fra ita spa por for card prints.
"""

from __future__ import annotations

import io

from imagetool.domain.models import OcrResult


class TesseractOcrEngine:
    def __init__(self, tesseract_cmd: str | None = None) -> None:
        import pytesseract  # imported lazily: optional dependency

        if tesseract_cmd:
            pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
        self._pytesseract = pytesseract
        self._installed = set(pytesseract.get_languages(config=""))

    def read(self, image: bytes, languages: list[str], image_url: str) -> OcrResult:
        from PIL import Image

        usable = [code for code in languages if code in self._installed] or ["eng"]
        with Image.open(io.BytesIO(image)) as picture:
            text = self._pytesseract.image_to_string(picture.convert("RGB"), lang="+".join(usable))
        return OcrResult(text=text, lines=[line.strip() for line in text.splitlines() if line.strip()])
