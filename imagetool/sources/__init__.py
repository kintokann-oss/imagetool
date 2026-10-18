"""Source Adapter registry. Adding a website = adding an adapter here."""

from __future__ import annotations

from imagetool.config import Settings
from imagetool.domain.ports import SourceAdapter
from imagetool.sources.mock_marketplace import MockMarketplaceAdapter


def build_source_adapters(settings: Settings) -> dict[str, SourceAdapter]:
    adapters: list[SourceAdapter] = [MockMarketplaceAdapter(settings.fixtures_dir)]
    return {adapter.name: adapter for adapter in adapters}
