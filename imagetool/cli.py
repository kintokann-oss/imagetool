"""Command line:  python -m imagetool.cli {run,benchmark,catalog} ..."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

import yaml

from imagetool.catalog.refresh import load_from_directory, refresh_from_api
from imagetool.catalog.ygo import SqliteCardCatalog
from imagetool.classify.keywords import default_dictionary
from imagetool.config import load_settings
from imagetool.container import build_container
from imagetool.db import connect, init_db
from imagetool.domain.models import RunSpec
from imagetool.engines import build_image_classifier, build_ocr_engine
from imagetool.services import repository
from imagetool.sources.mock_marketplace import MockMarketplaceAdapter


def _run(args: argparse.Namespace) -> int:
    spec = RunSpec.model_validate(yaml.safe_load(Path(args.spec).read_text("utf-8")) or {})
    container = build_container(load_settings())
    run_id = container.run_service.create_run(spec)
    container.run_service.execute(run_id)
    connection = container.connect()
    run = repository.get_run(connection, run_id)
    print(json.dumps(run, indent=2, ensure_ascii=False))
    for row in repository.list_classifications(connection, run_id, None):
        identity = ", ".join(f"{name}={field['value']}" for name, field in row["identity"].items())
        bundle = f" bundle×{row['estimated_item_count'] or '?'}" if row["is_bundle"] else ""
        print(f"[{row['category']:<12} {row['confidence']:.2f}{bundle}] {row['title']}  ->  {identity}")
    return 0 if run and run["status"] == "done" else 1


def _benchmark(args: argparse.Namespace) -> int:
    from imagetool.benchmark import run_benchmark

    settings = load_settings()
    connection = connect(":memory:")
    init_db(connection)
    load_from_directory(connection, settings.fixtures_dir / "ygoprodeck_sample")
    report = run_benchmark(
        MockMarketplaceAdapter(settings.fixtures_dir),
        build_ocr_engine(settings),
        build_image_classifier(settings),
        default_dictionary(),
        SqliteCardCatalog(connection),
        min_confidence=args.min_confidence,
    )
    print(report.summary())
    return 0 if report.passed else 1


def _catalog(args: argparse.Namespace) -> int:
    settings = load_settings()
    connection = connect(settings.database_path)
    init_db(connection)
    if args.action == "refresh":
        counts = refresh_from_api(connection)
    else:
        counts = load_from_directory(connection, settings.fixtures_dir / "ygoprodeck_sample")
    print(json.dumps(counts))
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(prog="imagetool")
    commands = parser.add_subparsers(dest="command", required=True)

    run = commands.add_parser("run", help="execute a Run from a Run Spec YAML/JSON file")
    run.add_argument("spec")
    run.set_defaults(handler=_run)

    benchmark = commands.add_parser("benchmark", help="score the pipeline on the mock fixtures")
    benchmark.add_argument("--min-confidence", type=float, default=0.6)
    benchmark.set_defaults(handler=_benchmark)

    catalog = commands.add_parser("catalog", help="manage the Yu-Gi-Oh card catalog")
    catalog.add_argument("action", choices=["refresh", "load-sample"])
    catalog.set_defaults(handler=_catalog)

    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    sys.exit(main())
