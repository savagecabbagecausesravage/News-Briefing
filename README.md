# Building a Daily News Briefing Agent with Claude Code

A complete guide to building an autonomous daily news briefing agent that fetches, summarizes, translates, and publishes news — using Claude Code scheduled triggers, GitHub Actions, and GitHub Pages. Zero API costs.

---

## What You Get

- A **responsive web page** updated daily with 15-18 curated news articles
- **Bilingual** (English + Chinese) with a one-click language toggle
- **Clickable headlines** linking to original sources
- **Date dropdown** to browse the last 5 days of briefings
- **Notion page** with the same content, organized under a parent page
- **Slack DM** with top 5 headlines and a link to the full briefing
- **Fully autonomous** — runs on a cron schedule with no manual intervention

**Live example:** https://savagecabbagecausesravage.github.io/News-Briefing/

---

## Architecture

```
23:55 UTC — GitHub Actions (fetch-news.yml)
  └── Python fetches 500+ articles from 38 RSS feeds + NewsAPI
  └── Commits data/fetched.json to the repo

00:00 UTC — Claude Code Scheduled Trigger (Sonnet)
  Phase 1 (parent agent):
    ├── Clones repo (pre-fetched data is already there)
    ├── Reads compact article list via summarize_cli.py
    ├── Writes briefing as Markdown (NOT JSON)
    ├── Python converts Markdown → JSON → HTML
    └── Pushes to GitHub Pages

  Phase 2 (subagent — required for MCP bug workaround):
    ├── Writes structured briefing to Notion
    └── DMs user on Slack with top 5 headlines
```

### Why This Architecture?

| Decision | Reason |
|----------|--------|
| **GitHub Actions fetches, Claude summarizes** | Remote trigger environment blocks outbound HTTP to RSS feeds |
| **LLM writes Markdown, not JSON** | Models time out or stop mid-task when writing large JSON. Markdown is natural output. Python parses it. |
| **Sonnet, not Opus** | Opus times out on the Markdown write step. Sonnet is 3x faster with minimal quality loss for news summaries. |
| **Subagent for Notion/Slack** | MCP connector tools don't load on the trigger's first turn (platform bug). Spawning a subagent via the Agent tool properly initializes them. |
| **GitHub PAT in clone URL** | Remote environment has no git credentials. PAT enables push. |
| **setup.sh for dependencies** | `sgmllib3k` (feedparser dependency) fails to build on Python 3.12+. The setup script handles manual installation. |

---

## Prerequisites

