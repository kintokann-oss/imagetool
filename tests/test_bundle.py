import pytest

from imagetool.classify.bundle import detect_bundle


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Колекция 50 карти Yu-Gi-Oh", (True, 50)),
        ("Collection of 30 vinyl records", (True, 30)),
        ("PS4 Slim 1TB + 3 igre", (True, 3)),
        ("Συλλογή καρτών yugioh", (True, None)),
        ("Pink Floyd - The Wall 2LP", (False, None)),
        ("Samsung TV 2x HDMI", (False, None)),
        ("Blue-Eyes White Dragon LOB-EN001", (False, None)),
    ],
)
def test_detect_bundle(title: str, expected: tuple[bool, int | None]) -> None:
    # Act
    result = detect_bundle(title, "")

    # Assert
    assert result == expected
