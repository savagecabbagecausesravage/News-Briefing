"""CLI helper: reads fetched.json, prints a compact article list for the agent to summarize.

Usage: python summarize_cli.py /path/to/fetched.json

Outputs a condensed version of the articles (title, source, preview, category)
that fits within a reasonable context window for the agent to read and summarize.
"""

import json
import sys
from pathlib import Path

MAX_PER_SUBSECTION = 5
MAX_TOTAL = 30


def main():
    if len(sys.argv) < 2:
        print("Usage: python summarize_cli.py <fetched.json>")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    categories = data.get("categories", {})
    total = 0

    for cat_key, cat_data in categories.items():
        print(f"\n## {cat_data['display_name']}")
        for sub_name, articles in cat_data["subsections"].items():
            if not articles:
                continue
            articles.sort(key=lambda a: a.get("published") or "", reverse=True)
            articles = articles[:MAX_PER_SUBSECTION]
            print(f"\n### {sub_name}")
            for a in articles:
                if total >= MAX_TOTAL:
                    break
                title = a.get("title", "").strip()
                source = a.get("source", "")
                url = a.get("url", "")
                print(f"- {title} | {source} | {url}")
                total += 1
            if total >= MAX_TOTAL:
                break
        if total >= MAX_TOTAL:
            break

    print(f"\n---\n{total} articles")


if __name__ == "__main__":
    main()
