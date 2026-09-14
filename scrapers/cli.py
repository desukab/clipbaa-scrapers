"""Pipeline CLI: run, match, history, export, list-sources, validate-config, scrape-asins."""
import argparse
import dataclasses
import logging
import os
import sys
import time
from pathlib import Path
from typing import List, Optional

from scrapers import sources  # noqa: F401  (registers built-ins)
from scrapers.config import Settings
from scrapers.errors import ConfigError, DependencyError, PipelineError, SourceError
from scrapers.io import atomic_write_json, ensure_dir, load_json, new_run_id, write_manifest
from scrapers.logging_setup import add_file_handler, setup_logging
from scrapers.metrics import RunMetrics
from scrapers.registry import get_source, list_sources


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="pipeline", description="Scrapling e-commerce pipeline")
    parser.add_argument("--env-file", default=None, help="Path to an .env file")
    parser.add_argument("--output-dir", default=None, help="Override OUTPUT_DIR")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Crawl all sources, match, and report")
    p_run.add_argument("--live", action="store_true")
    p_run.add_argument("--mock", action="store_true")
    p_run.add_argument("--sources", default=None, help="Comma-separated source names")
    p_run.add_argument("--max-products", type=int, default=None)
    p_run.add_argument("--allow-mock-fallback", action="store_true")
    p_run.set_defaults(func=_cmd_run)

    sub.add_parser("match", help="Run matching on existing raw data").set_defaults(func=_cmd_match)
    sub.add_parser("history", help="Show price history velocity/alerts").set_defaults(func=_cmd_history)
    sub.add_parser("list-sources", help="List registered sources").set_defaults(func=_cmd_list_sources)
    sub.add_parser("validate-config", help="Validate configuration and exit").set_defaults(func=_cmd_validate)

    p_export = sub.add_parser("export", help="Write reports and optional exports")
    p_export.add_argument("--sheets", action="store_true")
    p_export.add_argument("--webhook", action="store_true")
    p_export.set_defaults(func=_cmd_export)

    p_asins = sub.add_parser("scrape-asins", help="Scrape specific Amazon ASINs (live)")
    p_asins.add_argument("asins", nargs="+")
    p_asins.set_defaults(func=_cmd_scrape_asins)
    return parser


def _settings(args) -> Settings:
    settings = Settings.from_env(env_file=args.env_file)
    if getattr(args, "output_dir", None):
        settings = dataclasses.replace(settings, output_dir=args.output_dir)
    return settings


def _cmd_list_sources(args) -> int:
    for spec in list_sources():
        print(f"{spec.name:<10} {spec.title}  ({len(spec.mock_items)} mock items, out={spec.output_file})")
    return 0


def _cmd_validate(args) -> int:
    try:
        settings = _settings(args)
    except ConfigError as exc:
        print(f"invalid configuration: {exc}", file=sys.stderr)
        return 2
    print(f"configuration OK (log_level={settings.log_level}, log_format={settings.log_format}, "
          f"output_dir={settings.output_dir})")
    return 0


def _resolve_sources(names: List[str]) -> list:
    specs = []
    known = {spec.name for spec in list_sources()}
    for name in names:
        if name not in known:
            raise ConfigError(f"unknown source {name!r}; available: {', '.join(sorted(known))}")
        specs.append(get_source(name))
    return specs


def _crawl_source(spec, settings, mode, allow_mock_fallback, max_products, log):
    from scrapers.sources import base as base_mod

    if mode == "mock":
        return "mock", list(spec.mock_items), None
    if not base_mod.SPIDERS_OK:
        raise DependencyError(
            "Live scraping requires 'scrapling[fetchers]'. "
            "Install it on a glibc host (e.g. proot-Distro Ubuntu): "
            "pip install -e '.[fetchers]' && scrapling install"
        )
    try:
        kwargs = spec.build_spider_kwargs(settings)
        if max_products is not None:
            kwargs["max_products"] = max_products
        spider = spec.spider_cls(**kwargs)
        items = base_mod.run_spider(spider)
        return "ok", items, None
    except DependencyError:
        raise
    except SourceError as exc:
        log.warning("source %s failed: %s", spec.name, exc)
        if allow_mock_fallback:
            return "mock-fallback", list(spec.mock_items), "fallback after failure"
        return "failed", [], str(exc)