- **Claude Code** with a claude.ai account (for scheduled triggers)
- **GitHub account** (free tier is fine)
- **NewsAPI key** (free at [newsapi.org](https://newsapi.org/register)) — optional, RSS feeds work without it
- **GitHub Personal Access Token** (fine-grained, scoped to the repo)
- **Notion** connected to Claude Code (via MCP connector) — optional
- **Slack** connected to Claude Code (via MCP connector) — optional

---

## Step-by-Step Setup

### 1. Create the GitHub Repository

Create a new **public** repository (public = free GitHub Pages).

```
your-repo/
├── .github/
│   └── workflows/
│       └── fetch-news.yml    # Cron job to fetch articles
├── src/
│   ├── fetch_news.py         # RSS + NewsAPI fetching
│   ├── summarize_cli.py      # Compact article output for the agent
│   ├── parse_briefing.py     # Markdown → JSON converter
│   ├── generate_page.py      # JSON → HTML renderer
│   ├── main.py               # CLI entry point
│   ├── sources.yaml           # Source configuration
│   └── template.html          # Jinja2 HTML template
├── docs/                      # GitHub Pages serves from here
│   └── index.html             # Generated output
├── data/
│   └── fetched.json           # Pre-fetched articles (committed by GitHub Actions)
├── requirements.txt
├── setup.sh                   # Dependency installer for remote env
└── .gitignore
```

### 2. Configure News Sources (`src/sources.yaml`)

This is where you define what news you want. The file has two sections:

**RSS feeds** — direct feeds from publications:
```yaml
rss_feeds:
  - name: "BBC World"
    url: "https://feeds.bbci.co.uk/news/world/rss.xml"
    category: "world_and_markets"
    subsection: "Top Headlines"
```

**NewsAPI queries** — for sources without RSS feeds:
```yaml
newsapi_queries:
  - query: "private equity deals"
    category: "private_equity_and_vc"
    subsection: "Deals & Fundraising"
```

#### Personalisation choices:

| What to customise | How |
|-------------------|-----|
| **Topics/categories** | Edit the `categories` section in sources.yaml. Add/remove/rename sections. |
| **Sources** | Add/remove RSS feeds and NewsAPI queries. See the [RSS feed research](#appendix-rss-feeds) appendix. |
| **Weighting** | Adjust the `weight` field per category (should sum to 1.0). |
| **Article count** | Change `MAX_PER_SUBSECTION` and `MAX_TOTAL` in `summarize_cli.py`. |

### 3. Configure the HTML Template (`src/template.html`)

The template uses Jinja2 and supports:
- Dark/light mode (follows system preference)
- Language toggle (EN/CN by default)
- Date dropdown for historical briefings (last 5 days)
- Responsive design (mobile + desktop)
- Clickable headlines linking to original articles

#### Personalisation choices:

| What to customise | How |
|-------------------|-----|
| **Languages** | Change the `lang-en`/`lang-cn` CSS classes and add your language. Update `SECTION_CN` and `SUBSECTION_CN` dicts in `generate_page.py`. |
| **Colour scheme** | Edit the CSS variables in `:root` and `@media (prefers-color-scheme: dark)`. |
| **Archive depth** | Change `archive_files[5:]` in `generate_page.py` to keep more/fewer days. |

### 4. Set Up GitHub Actions (`fetch-news.yml`)

This workflow runs 5 minutes before your Claude trigger to pre-fetch articles:

```yaml
name: Fetch News Data

on:
  schedule:
    - cron: '55 23 * * *'  # 5 min before trigger
  workflow_dispatch:        # Manual trigger

permissions:
  contents: write

jobs:
  fetch:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
          cache: 'pip'
      - run: pip install -r requirements.txt
      - run: cd src && python main.py fetch
        env:
          NEWS_API_KEY: ${{ secrets.NEWS_API_KEY }}
      - run: |
          git config user.name "github-actions[bot]"
          git config user.email "github-actions[bot]@users.noreply.github.com"
          git add data/fetched.json
          git diff --staged --quiet || git commit -m "Fetch news data $(date -u +%Y-%m-%d)"
          git push
```

**Add the `NEWS_API_KEY` secret** in your repo: Settings → Secrets → Actions → New repository secret.

### 5. Create a GitHub Personal Access Token

1. GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Name: `news-briefing-bot`
3. Repository access: Only select your repo
4. Permissions: Contents → Read and write
5. Generate and save the token securely (e.g., `~/.secrets/github-pat.txt`)

**Never paste tokens in chat.** Save to a local file, then tell Claude the file path.

### 6. Enable GitHub Pages

1. Repo → Settings → Pages
2. Source: Deploy from a branch
3. Branch: `main`, folder: `/docs`
4. Save

Your page will be live at: `https://<username>.github.io/<repo-name>/`

### 7. Create the Claude Code Scheduled Trigger

The trigger prompt has two phases:

**Phase 1 (parent agent):** Clone repo → read articles → write Markdown briefing → convert to HTML → push to GitHub

**Phase 2 (subagent):** Write to Notion + send Slack DM

Key elements of the trigger configuration:
- **Model:** `claude-sonnet-4-6` (fast enough to avoid timeouts)
- **Cron:** `0 0 * * *` (adjust to your timezone needs)
- **persist_session:** `true` (safety net if agent pauses)
- **allowed_tools:** `["Bash", "Read", "Write", "Edit", "Glob", "Grep", "Agent", "mcp__Notion__*", "mcp__Slack__*"]`
- **MCP connections:** Notion and Slack connectors

#### The Markdown Format

The agent writes Markdown, not JSON. This is the critical design decision that makes the pipeline reliable:

```markdown
## World & Markets
### Top Headlines
#### US Announces New Tariffs on Chinese Tech | Reuters | https://reuters.com/...
EN: The US has announced new tariffs targeting Chinese semiconductor exports. The move is expected to escalate trade tensions.
CN: 美国宣布对中国半导体出口征收新关税。此举预计将加剧贸易紧张局势。
TitleCN: 美国宣布对中国科技出口征收新关税

#### Another Headline | Source | URL
EN: Summary.
CN: 摘要。
TitleCN: 中文标题
```

`parse_briefing.py` converts this to structured JSON, which `generate_page.py` renders into HTML.

#### Personalisation choices for the trigger:

| What to customise | How |
|-------------------|-----|
| **Schedule** | Change `cron_expression`. Use [crontab.guru](https://crontab.guru) to build expressions. |
| **Item count** | Change "15-18 items" in the prompt. More items = higher timeout risk. |
| **Content focus** | Edit the "CRITICAL CONTENT RULES" section. Add/remove subsections, change weights. |
| **Languages** | Replace `CN:` and `TitleCN:` with your language. Update `parse_briefing.py` regex accordingly. |
| **Output channels** | Remove Notion/Slack tasks from the subagent prompt if not needed. |
| **Notion structure** | Change page titles, parent page name, block types in the subagent prompt. |
| **Slack format** | Customise the message format, channel (DM vs channel), number of headlines. |

### 8. MCP Connector Setup

If using Notion and/or Slack, attach MCP connectors to your trigger:

```json
"mcp_connections": [
  {
    "connector_uuid": "<your-notion-connector-id>",
    "name": "Notion",
    "url": "https://mcp.notion.com/mcp"
  },
  {
    "connector_uuid": "<your-slack-connector-id>",
    "name": "Slack",
    "url": "https://mcp.slack.com/mcp"
  }
]
```

Find your connector UUIDs from an existing trigger or the Claude Code settings.

**Important:** MCP tools don't work on the trigger's first turn (platform bug). The subagent pattern is the workaround — the parent agent spawns a subagent via the `Agent` tool, and the subagent properly initializes MCP connectors.

---

## Lessons Learned

### What Failed and Why

| Attempt | What happened | Root cause |
|---------|--------------|------------|
| Agent writes large JSON directly | Agent stops mid-task, sends text-only message | Models "announce" before writing large output, ending the turn |
| Opus model for generation | Times out | Opus output speed too slow for the content volume |
| RSS feeds in remote trigger | Connection blocked | Remote env restricts outbound HTTP |
| MCP tools on first turn | Tools not found | Platform bug — deferred tool registry doesn't include MCP until after user interaction |
| `pip install` in remote env | `sgmllib3k` build fails | Python 3.12+ dropped `sgmllib` module |
| `persist_session: false` | Agent stops, no way to continue | Text-only messages end the turn permanently |

### What Worked

| Pattern | Why it works |
|---------|-------------|
| **LLM writes Markdown, Python converts** | Natural output format, no timeout risk, easy to parse |
| **GitHub Actions for fetching** | Full network access, commits data for the trigger to read |
| **Subagent delegation for MCP** | Subagents properly initialize MCP connectors |
| **Sonnet for generation** | 3x faster than Opus, sufficient quality for news summaries |
| **setup.sh for dependencies** | Handles `sgmllib3k` build issue reliably |
| **Compact article input (30 max)** | Reduces context, leaves headroom for output |

### Research Sources

These open-source projects informed the architecture:

- [ai-news-bot](https://github.com/giftedunicorn/ai-news-bot) — LLM writes natural text, not JSON
- [auto-news](https://github.com/finaldie/auto-news) — Airflow DAGs for pipeline orchestration
- [Chronicle-n8n](https://github.com/coeusyk/chronicle-n8n) — Tiny JSON per item, not giant blobs
- [Agently Daily News](https://github.com/AgentEra/Agently-Daily-News-Collector) — Editorial pipeline with YAML prompt schemas
- [AI-News-Briefing](https://github.com/hoangsonww/AI-News-Briefing) — Claude Code as agentic runtime

---

## Appendix: RSS Feeds

### Working RSS feeds (verified)

**AI/ML:**
- TechCrunch AI: `https://techcrunch.com/category/artificial-intelligence/feed/`
- The Verge AI: `https://www.theverge.com/rss/ai-artificial-intelligence/index.xml`
- Ars Technica: `https://feeds.arstechnica.com/arstechnica/index`
- VentureBeat AI: `https://venturebeat.com/category/ai/feed/`
- MIT Technology Review: `https://www.technologyreview.com/feed/`
- OpenAI Blog: `https://openai.com/blog/rss.xml`
- Google AI Blog: `https://blog.google/technology/ai/rss/`
- NVIDIA AI: `https://blogs.nvidia.com/feed/`
- Microsoft Research: `https://www.microsoft.com/en-us/research/feed/`
- ArXiv cs.AI/cs.LG/cs.CL: `https://rss.arxiv.org/rss/cs.AI` (also cs.LG, cs.CL)
- IEEE Spectrum: `https://spectrum.ieee.org/feeds/feed.rss`
- BAIR: `https://bair.berkeley.edu/blog/feed.xml`
- Import AI: `https://importai.substack.com/feed`
- Benedict Evans: `https://www.ben-evans.com/benedictevans?format=rss`

**Finance/PE:**
- Bloomberg: `https://feeds.bloomberg.com/markets/news.rss`
- Financial Times: `https://www.ft.com/rss/home`
- Finextra: `https://www.finextra.com/rss/headlines.aspx`
- PYMNTS: `https://www.pymnts.com/feed/`
- American Banker: `https://www.americanbanker.com/feed.rss`

**General News:**
- BBC World: `https://feeds.bbci.co.uk/news/world/rss.xml`
- Al Jazeera: `https://www.aljazeera.com/xml/rss/all.xml`
- The Economist: `https://www.economist.com/the-world-this-week/rss.xml`
- CNBC: `https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114`
- WSJ: `https://feeds.a.dj.com/rss/RSSMarketsMain.xml`

**Science:**
- Nature: `https://www.nature.com/nature.rss`
- Science AAAS: `https://www.science.org/rss/news_current.xml`
- New Scientist: `https://www.newscientist.com/feed/home/`

**Think Tanks:**
- CSIS: `https://www.csis.org/rss.xml`
- CFR: `https://feeds.feedburner.com/cfr_main`
- Politico EU: `https://www.politico.eu/feed/`

### No RSS (use NewsAPI instead)
- Anthropic Blog, PitchBook, Reuters, AP, Stanford HAI

---

## Appendix: Cost

| Component | Cost |
|-----------|------|
| Claude Code trigger | Included in Claude Pro/Team subscription |
| GitHub Actions | Free tier (2000 min/month) |
| GitHub Pages | Free for public repos |
| NewsAPI | Free tier (100 req/day) |
| Notion MCP | Free |
| Slack MCP | Free |
| **Total** | **$0/month** (beyond existing Claude subscription) |

---

## Appendix: Timezone Reference

The cron schedules use UTC. Common conversions:

| Your timezone | 8am local = UTC | Cron for 8am delivery |
|---------------|-----------------|----------------------|
| Berlin (CEST, summer) | 06:00 UTC | `0 6 * * *` |
| Berlin (CET, winter) | 07:00 UTC | `0 7 * * *` |
| China (CST) | 00:00 UTC | `0 0 * * *` |
| US East (EDT) | 12:00 UTC | `0 12 * * *` |
| US West (PDT) | 15:00 UTC | `0 15 * * *` |
| London (BST) | 07:00 UTC | `0 7 * * *` |

Set the fetch workflow 5 minutes before the trigger.
