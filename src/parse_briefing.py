"""Parse agent-written Markdown briefing into structured JSON for the HTML template.

The agent writes natural Markdown with a specific structure:
    ## BREAKING
    ### Title | Source | URL
    Summary in English (2-3 sentences)
    ---CN---
    Chinese translation
    ---DETAIL---
    Detail in English (1-2 paragraphs)
    ---DETAIL_CN---
    Detail in Chinese

    ## World & Markets
    ### Top Headlines
    #### Title | Source | URL
    Summary...
    ---CN---
    ...

This script parses that into the JSON structure expected by generate_page.py.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

SECTION_MAP = {
    "world & markets": ("world_and_markets", "World & Markets"),
    "ai & technology": ("ai_and_technology", "AI & Technology"),
    "private equity & vc": ("private_equity_and_vc", "Private Equity & VC"),
    "fintech": ("fintech", "Fintech"),
}


def parse_entry(lines: list[str]) -> dict | None:
    """Parse a single entry block (title line + content lines)."""
    if not lines:
        return None

    # First line: #### Title | Source | URL  or  ### Title | Source | URL
    header = lines[0].lstrip("#").strip()
    parts = [p.strip() for p in header.split("|")]
    if len(parts) < 2:
        return None

    title = parts[0]
    source = parts[1] if len(parts) > 1 else ""
    url = parts[2] if len(parts) > 2 else ""

    # Join remaining lines and split by markers
    body = "\n".join(lines[1:]).strip()

    summary_en = ""
    summary_cn = ""
    detail_en = ""
    detail_cn = ""

    # Try simple EN:/CN: format first
    en_match = re.search(r"(?:^|\n)EN:\s*(.+?)(?=\nCN:|\n---|\Z)", body, re.DOTALL)
    cn_match = re.search(r"(?:^|\n)CN:\s*(.+?)(?=\n---|\nEN:|\Z)", body, re.DOTALL)

    if en_match:
        summary_en = en_match.group(1).strip()
        summary_cn = cn_match.group(1).strip() if cn_match else summary_en
        # detail = summary for this simple format
        detail_en = summary_en
        detail_cn = summary_cn
        if not title or not summary_en:
            return None
        return {
            "title": title, "summary_en": summary_en, "summary_cn": summary_cn,
            "url": url, "source": source, "detail_en": detail_en, "detail_cn": detail_cn,
        }

    # Legacy ---CN--- marker format
    if "---CN---" in body:
        before_cn, after_cn = body.split("---CN---", 1)
        summary_en = before_cn.strip()
        remainder = after_cn.strip()
    else:
        summary_en = body
        remainder = ""

    if "---DETAIL---" in remainder:
        cn_part, detail_part = remainder.split("---DETAIL---", 1)
        summary_cn = cn_part.strip()
        if "---DETAIL_CN---" in detail_part:
            detail_en_part, detail_cn_part = detail_part.split("---DETAIL_CN---", 1)
            detail_en = detail_en_part.strip()
            detail_cn = detail_cn_part.strip()
        else:
            detail_en = detail_part.strip()
    elif remainder:
        summary_cn = remainder.strip()

    if not title or not summary_en:
        return None

    return {
        "title": title,
        "summary_en": summary_en,
        "summary_cn": summary_cn or summary_en,
        "url": url,
        "source": source,
        "detail_en": detail_en or summary_en,
        "detail_cn": detail_cn or summary_cn or detail_en or summary_en,
    }


def parse_briefing(markdown: str) -> dict:
    """Parse the full Markdown briefing into structured JSON."""
    lines = markdown.split("\n")
    result = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "breaking": [],
        "sections": [],
    }

    # Initialize sections
    section_order = [
        ("world_and_markets", "World & Markets",
         ["Top Headlines", "US-China Relations", "Financial Markets",
          "Science & Technology Breakthroughs"]),
        ("ai_and_technology", "AI & Technology",
         ["Research & Papers", "Industry News", "Key People & Company Updates"]),
        ("private_equity_and_vc", "Private Equity & VC",
         ["Deals & Fundraising", "Fund News & Trends"]),
        ("fintech", "Fintech",
         ["Platforms & Products", "Regulation"]),
    ]

    sections = {}
    for key, name, subs in section_order:
        section = {
            "key": key,
            "display_name": name,
            "subsections": [{"name": s, "entries": []} for s in subs],
        }
        sections[key] = section
        result["sections"].append(section)

    # Parse state
    current_section = None
    current_subsection = None
    current_entry_lines = []
    in_breaking = False

    def flush_entry():
        nonlocal current_entry_lines
        if not current_entry_lines:
            return
        entry = parse_entry(current_entry_lines)
        current_entry_lines = []
        if entry is None:
            return
        if in_breaking:
            result["breaking"].append(entry)
        elif current_section and current_subsection is not None:
            sec = sections.get(current_section)
            if sec:
                for sub in sec["subsections"]:
                    if sub["name"] == current_subsection:
                        sub["entries"].append(entry)
                        break

    for line in lines:
        stripped = line.strip()

        # ## Section header
        if stripped.startswith("## ") and not stripped.startswith("### "):
            flush_entry()
            section_name = stripped[3:].strip().lower()
            if section_name == "breaking" or section_name == "breaking / urgent":
                in_breaking = True
                current_section = None
                current_subsection = None
            else:
                in_breaking = False
                for key, (sec_key, _) in SECTION_MAP.items():
                    if key in section_name:
                        current_section = sec_key
                        current_subsection = None
                        break

        # ### Subsection header or breaking entry
        elif stripped.startswith("### ") and not stripped.startswith("#### "):
            flush_entry()
            sub_name = stripped[4:].strip()
            if in_breaking or ("|" in sub_name):
                # This is an entry (breaking or single-level)
                current_entry_lines = [stripped]
            else:
                current_subsection = sub_name

        # #### Entry header
        elif stripped.startswith("#### "):
            flush_entry()
            current_entry_lines = [stripped]

        # Content line
        elif current_entry_lines is not None and (current_entry_lines or stripped):
            if current_entry_lines:
                current_entry_lines.append(line)

    flush_entry()
    return result


def main():
    if len(sys.argv) < 2:
        print("Usage: python parse_briefing.py <briefing.md> [output.json]")
        sys.exit(1)

    md_path = Path(sys.argv[1])
    markdown = md_path.read_text(encoding="utf-8")
    result = parse_briefing(markdown)

    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(
        md_path.parent / "summarized.json"
    )
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"Parsed {sum(len(s['entries']) for sec in result['sections'] for s in sec['subsections'])} entries + {len(result['breaking'])} breaking")
    print(f"Output: {output_path}")


if __name__ == "__main__":
    main()
