#!/usr/bin/env python3
"""CLI entrypoint for AIJobCrawler pipeline."""

import argparse
import sys
import time
from pathlib import Path

from companies import COMPANIES
from company_crawler import CompanyCrawler
from job_crawler import JobCrawler
from role_parser import parse_all_roles
from analyze import run_analysis, print_report
import charts

from db import get_connection, init_db
from talent_discovery import TalentDiscovery
from company_aggregator import aggregate_companies
from company_enricher import enrich_all_companies
from tracker import generate_tracker_md
import talent_charts


def cmd_crawl_companies(args: argparse.Namespace) -> None:
    """Crawl company info pages."""
    company_list = COMPANIES[: args.limit] if args.limit else COMPANIES
    print(f"Crawling {len(company_list)} companies...")
    with CompanyCrawler() as crawler:
        crawler.crawl_all(company_list)
    print("Done crawling companies.")


def cmd_crawl_jobs(args: argparse.Namespace) -> None:
    """Crawl job listings and parse role requirements."""
    company_list = COMPANIES[: args.limit] if args.limit else COMPANIES
    print(f"Crawling jobs for {len(company_list)} companies...")
    with JobCrawler() as crawler:
        results = crawler.crawl_all_companies(company_list)
    total = sum(results.values())
    print(f"Found {total} ML/Research roles across {len(results)} companies.")

    print("Parsing role requirements...")
    parse_all_roles()
    print("Done parsing requirements.")


def cmd_analyze(args: argparse.Namespace) -> None:
    """Run analysis and print report."""
    results = run_analysis()
    print_report(results)


def cmd_charts(args: argparse.Namespace) -> None:
    """Generate all charts."""
    charts.main()
    print("Charts saved to output/.")


def cmd_all(args: argparse.Namespace) -> None:
    """Run the full pipeline."""
    start = time.time()
    cmd_crawl_companies(args)
    cmd_crawl_jobs(args)
    cmd_analyze(args)
    cmd_charts(args)
    elapsed = time.time() - start
    print(f"\nFull pipeline completed in {elapsed:.1f}s.")


# --- Iteration 2: Talent Flow subcommands ---

def cmd_discover(args: argparse.Namespace) -> None:
    """Run talent discovery and aggregate into company_discovery."""
    conn = get_connection()
    init_db(conn)
    td = TalentDiscovery(conn)
    stats = td.discover_all(max_queries_per_lab=args.max_queries_per_lab)
    print(f"Discovery stats: {stats}")
    inserted = aggregate_companies(conn, min_talent=args.min_talent)
    print(f"Aggregated {len(inserted)} companies with >= {args.min_talent} talent.")
    conn.close()


def cmd_enrich(args: argparse.Namespace) -> None:
    """Enrich all un-enriched companies in company_discovery."""
    conn = get_connection()
    init_db(conn)
    count = enrich_all_companies(conn)
    print(f"Enriched {count} companies.")
    conn.close()


def cmd_track(args: argparse.Namespace) -> None:
    """Generate tracker.md and all 3 talent charts to output/."""
    conn = get_connection()
    init_db(conn)
    from config import OUTPUT_DIR
    out_dir = Path(OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)

    md_path = out_dir / "tracker.md"
    generate_tracker_md(conn, md_path)
    print(f"Wrote {md_path}")

    sankey_path = out_dir / "talent_sankey.html"
    talent_charts.generate_sankey(conn, sankey_path)
    print(f"Wrote {sankey_path}")

    bar_path = out_dir / "talent_ranking.png"
    talent_charts.generate_company_ranking_bar(conn, bar_path)
    print(f"Wrote {bar_path}")

    heatmap_path = out_dir / "talent_heatmap.png"
    talent_charts.generate_talent_heatmap(conn, heatmap_path)
    print(f"Wrote {heatmap_path}")

    conn.close()


