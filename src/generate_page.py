"""Generate static HTML page from summarized news data."""

import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger(__name__)

TEMPLATE_DIR = Path(__file__).parent
OUTPUT_DIR = Path(__file__).parent.parent / "docs"

# Chinese translations for section/subsection names
SECTION_CN = {
    "World & Markets": "世界与市场",
    "AI & Technology": "人工智能与科技",
    "Private Equity & VC": "私募股权与风投",
    "Fintech": "金融科技",
}

SUBSECTION_CN = {
    "Top Headlines": "头条新闻",
    "US-China Relations": "中美关系",
    "Financial Markets": "金融市场",
    "Science & Technology Breakthroughs": "科技突破",
    "Research & Papers": "研究与论文",
    "Industry News": "行业新闻",
    "Key People & Company Updates": "重要人物与公司动态",
    "Deals & Fundraising": "交易与融资",
    "Fund News & Trends": "基金动态与趋势",
    "Platforms & Products": "平台与产品",
    "Regulation": "监管政策",
}


def count_items(section: dict) -> int:
    """Count total items across all subsections."""
    total = 0
    for sub in section.get("subsections", []):
        total += len(sub.get("entries", []))
    return total


def generate(summarized_data: dict, github_repo: str = "") -> str:
    """Generate HTML page from summarized data and write to docs/index.html."""
    env = Environment(loader=FileSystemLoader(str(TEMPLATE_DIR)))
    template = env.get_template("template.html")

    # Add Chinese translations and item counts to sections
    sections = summarized_data.get("sections", [])
    for section in sections:
        section["display_name_cn"] = SECTION_CN.get(
            section["display_name"], section["display_name"]
        )
        section["item_count"] = count_items(section)
        for sub in section.get("subsections", []):
            sub["name_cn"] = SUBSECTION_CN.get(sub["name"], sub["name"])

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    generated_at = summarized_data.get(
        "generated_at",
        datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M"),
    )
    if "T" in generated_at:
        generated_at = generated_at.replace("T", " ")[:16]

    # Count total sources from sources.yaml
    import yaml
    sources_path = Path(__file__).parent / "sources.yaml"
    source_count = 0
    if sources_path.exists():
        with open(sources_path) as f:
            sources = yaml.safe_load(f)
            source_count = len(sources.get("rss_feeds", []))
            source_count += len(sources.get("newsapi_queries", []))

    html = template.render(
        date=today,
        breaking=summarized_data.get("breaking", []),
        sections=sections,
        generated_at=generated_at,
        source_count=source_count,
        github_repo=github_repo or os.environ.get("GITHUB_REPOSITORY", ""),
    )

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / "index.html"
    output_path.write_text(html, encoding="utf-8")
    logger.info(f"Generated {output_path} ({len(html)} bytes)")

    return str(output_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys

    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    output = generate(data)
    print(f"Output: {output}")
