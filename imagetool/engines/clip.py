"""CLIP zero-shot image classifier (optional dependency: torch + open_clip_torch).

Uses CUDA when available (RTX 3050, D13) and falls back to CPU. Model name format:
"<architecture>/<pretrained tag>", e.g. "ViT-B-32/laion2b_s34b_b79k" (fits easily in 4 GB VRAM).
"""

from __future__ import annotations

import io
from collections.abc import Mapping

from imagetool.domain.models import KNOWN_CATEGORIES, Category

PROMPTS: dict[Category, list[str]] = {
    Category.VINYL: ["a photo of a vinyl record", "a photo of a vinyl record sleeve", "a photo of an LP album cover"],
    Category.YUGIOH_CARD: ["a photo of a Yu-Gi-Oh trading card", "a photo of a collectible trading card"],
    Category.BOARD_GAME: ["a photo of a board game box", "a photo of board game pieces on a table"],
    Category.ELECTRONICS: ["a photo of an electronic device", "a photo of a smartphone, headphones, game console or laptop"],
    Category.UNKNOWN: ["a photo of furniture", "a photo of clothes", "a photo of a bicycle", "a photo of household items"],
}


class ClipImageClassifier:
    def __init__(self, model: str) -> None:
        import open_clip  # imported lazily: optional dependency
        import torch

        architecture, pretrained = model.split("/", 1)
        self._torch = torch
        self._device = "cuda" if torch.cuda.is_available() else "cpu"
        self._model, _, self._preprocess = open_clip.create_model_and_transforms(architecture, pretrained=pretrained)
        self._model = self._model.to(self._device).eval()
        if self._device == "cuda":
            self._model = self._model.half()
        tokenizer = open_clip.get_tokenizer(architecture)

        self._labels: list[Category] = []
        prompts: list[str] = []
        for category, texts in PROMPTS.items():
            self._labels += [category] * len(texts)
            prompts += texts
        with torch.no_grad():
            features = self._model.encode_text(tokenizer(prompts).to(self._device))
            self._text_features = features / features.norm(dim=-1, keepdim=True)

    def score(self, image: bytes, image_url: str) -> Mapping[Category, float]:
        from PIL import Image

        torch = self._torch
        with Image.open(io.BytesIO(image)) as picture:
            tensor = self._preprocess(picture.convert("RGB")).unsqueeze(0).to(self._device)
        if self._device == "cuda":
            tensor = tensor.half()
        with torch.no_grad():
            features = self._model.encode_image(tensor)
            features = features / features.norm(dim=-1, keepdim=True)
            probabilities = (100.0 * features @ self._text_features.T).softmax(dim=-1)[0].float().tolist()

        scores: dict[Category, float] = {}
        for label, probability in zip(self._labels, probabilities):
            scores[label] = scores.get(label, 0.0) + probability
        return {category: round(scores.get(category, 0.0), 4) for category in (*KNOWN_CATEGORIES, Category.UNKNOWN)}
