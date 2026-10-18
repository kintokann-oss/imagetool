from imagetool.catalog.ygo import SqliteCardCatalog, load_cardinfo, split_set_code
from imagetool.db import connect, init_db


def test_split_set_code_variants() -> None:
    # Act / Assert
    assert split_set_code("LOB-EN001") == ("LOB", "001")
    assert split_set_code("LOB-001") == ("LOB", "001")
    assert split_set_code("SDK-I001") == ("SDK", "001")
    assert split_set_code("garbage") is None


def test_loader_keeps_translations_for_known_cards_only() -> None:
    # Arrange
    connection = connect(":memory:")
    init_db(connection)
    load_cardinfo(connection, {"data": [{"id": 1, "name": "Kuriboh", "card_sets": [{"set_code": "MRD-EN071", "set_name": "Metal Raiders", "set_rarity": "Common"}]}]})

    # Act
    load_cardinfo(connection, {"data": [{"id": 1, "name": "Kuriboh"}, {"id": 2, "name": "Unbekannt"}]}, "de")
    catalog = SqliteCardCatalog(connection)

    # Assert
    assert catalog.find_print("MRD", "071").card_name == "Kuriboh"
    assert connection.execute("SELECT COUNT(*) FROM ygo_card_names WHERE language = 'de'").fetchone()[0] == 1


def test_reloading_english_replaces_prints() -> None:
    # Arrange
    connection = connect(":memory:")
    init_db(connection)
    card = {"id": 1, "name": "Kuriboh", "card_sets": [{"set_code": "MRD-EN071", "set_name": "Metal Raiders"}]}
    load_cardinfo(connection, {"data": [card]})

    # Act
    load_cardinfo(connection, {"data": [card]})

    # Assert
    assert connection.execute("SELECT COUNT(*) FROM ygo_prints").fetchone()[0] == 1
