"""Summarize news data — used by Claude Code trigger, not API.

This module provides:
1. build_prompt() — generates the summarization prompt from fetched data
2. parse_response() — parses Claude's JSON response
3. The trigger reads fetched.json, builds the prompt, summarizes itself,
   then passes the result to generate_page.py
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_ARTICLES_PER_SUBSECTION = 15


def _truncate_articles(categories: dict) -> dict:
    """Cap articles per subsection to control token usage."""
    for cat in categories.values():
        for sub_name, articles in cat["subsections"].items():
            if len(articles) > MAX_ARTICLES_PER_SUBSECTION:
                articles.sort(
                    key=lambda a: a.get("published") or "",
                    reverse=True,
                )
                cat["subsections"][sub_name] = articles[:MAX_ARTICLES_PER_SUBSECTION]
    return categories


def build_prompt(fetched_data: dict) -> str:
    """Build the summarization prompt from fetched article data."""
    categories = _truncate_articles(fetched_data["categories"])

    articles_text = ""
    for cat_key, cat_data in categories.items():
        articles_text += f"\n## {cat_data['display_name']} (weight: {cat_data['weight']})\n"
        for sub_name, articles in cat_data["subsections"].items():
            if not articles:
                continue
            articles_text += f"\n### {sub_name}\n"
            for a in articles:
                articles_text += f"- **{a['title']}** ({a['source']})\n"
                articles_text += f"  URL: {a['url']}\n"
                if a.get("summary"):
                    articles_text += f"  Preview: {a['summary'][:200]}\n"
                if a.get("published"):
                    articles_text += f"  Published: {a['published']}\n"

    prompt = f"""You are a news editor creating a daily briefing. Below are raw articles fetched from various sources.

Your job:
1. **Select** the most important/newsworthy articles. Target ~10 minutes total reading time for summaries (roughly 20-35 items total).
2. **Rank** by importance within each section.
3. **Summarize** each selected article in 2-3 sentences in English.
4. **Translate** each summary to Chinese (Simplified).
5. **Flag** any breaking/urgent news that should appear at the top.
6. Respect the category weights: World & Markets ~40%, AI & Technology ~30%, PE & VC ~18%, Fintech ~12%. These are approximate — if a section has more newsworthy items, include more.

## Articles

{articles_text}

## Output Format

Return valid JSON with this exact structure:
{{
  "generated_at": "ISO timestamp",
  "breaking": [
    {{
      "title": "...",
      "summary_en": "2-3 sentence summary",
      "summary_cn": "Chinese translation of summary",
      "url": "...",
      "source": "...",
      "detail_en": "Optional 1-2 paragraph deeper context",
      "detail_cn": "Chinese translation of detail"
    }}
  ],
  "sections": [
    {{
      "key": "world_and_markets",
      "display_name": "World & Markets",
      "subsections": [
        {{
          "name": "Top Headlines",
          "entries": [
            {{
              "title": "...",
              "summary_en": "...",
              "summary_cn": "...",
              "url": "...",
              "source": "...",
              "detail_en": "...",
              "detail_cn": "..."
            }}
          ]
        }}
      ]
    }},
    {{
      "key": "ai_and_technology",
      "display_name": "AI & Technology",
      "subsections": [...]
    }},
    {{
      "key": "private_equity_and_vc",
      "display_name": "Private Equity & VC",
      "subsections": [...]
    }},
    {{
      "key": "fintech",
      "display_name": "Fintech",
      "subsections": [...]
    }}
  ]
}}

Important:
- Keep sections in the order shown above (World & Markets first).
- If a subsection has no noteworthy articles, include it with an empty entries array.
- The detail fields should provide additional context beyond the summary.
- Chinese translations should be natural Simplified Chinese news style.
- Only return valid JSON, no markdown fences or extra text."""

    return prompt


def parse_response(response_text: str) -> dict:
    """Parse Claude's JSON response, handling markdown fences."""
    text = response_text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3].strip()
    return json.loads(text)


if __name__ == "__main__":
    # Utility: print the prompt for a given fetched.json
    import sys
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)
    print(build_prompt(data))