def cmd_discover_companies(args: argparse.Namespace) -> None:
    """Run pluggable discoverers (YC, HF, AI news, talent flow) into company_discovery."""
    from discoverers import CompanyDiscoverer
    from discoverers.runner import run_discoverers
    from discoverers.yc import YCDiscoverer
    from discoverers.huggingface import HuggingFaceDiscoverer
    from discoverers.ai_news import AINewsDiscoverer
    from discoverers.talent_flow import TalentFlowDiscoverer

    conn = get_connection()
    init_db(conn)

    requested = {s.strip() for s in (args.sources or "yc,hf,ai_news").split(",") if s.strip()}
    discoverers: list[CompanyDiscoverer] = []
    if "yc" in requested:
        discoverers.append(YCDiscoverer())
    if "hf" in requested:
        discoverers.append(HuggingFaceDiscoverer())
    if "ai_news" in requested:
        discoverers.append(AINewsDiscoverer())
    if "talent_flow" in requested:
        discoverers.append(TalentFlowDiscoverer(conn))

    stats = run_discoverers(conn, discoverers, limit_per_source=args.limit)
    print(f"Discoverer stats: {stats}")
    conn.close()


def cmd_crawl_jobs_from_db(args: argparse.Namespace) -> None:
    """Crawl job listings from companies in the company_discovery table."""
    conn = get_connection()
    init_db(conn)
    with JobCrawler() as crawler:
        results = crawler.crawl_from_db(conn, limit=args.limit)
    total = sum(results.values())
    print(f"Found {total} ML/Research roles across {len(results)} companies.")
    conn.close()


def cmd_discover_all(args: argparse.Namespace) -> None:
    """Run discover + enrich + track in sequence."""
    start = time.time()
    cmd_discover(args)
    cmd_enrich(args)
    cmd_track(args)
    print(f"\nTalent flow pipeline completed in {time.time() - start:.1f}s.")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="aijobcrawler",
        description="Crawl AI company job listings, analyze ML/Research role requirements, and generate charts.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of companies to crawl (for testing)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("crawl-companies", help="Crawl company info pages")
    subparsers.add_parser("crawl-jobs", help="Crawl job listings and parse requirements")
    subparsers.add_parser("analyze", help="Run analysis and print report")
    subparsers.add_parser("charts", help="Generate all charts")
    subparsers.add_parser("all", help="Run the full pipeline")

    # Iter 2: talent flow
    p_discover = subparsers.add_parser("discover", help="Discover talent moves and aggregate companies")
    p_discover.add_argument("--max-queries-per-lab", type=int, default=None, dest="max_queries_per_lab")
    p_discover.add_argument("--min-talent", type=int, default=2, dest="min_talent")

    subparsers.add_parser("enrich", help="Enrich discovered companies via Google search")

    subparsers.add_parser("track", help="Generate tracker.md and talent charts")

    p_disc_co = subparsers.add_parser(
        "discover-companies",
        help="Run pluggable company discoverers (yc, hf, ai_news, talent_flow)",
    )
    p_disc_co.add_argument(
        "--sources",
        type=str,
        default="yc,hf,ai_news",
        help="Comma-separated source names",
    )

    subparsers.add_parser(
        "crawl-jobs-from-db",
        help="Crawl jobs for companies in company_discovery table",
    )

    p_discover_all = subparsers.add_parser("discover-all", help="Run discover + enrich + track")
    p_discover_all.add_argument("--max-queries-per-lab", type=int, default=None, dest="max_queries_per_lab")
    p_discover_all.add_argument("--min-talent", type=int, default=2, dest="min_talent")

    args = parser.parse_args()

    commands = {
        "crawl-companies": cmd_crawl_companies,
        "crawl-jobs": cmd_crawl_jobs,
        "analyze": cmd_analyze,
        "charts": cmd_charts,
        "all": cmd_all,
        "discover": cmd_discover,
        "enrich": cmd_enrich,
        "track": cmd_track,
        "discover-all": cmd_discover_all,
        "discover-companies": cmd_discover_companies,
        "crawl-jobs-from-db": cmd_crawl_jobs_from_db,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
