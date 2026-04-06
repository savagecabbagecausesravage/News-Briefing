"""Main entry point: fetch → summarize → generate."""

import json
import logging
import sys
from pathlib import Path

from fetch_news import fetch_all
from summarize import summarize_and_rank
from generate_page import generate

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== Starting Daily News Briefing Pipeline ===")

    # Step 1: Fetch
    logger.info("Step 1/3: Fetching news from all sources...")
    fetched = fetch_all()
    logger.info(f"Fetched {fetched['total_articles']} articles")

    # Save intermediate data for debugging
    debug_dir = Path(__file__).parent.parent / "debug"
    debug_dir.mkdir(exist_ok=True)
    with open(debug_dir / "fetched.json", "w") as f:
        json.dump(fetched, f, indent=2, default=str)

    if fetched["total_articles"] == 0:
        logger.error("No articles fetched. Check sources and network connectivity.")
        sys.exit(1)

    # Step 2: Summarize
    logger.info("Step 2/3: Summarizing with Claude API...")
    summarized = summarize_and_rank(fetched)

    with open(debug_dir / "summarized.json", "w") as f:
        json.dump(summarized, f, indent=2, ensure_ascii=False)

    # Step 3: Generate
    logger.info("Step 3/3: Generating HTML page...")
    output_path = generate(summarized)

    logger.info(f"=== Pipeline complete. Output: {output_path} ===")


if __name__ == "__main__":
    main()
