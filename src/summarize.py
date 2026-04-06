"""Summarize, categorize, rank, and translate news articles using Claude API."""

import json
import logging
import os

import anthropic

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_ARTICLES_PER_SUBSECTION = 15  # Cap input to manage token usage


def get_client() -> anthropic.Anthropic:
    return anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


def _truncate_articles(categories: dict) -> dict:
    """Cap articles per subsection to control token usage."""
    for cat in categories.values():
        for sub_name, articles in cat["subsections"].items():
            if len(articles) > MAX_ARTICLES_PER_SUBSECTION:
                # Sort by published date (newest first), keep top N
                articles.sort(
                    key=lambda a: a.get("published") or "",
                    reverse=True,
                )
                cat["subsections"][sub_name] = articles[:MAX_ARTICLES_PER_SUBSECTION]
    return categories


def summarize_and_rank(fetched_data: dict) -> dict:
    """Send all articles to Claude for summarization, ranking, and translation."""
    client = get_client()
    categories = _truncate_articles(fetched_data["categories"])

    # Build article list for the prompt
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
```json
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
```

Important:
- Keep sections in the order shown above (World & Markets first).
- If a subsection has no noteworthy articles, include it with an empty items array.
- The detail fields should provide additional context someone would want if they click to expand — not just a longer version of the summary.
- Chinese translations should be natural, not literal. Use standard Simplified Chinese news style.
- Only return valid JSON, no markdown fences or extra text.
"""

    logger.info("Sending articles to Claude for summarization...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=8000,
        messages=[{"role": "user", "content": prompt}],
    )

    result_text = response.content[0].text.strip()

    # Handle case where Claude wraps in markdown code fences
    if result_text.startswith("```"):
        result_text = result_text.split("\n", 1)[1]
        if result_text.endswith("```"):
            result_text = result_text[:-3].strip()

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Claude response as JSON: {e}")
        logger.error(f"Response (first 500 chars): {result_text[:500]}")
        raise

    logger.info(
        f"Summarization complete. "
        f"Breaking: {len(result.get('breaking', []))}, "
        f"Sections: {len(result.get('sections', []))}"
    )
    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    import sys
    # Read fetched data from stdin or file
    if len(sys.argv) > 1:
        with open(sys.argv[1]) as f:
            data = json.load(f)
    else:
        data = json.load(sys.stdin)

    result = summarize_and_rank(data)
    print(json.dumps(result, indent=2, ensure_ascii=False))
