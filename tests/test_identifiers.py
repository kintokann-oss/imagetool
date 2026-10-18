from imagetool.domain.models import Listing
from imagetool.identify.board_game import identify_board_game
from imagetool.identify.electronics import identify_electronics
from imagetool.identify.vinyl import identify_vinyl


def _listing(title: str, description: str = "") -> Listing:
    return Listing(source="test", source_listing_id="1", title=title, description=description)


def test_vinyl_artist_with_hyphen_is_not_split() -> None:
    # Act
    result = identify_vinyl(_listing("Jay-Z - The Black Album 2LP 2003"), [], None).as_values()

    # Assert
    assert result["artist"] == "Jay-Z"
    assert result["title"] == "The Black Album"
    assert result["format"] == "2LP"
    assert result["year"] == "2003"


def test_vinyl_regional_label_in_cyrillic() -> None:
    # Act
    result = identify_vinyl(_listing("Плоча", "Издание на Балкантон"), [], None).as_values()

    # Assert
    assert result["label"] == "Balkanton"


def test_board_game_local_name_maps_to_canonical() -> None:
    # Act
    result = identify_board_game(_listing("Επιτραπέζιο Κατάν", "Kaissa"), [], None).as_values()

    # Assert
    assert result["title"] == "Catan"
    assert result["publisher"] == "Kaissa"


def test_electronics_brand_from_product_line() -> None:
    # Act
    result = identify_electronics(_listing("Galaxy S21 128GB"), [], None).as_values()

    # Assert
    assert result["brand"] == "Samsung"
    assert result["model"] == "Galaxy S21"
    assert result["product_type"] == "phone"


def test_electronics_model_stops_at_storage_size() -> None:
    # Act
    result = identify_electronics(_listing("Lenovo ThinkPad T480 16GB"), [], None).as_values()

    # Assert
    assert result["brand"] == "Lenovo"
    assert result["model"] == "ThinkPad T480"


def test_electronics_model_from_line_and_variant() -> None:
    # Act
    result = identify_electronics(_listing("Nintendo Switch OLED white"), [], None).as_values()

    # Assert
    assert result["model"] == "Switch OLED"
