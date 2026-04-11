"""Bridge from discovered companies to iteration 1 job crawler."""
from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_companies_for_crawling(conn: sqlite3.Connection) -> list[dict]:
    """Return discovered companies that have a careers_url set and aren't yet crawled."""
    rows = conn.execute(
        """SELECT company_name, website, careers_url, category
           FROM company_discovery
           WHERE careers_url != '' AND added_to_pipeline = 0
           ORDER BY talent_count DESC"""
    ).fetchall()
    return [dict(r) for r in rows]


def mark_company_crawled(conn: sqlite3.Connection, name: str) -> None:
    """Flag a company as added to the job crawling pipeline."""
    conn.execute(
        "UPDATE company_discovery SET added_to_pipeline = 1 WHERE company_name = ?",
        (name,),
    )
    conn.commit()


def run_full_pipeline(
    conn: sqlite3.Connection,
    job_crawler: Optional[object] = None,
    output_dir: str | Path = "output",
) -> dict:
    """For each discovered company, run JobCrawler, mark crawled, then regenerate outputs.

    Args:
        conn: SQLite connection.
        job_crawler: Optional JobCrawler instance (or anything with crawl_company(name, url)).
                     If None, a real JobCrawler is constructed.
        output_dir: Where to write tracker.md and charts.

    Returns:
        {"crawled": <count>, "tracker": <path>, "charts": [<paths>]}
    """
    from tracker import generate_tracker_md
    import talent_charts

    companies = get_companies_for_crawling(conn)
    crawled = 0

    if job_crawler is None:
        try:
            from job_crawler import JobCrawler  # type: ignore
            job_crawler = JobCrawler()
        except Exception as e:  # noqa: BLE001
            logger.warning(f"JobCrawler not available, pipeline will mark only: {e}")

    for comp in companies:
        name = comp["company_name"]
        url = comp["careers_url"]
        try:
            if job_crawler is not None and hasattr(job_crawler, "crawl_company"):
                job_crawler.crawl_company(name, url)  # type: ignore[attr-defined]
            mark_company_crawled(conn, name)
            crawled += 1
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed crawling {name}: {e}")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    tracker_path = out / "tracker.md"
    generate_tracker_md(conn, tracker_path)
    chart_paths = [
        talent_charts.generate_sankey(conn, out / "talent_sankey.html"),
        talent_charts.generate_company_ranking_bar(conn, out / "talent_ranking.png"),
        talent_charts.generate_talent_heatmap(conn, out / "talent_heatmap.png"),
    ]
    return {"crawled": crawled, "tracker": tracker_path, "charts": chart_paths}
