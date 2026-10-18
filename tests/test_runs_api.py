import json

from PIL import Image


def _start(client, **spec) -> dict:
    response = client.post("/runs", json=spec)
    assert response.status_code == 202, response.text
    return client.get(f"/runs/{response.json()['id']}").json()


def test_health(client) -> None:
    # Act
    response = client.get("/health")

    # Assert
    assert response.json() == {"status": "ok"}


def test_run_classifies_all_fixture_listings(client) -> None:
    # Act
    run = _start(client)

    # Assert
    assert run["status"] == "done"
    assert run["fetched"] == 28
    assert run["classified"] + run["unknown"] == 28
    assert run["failed"] == 0


def test_classifications_filter_by_category(client) -> None:
    # Arrange
    run = _start(client)

    # Act
    rows = client.get(f"/runs/{run['id']}/classifications", params={"category": "yugioh_card"}).json()

    # Assert
    assert rows and all(row["category"] == "yugioh_card" for row in rows)
    blue_eyes = next(row for row in rows if row["title"].startswith("Blue Eyes"))
    assert blue_eyes["identity"]["card_name"]["value"] == "Blue-Eyes White Dragon"
    assert blue_eyes["identity"]["set_name"]["value"] == "Legend of Blue Eyes White Dragon"


def test_second_run_skips_unchanged_listings(client) -> None:
    # Arrange
    _start(client)

    # Act
    second = _start(client)

    # Assert
    assert second["skipped_unchanged"] == 28
    assert second["classified"] == 0


def test_price_change_triggers_reclassification(client, fixtures_dir) -> None:
    # Arrange
    _start(client)
    path = fixtures_dir / "mock_marketplace" / "listings.json"
    data = json.loads(path.read_text("utf-8"))
    data["listings"][0]["price"] = 99
    path.write_text(json.dumps(data, ensure_ascii=False), "utf-8")

    # Act
    second = _start(client)

    # Assert
    assert second["skipped_unchanged"] == 27
    assert second["classified"] == 1


def test_listing_detail_keeps_small_image_and_ocr_text(client) -> None:
    # Arrange
    run = _start(client, query="Mirror Force")
    row = client.get(f"/runs/{run['id']}/classifications").json()[0]

    # Act
    listing = client.get(f"/listings/{row['listing_id']}").json()

    # Assert
    image = listing["images"][0]
    assert "MRD-EN138" in image["ocr_text"]
    with Image.open(image["thumbnail_path"]) as thumbnail:
        assert max(thumbnail.size) <= 512
    assert listing["classification"]["signals"]
    assert listing["prices"][0]["price"] == 25


def test_unknown_source_is_rejected(client) -> None:
    # Act
    response = client.post("/runs", json={"source": "nope"})

    # Assert
    assert response.status_code == 400


def test_missing_run_and_listing_return_404(client) -> None:
    # Act / Assert
    assert client.get("/runs/999").status_code == 404
    assert client.get("/runs/999/classifications").status_code == 404
    assert client.get("/listings/999").status_code == 404