def _validate_and_count(items: list, source: str) -> tuple:
    from scrapers.schemas import validate_record

    kept = []
    dropped = 0
    for item in items:
        record = dict(item)
        record.setdefault("source", source)
        errors = validate_record(record)
        if errors:
            dropped += 1
            logging.getLogger("scrapers.cli").warning(
                "dropped invalid %s record (%s): %s",
                source,
                record.get("asin") or record.get("product_id") or record.get("sku"),
                errors,
            )
            continue
        kept.append(record)
    return kept, dropped


def run_pipeline(
    settings: Settings,
    mode: str,
    source_specs: list,
    allow_mock_fallback: bool,
    max_products: Optional[int],
) -> int:
    log = logging.getLogger("scrapers.cli")
    setup_logging(settings.log_level, settings.log_format)
    ensure_dir(settings.output_dir)
    run_id = new_run_id()
    log_dir = Path(settings.output_dir) / "runs" / run_id
    ensure_dir(log_dir)
    add_file_handler(str(log_dir / "run.log"))

    from scrapers.matching import history as history_mod
    from scrapers.matching.matcher import run_matching
    from scrapers.reporting.writer import write_all_outputs

    metrics = RunMetrics(mode=mode, started_at=run_id)
    raw_products: dict = {}
    total_invalid = 0

    for spec in source_specs:
        metric = metrics.for_source(spec.name)
        started = time.perf_counter()
        status, items, note = _crawl_source(spec, settings, mode, allow_mock_fallback, max_products, log)
        metric.status = status
        if status == "failed":
            metric.failed = 1
        else:
            items, dropped = _validate_and_count(items, spec.name) if items else (items, 0)
            total_invalid += dropped
            metric.scraped = len(items)
            metric.requested = len(items)
            path = os.path.join(settings.output_dir, spec.output_file)
            atomic_write_json(path, items)
            raw_products[spec.name] = items
            log.info("source %s done: status=%s items=%d%s", spec.name, status, len(items), f" ({note})" if note else "")
        metric.elapsed_ms = int((time.perf_counter() - started) * 1000)

    summary = run_matching(settings)
    writes = write_all_outputs(settings, summary)
    hist_path = history_mod.history_path(settings)
    rows = history_mod.collect_raw(raw_products, run_id)
    history_mod.append_history(hist_path, rows)
    all_rows = history_mod.read_lines(hist_path)
    velocity = history_mod.compute_velocity(all_rows)
    alerts = history_mod.compute_alerts(all_rows)

    metrics.finished_at = new_run_id()
    manifest = {
        "run_id": run_id,
        "mode": mode,
        "settings": settings.to_dict(redact=True),
        "metrics": metrics.to_dict(),
        "schema": {"invalid_records_dropped": total_invalid},
        "matching": {
            "marketplace_total": summary.marketplace_total,
            "candidates": len(summary.candidates),
            "winners": len(summary.winners),
            "near_misses": len(summary.near_misses),
            "high_opportunity": summary.high_opportunity,
        },
        "history": {"velocity": velocity, "alerts": alerts},
        "outputs": {key: str(value) for key, value in writes.items()},
        "history_file": hist_path,
    }
    manifest_path = write_manifest(settings.output_dir, run_id, manifest)
    _print_summary(summary, settings)
    log.info("pipeline run finished: run_dir=%s, manifest=%s, exit after mode=%s", run_id, manifest_path, mode)
    return 0 if mode == "mock" else metrics.exit_code()


def _print_summary(summary, settings):
    print("\n" + "=" * 70)
    print(f"MARKETPLACE PRODUCTS: {summary.marketplace_total}")
    print(f"SCORED CANDIDATES:    {len(summary.candidates)}")
    print(f"WINNERS:              {len(summary.winners)}")
    print(f"NEAR MISSES:          {len(summary.near_misses)}")
    print("=" * 70)
    winners = summary.winners
    listing = winners or sorted(summary.candidates, key=lambda m: m.opportunity_score, reverse=True)[:10]
    if not listing:
        print("No candidates matched. Adjust thresholds (MIN_CONFIDENCE, MIN_TICKET_PRICE, ...).")
        return
    for position, m in enumerate(listing, 1):
        tag = "" if m in winners else "  (below threshold)"
        print(
            f"{position:>2}. {m.marketplace_title[:52]:<52} | {m.deodap_sku:<12} | "
            f"₹{m.deodap_cost} -> ₹{m.marketplace_price} | ₹{m.absolute_margin_inr} | "
            f"{m.margin_percentage}% | conf {m.match_confidence:.0%} | opp {m.opportunity_score}{tag}"
        )


