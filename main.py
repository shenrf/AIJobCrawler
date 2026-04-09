#!/usr/bin/env python3
"""CLI entrypoint for AIJobCrawler pipeline."""

import argparse
import sys
import time

from companies import COMPANIES
from company_crawler import CompanyCrawler
from job_crawler import JobCrawler
from role_parser import parse_all_roles
from analyze import run_analysis, print_report
import charts


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

    args = parser.parse_args()

    commands = {
        "crawl-companies": cmd_crawl_companies,
        "crawl-jobs": cmd_crawl_jobs,
        "analyze": cmd_analyze,
        "charts": cmd_charts,
        "all": cmd_all,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
