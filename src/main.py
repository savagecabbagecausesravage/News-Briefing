"""Main entry point — two modes:

1. `python main.py fetch` — fetch news, save to debug/fetched.json
2. `python main.py generate <summarized.json>` — generate HTML from summarized data
3. `python main.py prompt` — fetch news and print the summarization prompt

The Claude Code trigger orchestrates: fetch → (Claude summarizes) → generate.
"""

import json
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = Path(__file__).parent.parent / "data"


def cmd_fetch():
    """Fetch news from all sources and save to data/fetched.json."""
    from fetch_news import fetch_all

    logger.info("Fetching news from all sources...")
    fetched = fetch_all()
    logger.info(f"Fetched {fetched['total_articles']} articles")

    DATA_DIR.mkdir(exist_ok=True)
    output = DATA_DIR / "fetched.json"
    with open(output, "w", encoding="utf-8") as f:
        json.dump(fetched, f, indent=2, default=str)

    print(f"Saved {fetched['total_articles']} articles to {output}")
    return fetched


def cmd_prompt():
    """Fetch news and print the summarization prompt."""
    from fetch_news import fetch_all
    from summarize import build_prompt

    fetched = fetch_all()
    DATA_DIR.mkdir(exist_ok=True)
    with open(DATA_DIR / "fetched.json", "w", encoding="utf-8") as f:
        json.dump(fetched, f, indent=2, default=str)

    prompt = build_prompt(fetched)
    print(prompt)


def cmd_generate(input_path: str):
    """Generate HTML page from summarized JSON data."""
    from generate_page import generate

    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    output = generate(data)
    print(f"Generated: {output}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py [fetch|prompt|generate <file>]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "fetch":
        cmd_fetch()
    elif command == "prompt":
        cmd_prompt()
    elif command == "generate":
        if len(sys.argv) < 3:
            print("Usage: python main.py generate <summarized.json>")
            sys.exit(1)
        cmd_generate(sys.argv[2])
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
