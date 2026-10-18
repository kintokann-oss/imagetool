from imagetool.classify import classify_listing
from imagetool.classify.category import decide_category
from imagetool.classify.keywords import default_dictionary
from imagetool.domain.models import Category, ImageEvidence, Listing, OcrResult, RunSpec, Signal, SignalKind


def _listing(title: str, description: str = "") -> Listing:
    return Listing(source="test", source_listing_id="1", title=title, description=description)


def test_title_keyword_in_each_language_wins(catalog) -> None:
    # Arrange
    titles = {
        "Δίσκος βινυλίου Beatles": Category.VINYL,
        "Настолна игра за деца": Category.BOARD_GAME,
        "Mobitel Samsung Galaxy S10": Category.ELECTRONICS,
        "Yugioh karta rijetka": Category.YUGIOH_CARD,
        "Lauamäng perele": Category.BOARD_GAME,
        "Disc de vinil Electrecord": Category.VINYL,
    }

    for title, expected in titles.items():
        # Act
        result = classify_listing(_listing(title), [], RunSpec(), default_dictionary(), catalog)

        # Assert
        assert result.category == expected, title


def test_below_min_confidence_is_unknown(catalog) -> None:
    # Arrange: only a weak description hit
    listing = _listing("Selling this", "comes with a record of purchase")

    # Act
    result = classify_listing(listing, [], RunSpec(min_confidence=0.6), default_dictionary(), catalog)

    # Assert
    assert result.category == Category.UNKNOWN
    assert result.signals, "evidence is kept even when the answer is unknown"


def test_category_outside_run_spec_never_wins(catalog) -> None:
    # Arrange
    listing = _listing("Catan board game", "Kosmos, complete")

    # Act
    result = classify_listing(listing, [], RunSpec(categories=[Category.VINYL]), default_dictionary(), catalog)

    # Assert
    assert result.category == Category.UNKNOWN


def test_ocr_set_code_alone_identifies_a_card(catalog) -> None:
    # Arrange: title says nothing useful, the photo shows the set code
    listing = _listing("Κάρτα")
    image = ImageEvidence(source_url="x", ocr=OcrResult(text="MRD-EN138", lines=["MRD-EN138"]))

    # Act
    result = classify_listing(listing, [image], RunSpec(), default_dictionary(), catalog)

    # Assert
    assert result.category == Category.YUGIOH_CARD
    assert result.identity.value("card_name") == "Mirror Force"


def test_conflicting_evidence_lowers_confidence() -> None:
    # Arrange
    agreeing = [Signal(kind=SignalKind.TITLE_KEYWORD, category=Category.VINYL, weight=1.0, detail="a")] * 2
    conflicting = agreeing + [Signal(kind=SignalKind.IMAGE_LABEL, category=Category.ELECTRONICS, weight=0.9, detail="b")]

    # Act
    _, confident = decide_category(agreeing, list(Category), 0.0)
    _, less_confident = decide_category(conflicting, list(Category), 0.0)

    # Assert
    assert less_confident < confident
