from imagetool.domain.models import ImageEvidence, Listing, OcrResult
from imagetool.identify.yugioh import find_edition, find_set_code, identify_yugioh


def _identify(catalog, title: str, ocr: str = ""):
    listing = Listing(source="test", source_listing_id="1", title=title)
    images = [ImageEvidence(source_url="x", ocr=OcrResult(text=ocr, lines=ocr.splitlines()))] if ocr else []
    return identify_yugioh(listing, images, catalog).as_values()


def test_set_code_with_ocr_digit_noise() -> None:
    # Act
    result = find_set_code("P0t of Greed\nLOB-EN1l9")

    # Assert
    assert result == ("LOB", "EN", "119")


def test_model_numbers_are_not_set_codes() -> None:
    # Act / Assert
    assert find_set_code("Sony WH-1000XM4") is None


def test_set_code_gives_name_and_set(catalog) -> None:
    # Act
    result = _identify(catalog, "Yugioh card", "BLUE-EYES WHITE DRAGON\nLOB-EN001")

    # Assert
    assert result["card_name"] == "Blue-Eyes White Dragon"
    assert result["set_name"] == "Legend of Blue Eyes White Dragon"
    assert result["print_language"] == "en"


def test_german_print_matches_by_set_code_and_translated_name(catalog) -> None:
    # Act
    result = _identify(catalog, "Карта", "Dunkler Magier\nLOB-DE005")

    # Assert
    assert result["card_name"] == "Dark Magician"
    assert result["print_language"] == "de"


def test_name_only_uses_fuzzy_catalog_match(catalog) -> None:
    # Arrange: OCR misread the name and no set code is visible
    # Act
    result = _identify(catalog, "Yugioh kaart", "Red-Eyes Black Dragcn")

    # Assert
    assert result["card_name"] == "Red-Eyes Black Dragon"
    assert "set_name" not in result


def test_translated_name_in_listing_title(catalog) -> None:
    # Act
    result = _identify(catalog, "Carte Yu-Gi-Oh Mago Nero")

    # Assert
    assert result["card_name"] == "Dark Magician"


def test_unknown_print_still_gives_set_name_from_prefix(catalog) -> None:
    # Act
    result = _identify(catalog, "Yugioh", "PSV-EN088")

    # Assert
    assert result["set_name"] == "Pharaoh's Servant"
    assert "card_name" not in result


def test_name_disagreeing_with_set_code_is_reported(catalog) -> None:
    # Act
    result = _identify(catalog, "Yugioh Mirror Force", "MIRROR FORCE\nLOB-EN001")

    # Assert
    assert result["card_name"] == "Blue-Eyes White Dragon"
    assert result["name_read_as"] == "Mirror Force"


def test_editions_in_several_languages() -> None:
    # Act / Assert
    assert find_edition("1. Auflage") == "1st edition"
    assert find_edition("Κάρτα 1η έκδοση") == "1st edition"
    assert find_edition("Unlimited") == "unlimited"
