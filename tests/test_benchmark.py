from imagetool.benchmark import PASS_BAR, run_benchmark
from imagetool.classify.keywords import default_dictionary
from imagetool.engines.fixture import FixtureImageClassifier, FixtureOcrEngine
from imagetool.sources.mock_marketplace import MockMarketplaceAdapter


def test_fixture_benchmark_meets_pass_bar(fixtures_dir, catalog) -> None:
    # Act
    report = run_benchmark(
        MockMarketplaceAdapter(fixtures_dir),
        FixtureOcrEngine(fixtures_dir),
        FixtureImageClassifier(fixtures_dir),
        default_dictionary(),
        catalog,
    )

    # Assert
    assert report.category_accuracy >= PASS_BAR, report.summary()
    assert report.card_accuracy >= PASS_BAR, report.summary()
