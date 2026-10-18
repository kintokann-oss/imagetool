"""Weighted vote of Signals → Category + confidence."""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable

from imagetool.domain.models import Category, Signal


def decide_category(
    signals: list[Signal],
    allowed: Iterable[Category],
    min_confidence: float,
) -> tuple[Category, float]:
    """Confidence = evidence strength (1 - e^-total) × share of the winning category.

    One title keyword alone gives 0.63; title + OCR agreeing gives ~0.83; conflicting
    evidence lowers the share. Categories outside `allowed` never win (Run Spec restriction).
    """
    allowed_set = set(allowed)
    totals: dict[Category, float] = defaultdict(float)
    for signal in signals:
        totals[signal.category] += signal.weight

    overall = sum(totals.values())
    candidates = {category: total for category, total in totals.items() if category in allowed_set}
    if not candidates or overall <= 0:
        return Category.UNKNOWN, 0.0

    winner = max(candidates, key=lambda category: candidates[category])
    strength = 1 - math.exp(-candidates[winner])
    share = candidates[winner] / overall
    confidence = round(strength * share, 3)
    if confidence < min_confidence:
        return Category.UNKNOWN, confidence
    return winner, confidence