def _cmd_run(args) -> int:
    try:
        settings = _settings(args)
        mode = "mock" if args.mock else "live"
        names = [n.strip() for n in (args.sources or "").split(",") if n.strip()] if getattr(args, "sources", None) else None
        specs = _resolve_sources(names) if names else list(list_sources())
        return run_pipeline(settings, mode=mode, source_specs=specs,
                            allow_mock_fallback=args.allow_mock_fallback,
                            max_products=args.max_products)
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (ConfigError, PipelineError) as exc:
        print(f"pipeline error: {exc}", file=sys.stderr)
        return 2


def _cmd_match(args) -> int:
    from scrapers.matching.matcher import run_matching
    from scrapers.reporting.writer import write_all_outputs

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    summary = run_matching(settings)
    write_all_outputs(settings, summary)
    _print_summary(summary, settings)
    return 0


def _cmd_history(args) -> int:
    from scrapers.matching.history import compute_alerts, compute_velocity, history_path, read_lines

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    path = history_path(settings)
    if not os.path.exists(path):
        print("no history yet; run `pipeline run` first")
        return 0
    rows = read_lines(path)
    print(f"history file: {path} ({len(rows)} rows)")
    print(f"velocity: {compute_velocity(rows)}")
    print(f"alerts:   {compute_alerts(rows)}")
    return 0


def _cmd_export(args) -> int:
    from scrapers.matching.matcher import run_matching
    from scrapers.reporting.writer import write_all_outputs

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    summary = run_matching(settings)
    write_all_outputs(settings, summary)
    if args.sheets:
        from scrapers.reporting.sheets import export_to_sheets

        rows = [{
            "amazon_title": m.marketplace_title,
            "deodap_sku": m.deodap_sku,
            "cost": m.deodap_cost,
            "amazon_price": m.marketplace_price,
            "absolute_margin_inr": m.absolute_margin_inr,
            "margin_percentage": m.margin_percentage,
        } for m in summary.winners]
        export_to_sheets(settings, rows)
        print(f"sheets export complete ({len(summary.winners)} winners)")
    if args.webhook:
        from scrapers.reporting.webhook import build_payload, post_webhook

        if not settings.webhook_url or not settings.webhook_secret:
            print("webhook export requires WEBHOOK_URL and WEBHOOK_SECRET", file=sys.stderr)
            return 2
        payload = build_payload(summary.to_dict(), [m.__dict__ for m in summary.winners])
        code = post_webhook(settings.webhook_url, settings.webhook_secret, payload)
        print(f"webhook posted, status={code}")
    return 0


def _cmd_scrape_asins(args) -> int:
    from scrapers.sources.amazon import SEED_FILE, SeedAsinsSpider
    from scrapers.sources.base import run_spider

    settings = _settings(args)
    setup_logging(settings.log_level, settings.log_format)
    spider = SeedAsinsSpider(asins=args.asins, crawldir=settings.crawldir, max_products=0)
    items = run_spider(spider)
    atomic_write_json(os.path.join(settings.output_dir, "amazon_movers_raw.json"), items)
    seed = load_json(str(SEED_FILE), default={}) or {"amazon_movers": {"asins": []}}
    seed.setdefault("amazon_movers", {}).setdefault("asins", [])
    scraped = {str(i["asin"]) for i in items if i.get("asin")}
    seed["amazon_movers"]["asins"] = sorted(set(seed["amazon_movers"]["asins"]) | scraped)
    atomic_write_json(str(SEED_FILE), seed)
    print(f"scraped {len(items)} asins; seed file now has {len(seed['amazon_movers']['asins'])} asins")
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        return args.func(args)
    except DependencyError as exc:
        print(str(exc), file=sys.stderr)
        return 4
    except (ConfigError, PipelineError) as exc:
        print(f"pipeline error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())