from datetime import date

import pytest

from imagetool.domain.models import PriceRange, RunSpec
from imagetool.sources.mock_marketplace import MockMarketplaceAdapter


def test_filters_by_country_price_and_date(fixtures_dir) -> None:
    # Arrange
    adapter = MockMarketplaceAdapter(fixtures_dir)
    spec = RunSpec(countries=["GR"], price=PriceRange(max=100), posted_after=date(2026, 10, 3))

    # Act
    listings = list(adapter.fetch(spec))

    # Assert
    assert listings
    assert all(l.country == "GR" and l.price <= 100 and l.posted_at >= date(2026, 10, 3) for l in listings)


def test_query_matches_and_newest_first(fixtures_dir) -> None:
    # Arrange
    adapter = MockMarketplaceAdapter(fixtures_dir)

    # Act
    listings = list(adapter.fetch(RunSpec(query="yu-gi-oh")))

    # Assert
    assert len(listings) >= 4
    dates = [listing.posted_at for listing in listings]
    assert dates == sorted(dates, reverse=True)


def test_image_urls_cannot_escape_fixtures(fixtures_dir) -> None:
    # Arrange
    adapter = MockMarketplaceAdapter(fixtures_dir)

    # Act / Assert
    with pytest.raises(ValueError):
        adapter.fetch_image("mock://../../etc/passwd")
