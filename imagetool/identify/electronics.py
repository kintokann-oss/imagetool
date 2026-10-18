"""Electronics identification: product type, brand, model."""

from __future__ import annotations

import re

from imagetool.domain.models import ImageEvidence, ItemIdentity, Listing
from imagetool.identify.common import find_known
from imagetool.text.normalize import contains_term, normalize

BRANDS = [
    "Sony", "Samsung", "Apple", "LG", "Philips", "Xiaomi", "Huawei", "Nintendo", "Microsoft",
    "Bose", "JBL", "Canon", "Nikon", "Lenovo", "HP", "Dell", "Asus", "Acer", "Panasonic",
    "Technics", "Pioneer", "Sennheiser", "Garmin", "Google", "OnePlus", "Motorola", "Nokia",
]
# Product lines that imply the brand when the brand itself is not written.
PRODUCT_LINES = {
    "iPhone": "Apple", "iPad": "Apple", "MacBook": "Apple", "AirPods": "Apple",
    "PlayStation": "Sony", "PS4": "Sony", "PS5": "Sony", "Galaxy": "Samsung",
    "Xbox": "Microsoft", "Switch": "Nintendo", "ThinkPad": "Lenovo", "Pixel": "Google",
}
PRODUCT_TYPES: dict[str, list[str]] = {
    "headphones": ["headphones", "earbuds", "airpods", "ακουστικά", "слушалки", "slušalice", "căști", "casti", "kõrvaklapid"],
    "phone": ["iphone", "galaxy", "smartphone", "phone", "κινητό", "τηλέφωνο", "телефон", "смартфон", "mobitel", "telefon", "nutitelefon"],
    "console": ["playstation", "ps4", "ps5", "xbox", "nintendo switch", "console", "κονσόλα", "конзола", "konzola", "consolă", "consola", "konsool"],
    "laptop": ["laptop", "macbook", "thinkpad", "notebook", "λάπτοπ", "лаптоп", "sülearvuti"],
    "tablet": ["ipad", "tablet", "таблет"],
    "camera": ["camera", "κάμερα", "камера", "фотоапарат", "fotoaparat", "kamera", "kaamera"],
    "speaker": ["speaker", "ηχείο", "тонколона", "zvučnik", "boxă", "boxa", "kõlar"],
    "tv": ["tv", "television", "τηλεόραση", "телевизор", "televizor", "teler"],
    "turntable": ["turntable", "πικάπ", "грамофон", "gramofon", "pick-up", "plaadimängija"],
    "amplifier": ["amplifier", "ενισχυτής", "усилвател", "pojačalo", "amplificator", "võimendi"],
}
# A model token contains a digit (WH-1000XM4, S21, 1000D) or is a known line word followed by one.
_MODEL_TOKEN = re.compile(r"^(?=.*\d)[A-Za-z0-9][A-Za-z0-9\-+/]{0,19}$")
_VARIANT = re.compile(r"^(?:Slim|Pro|Max|Plus|Mini|Lite|Ultra|OLED|Air|SE|FE)$", re.IGNORECASE)
_STOP = {"gb", "tb", "mah", "w", "hz", "inch", "eur", "lei", "лв", "kn"}


def _model_after(anchor: str, title: str, is_line: bool) -> str | None:
    words = title.split()
    lowered = [word.casefold().strip(",.;:()") for word in words]
    if anchor.casefold() not in lowered:
        return None
    start = lowered.index(anchor.casefold()) + 1
    following = words[start].strip(",.;:()") if start < len(words) else ""
    if _MODEL_TOKEN.match(anchor) or (is_line and _VARIANT.match(following)):
        # The anchor already names the model ("PS4", "Switch"): keep a variant word ("Slim", "OLED").
        return following if _VARIANT.match(following) else ""
    picked: list[str] = []
    for word in words[start : start + 4]:
        token = word.strip(",.;:()")
        if token.casefold() in _STOP or re.fullmatch(r"\d+(gb|tb|mah|w|hz)", token.casefold()):
            break
        picked.append(token)
        if _MODEL_TOKEN.match(token):
            return " ".join(picked)
    return None


def identify_electronics(listing: Listing, images: list[ImageEvidence], _catalog: object) -> ItemIdentity:
    identity = ItemIdentity()
    ocr_text = "\n".join(image.ocr.text for image in images)
    text = f"{listing.title}\n{listing.description}\n{ocr_text}"
    normalized = normalize(text)

    for product_type, terms in PRODUCT_TYPES.items():
        if any(contains_term(normalized, normalize(term)) for term in terms):
            identity.set("product_type", product_type, 0.7, "dictionary")
            break

    brand = find_known(text, BRANDS)
    line = find_known(text, list(PRODUCT_LINES))
    if brand:
        identity.set("brand", brand, 0.85, "dictionary")
    elif line:
        identity.set("brand", PRODUCT_LINES[line], 0.75, "product_line")

    for anchor in (line, brand):
        model = _model_after(anchor, listing.title, anchor == line) if anchor else None
        if model is None:
            continue
        model_value = f"{line} {model}".strip() if anchor == line else model
        if model_value:
            identity.set("model", model_value, 0.7, "title")
            break
    return identity
