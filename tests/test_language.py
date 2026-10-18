import pytest

from imagetool.text.language import detect_language, ocr_languages


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Πωλείται δίσκος βινυλίου", "el"),
        ("Продавам грамофонна плоча", "bg"),
        ("Prodajem gramofonsku ploču, očuvana", "hr"),
        ("Vând disc de vinil, stare foarte bună", "ro"),
        ("Müüa vinüülplaat, väga heas korras", "et"),
        ("Selling vinyl record in good condition", "en"),
        ("", "en"),
    ],
)
def test_detect_language(text: str, expected: str) -> None:
    # Arrange / Act
    result = detect_language(text)

    # Assert
    assert result == expected


def test_ocr_languages_always_include_english() -> None:
    # Act
    codes = ocr_languages("bg")

    # Assert
    assert codes == ["bul", "eng"]
