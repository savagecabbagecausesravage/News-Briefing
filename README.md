# Daily News Briefing Agent

An autonomous agent that delivers a curated daily news briefing to a web page, Notion, and Slack — powered by Claude Code, GitHub Actions, and GitHub Pages. Zero API costs beyond a Claude subscription.

**Live demo:** https://savagecabbagecausesravage.github.io/News-Briefing/

## What it does

Every day at midnight UTC:
1. **GitHub Actions** fetches 500+ articles from 38 RSS feeds and NewsAPI
2. **Claude Code** reads the articles, picks the 15-18 most important, writes bilingual summaries (English + Chinese), and generates a responsive HTML page
3. The page is **pushed to GitHub Pages** — accessible on any device, no app needed
4. A **Notion page** is created under a parent "News Briefing" page with clickable article links
5. A **Slack DM** is sent with the top 5 headlines and a link to the full briefing

The page supports:
- EN/CN language toggle (one click)
- Dark/light mode (follows system)
- Date dropdown to browse last 5 days
- Clickable headlines linking to original sources
- Mobile-friendly responsive layout

---

## How to build this from scratch

### Prerequisites

- A **Claude Pro or Team subscription** (for scheduled triggers)
- A **GitHub account** (free tier)
- ~30 minutes

Optional:
- **NewsAPI key** (free at [newsapi.org](https://newsapi.org/register)) for extra source coverage
- **Notion** connected to Claude Code (for Notion pages)
- **Slack** connected to Claude Code (for Slack DMs)

---

### Step 1: Fork the repo

1. Go to https://github.com/savagecabbagecausesravage/News-Briefing
2. Click **Fork** (top right)
3. Name it whatever you want
4. Go to your fork's **Settings → General → Danger Zone → Change visibility → Make public** (required for free GitHub Pages)

### Step 2: Enable GitHub Pages

1. In your fork: **Settings → Pages**
2. Source: **Deploy from a branch**
3. Branch: **main**, folder: **/docs**
4. Click **Save**

Your page will be at: `https://<your-username>.github.io/<repo-name>/`

### Step 3: Add NewsAPI key (optional but recommended)

1. Sign up at [newsapi.org/register](https://newsapi.org/register) — it's free
2. Copy your API key from the dashboard
3. In your fork: **Settings → Secrets and variables → Actions → New repository secret**
4. Name: `NEWS_API_KEY`, Value: paste your key

Without this, the 38 RSS feeds still work. NewsAPI adds coverage for Reuters, AP, PitchBook and other sources that don't have RSS feeds.

### Step 4: Create a GitHub Personal Access Token

The Claude trigger needs to push generated HTML to your repo. It can't use your password, so it needs a token.

1. Go to **GitHub → Settings → Developer settings → Personal access tokens → Fine-grained tokens**
2. Click **Generate new token**
3. **Token name:** `news-briefing-bot`
4. **Expiration:** your choice (90 days is safe, no expiration is fine for a public news repo)
5. **Repository access:** Only select repositories → select your fork
6. **Permissions → Repository permissions → Contents:** Read and write
7. Click **Generate token**
8. **Save the token somewhere safe** (e.g., a local file `~/.secrets/github-pat.txt`). You'll need it in Step 7.

### Step 5: Run the fetch workflow

This downloads articles from all your RSS feeds and commits them to the repo.

1. Go to your fork → **Actions** tab
2. Click **Fetch News Data** in the left sidebar
3. Click **Run workflow → Run workflow**
4. Wait ~1-2 minutes for it to complete (green checkmark)

This commits a `data/fetched.json` file to your repo with hundreds of articles.

### Step 6: Customise your sources and topics

Edit `src/sources.yaml` to change what news you get. The file has two sections:

**RSS feeds** — add or remove feeds:
```yaml
rss_feeds:
  - name: "BBC World"
    url: "https://feeds.bbci.co.uk/news/world/rss.xml"
    category: "world_and_markets"        # which section it goes in
    subsection: "Top Headlines"           # which subsection
```

**NewsAPI queries** — keyword searches:
```yaml
newsapi_queries:
  - query: "private equity deals"
    category: "private_equity_and_vc"
    subsection: "Deals & Fundraising"
```

**To change the sections entirely** (e.g., replace Finance with Sports):
1. Edit the `categories` block at the top of `sources.yaml`
2. Update `SECTION_MAP` and `section_order` in `src/parse_briefing.py`
3. Update `SECTION_CN` and `SUBSECTION_CN` in `src/generate_page.py`
4. Update the trigger prompt (Step 7) to match

### Step 7: Create the Claude Code scheduled trigger

This is the heart of the system. Open Claude Code and run `/schedule` or use the command below.

**Before you start:** Have your GitHub PAT from Step 4 ready. Save it to a local file and tell Claude the path — never paste tokens in chat.

**Create the trigger with these settings:**

| Setting | Value |
|---------|-------|
| Name | `news-briefing` |
| Cron | `0 0 * * *` (midnight UTC — see timezone table below) |
| Model | `claude-sonnet-4-6` (NOT Opus — Opus is too slow and times out) |
| persist_session | `true` |

**The trigger prompt** (replace the bracketed parts):

```
You are an AUTONOMOUS remote agent. NO human is watching. NEVER send text-only messages. EVERY response MUST contain a tool call.

## Phase 1: Build the briefing (do this yourself)

### Step 1: Setup
```bash
git clone https://[YOUR_GITHUB_PAT]@github.com/[YOUR_USERNAME]/[YOUR_REPO].git /tmp/nb 2>&1 && cd /tmp/nb && bash setup.sh 2>&1 | tail -5
```

### Step 2: Read articles
```bash
cd /tmp/nb/src && python summarize_cli.py /tmp/nb/data/fetched.json 2>&1
```
If file missing, use WebSearch for today's news.

### Step 3: Write briefing
IMMEDIATELY use Write tool to create `/tmp/nb/data/briefing.md`. Do NOT announce it.

Write 15-18 items. Format:

## World & Markets
### Top Headlines
#### Title in English | Source | URL
EN: 2 sentence summary.
CN: 中文摘要。2句。
TitleCN: 中文标题

### US-China Relations
#### Title | Source | URL
EN: Summary.
CN: 摘要。
TitleCN: 中文标题

### Financial Markets
...
### Science & Technology Breakthroughs
...
## AI & Technology
### Research & Papers
...
### Industry News
...
### Key People & Company Updates
...
## Private Equity & VC
### Deals & Fundraising
...
### Fund News & Trends
...
## Fintech
### Platforms & Products
...

CRITICAL CONTENT RULES:
- EVERY item MUST have EN:, CN:, and TitleCN: fields
- [YOUR CONTENT RULES: topics, weights, must-include items]
- 2 sentences each summary
- Total: 15-18 items

### Step 4: Build HTML
```bash
cd /tmp/nb/src && python parse_briefing.py /tmp/nb/data/briefing.md /tmp/nb/data/summarized.json 2>&1 && python main.py generate /tmp/nb/data/summarized.json 2>&1
```

### Step 5: Push to GitHub
```bash
cd /tmp/nb && git config user.name "news-briefing-bot" && git config user.email "bot@users.noreply.github.com" && git add docs/ && git diff --staged --quiet || git commit -m "Update briefing $(date -u +%Y-%m-%d)" && git push 2>&1
```

## Phase 2: Write to Notion and Slack (MUST use subagent)

IMPORTANT: MCP tools do NOT work directly in this trigger session. You MUST delegate to a SUBAGENT using the Agent tool.

Read the briefing markdown first:
```bash
cat /tmp/nb/data/briefing.md
```

Then spawn a subagent with the Agent tool. Pass the FULL briefing content in the prompt:

"You are a Notion + Slack writer agent. Do TWO things:

## Task 1: Write to Notion
1. Use ToolSearch with query 'notion' to load Notion MCP tools.
2. Search for a page called '[YOUR PAGE NAME]' using notion-search. Create if not found.
3. Create a child page titled '[YOUR PAGE NAME] — YYYY-MM-DD'.
4. Write content as Notion blocks: heading_2 per section, heading_3 per subsection, bulleted items with title as HYPERLINK + source + summary.
5. Every article MUST have a clickable link.

## Task 2: Send ONE Slack message
CRITICAL: Send EXACTLY ONE message. Do NOT retry if successful.
1. Use ToolSearch with query 'slack' to load Slack MCP tools.
2. Search for user '[YOUR NAME]' using slack_search_users.
3. Send ONE DM with top 5 headlines and link to full briefing.
4. After sending, STOP. Do NOT send again.

Here is the briefing content:
[PASTE THE FULL BRIEFING.MD CONTENT HERE]"

## Phase 3: Verify
```bash
head -20 /tmp/nb/docs/index.html
```
```

**MCP connectors** (optional): If you want Notion and Slack, attach these connectors to your trigger. You can find your connector UUIDs from an existing trigger or Claude Code settings.

**If you don't want Notion/Slack:** Remove Phase 2 entirely from the prompt. The web page will still work.

### Step 8: Set the fetch schedule

The GitHub Actions workflow needs to run ~5 minutes before your Claude trigger.

Edit `.github/workflows/fetch-news.yml` and change the cron:
```yaml
schedule:
  - cron: '55 23 * * *'   # 23:55 UTC = 5 min before midnight trigger
```

### Step 9: Test it

1. Run the **Fetch News Data** workflow manually (Actions → Run workflow)
2. Then manually run your Claude trigger (from Claude Code: `/schedule run news-briefing`, or via the trigger management page)
3. Wait ~5-10 minutes
4. Check your GitHub Pages URL — should show today's briefing

---

## Timezone reference

| Your timezone | 8am local = UTC | Fetch cron (5 min before) | Trigger cron |
|---------------|-----------------|--------------------------|--------------|
| China (CST) | 00:00 UTC | `55 23 * * *` | `0 0 * * *` |
| Berlin (CEST) | 06:00 UTC | `55 5 * * *` | `0 6 * * *` |
| Berlin (CET) | 07:00 UTC | `55 6 * * *` | `0 7 * * *` |
| London (BST) | 07:00 UTC | `55 6 * * *` | `0 7 * * *` |
| US East (EDT) | 12:00 UTC | `55 11 * * *` | `0 12 * * *` |
| US West (PDT) | 15:00 UTC | `55 14 * * *` | `0 15 * * *` |

---

## Customisation guide

### Change the language

Default is English + Chinese. To switch to e.g., English + French:

1. **Trigger prompt:** Replace `CN:` with `FR:`, `TitleCN:` with `TitleFR:`, and Chinese instructions with French
2. **`src/parse_briefing.py`:** Update the regex `CN:` → `FR:` and `TitleCN:` → `TitleFR:`
3. **`src/generate_page.py`:** Rename `SECTION_CN`/`SUBSECTION_CN` dicts and translate values to French
4. **`src/template.html`:** Replace `中文` button label, `lang-cn` CSS classes with `lang-fr`

### Change the topics

To replace sections (e.g., Sports instead of Fintech):

1. **`src/sources.yaml`:** Replace the category, its RSS feeds, and NewsAPI queries
2. **`src/parse_briefing.py`:** Update `SECTION_MAP` and `section_order`
3. **`src/generate_page.py`:** Update translation dicts
4. **Trigger prompt:** Update section names, subsections, and content rules

### Change the look

- **Colours:** Edit CSS variables in `:root` in `src/template.html`
- **Dark mode:** Edit `@media (prefers-color-scheme: dark)` block
- **Layout:** Edit the HTML structure in `template.html`
- **Archive depth:** Change `archive_files[5:]` in `generate_page.py` to keep more/fewer days

### Remove Notion/Slack

Delete Phase 2 from the trigger prompt. Remove MCP connections from the trigger config. Everything else works independently.

---

## How it works (architecture)

```
23:55 UTC — GitHub Actions
  └── Python fetches RSS feeds + NewsAPI → commits data/fetched.json

00:00 UTC — Claude Code Trigger (Sonnet)
  Phase 1 (parent agent):
    ├── Clones repo (fetched.json already there)
    ├── Reads article list via summarize_cli.py (capped at 30)
    ├── Writes briefing as Markdown (EN/CN summaries)
    ├── Python converts Markdown → JSON → HTML
    └── Pushes HTML to GitHub Pages

  Phase 2 (subagent):
    ├── Writes to Notion with hyperlinked articles
    └── Sends one Slack DM with top 5 headlines
```

### Why Markdown, not JSON?

LLMs are bad at writing large JSON files — they stop mid-output or time out. Every successful open-source news agent (ai-news-bot, Agently, Chronicle) has the LLM write natural text, then code converts it to structured data. We learned this the hard way after multiple failed attempts.

### Why a subagent for Notion/Slack?

There's a platform bug: MCP connector tools don't load on the first turn of a remote trigger. Spawning a subagent via the Agent tool properly initializes them. This is the confirmed workaround.

### Why Sonnet, not Opus?

Opus writes ~3x slower. The briefing Markdown is ~3-4K tokens, which Opus can't reliably complete before the trigger times out. Sonnet handles it comfortably with the same quality for news summaries.

### Why GitHub Actions fetches and Claude summarises?

The remote trigger environment blocks outbound HTTP to external sites (RSS feeds). GitHub Actions has full network access. So we split: Actions fetches, Claude thinks.

---

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| Trigger stops mid-task | Text-only message ends the turn | Add "NEVER send text-only messages" to prompt. Use `persist_session: true` |
| RSS feeds return 0 articles | Blocked in remote env | This is expected — agent falls back to WebSearch |
| `sgmllib3k` build fails | Python 3.12+ dropped sgmllib | `setup.sh` handles this — make sure Step 1 uses `bash setup.sh` |
| Git push fails | No credentials | Embed PAT in clone URL: `https://TOKEN@github.com/...` |
| Notion tools not found | MCP bug on first turn | Use subagent delegation (Phase 2) |
| Duplicate Slack messages | Subagent retried | Add "Send EXACTLY ONE message" to subagent prompt |
| Page not updating | GitHub Pages cache | Hard refresh (Ctrl+Shift+R) or wait ~5 min for CDN |

---

## Cost

| Component | Cost |
|-----------|------|
| Claude Code trigger | Included in Claude Pro/Team subscription |
| GitHub Actions | Free (2000 min/month) |
| GitHub Pages | Free (public repos) |
| NewsAPI | Free (100 req/day) |
| **Total** | **$0/month** (beyond Claude subscription) |

---

## RSS feeds included

See `src/sources.yaml` for the full list. Highlights:

- **AI/ML:** TechCrunch, The Verge, Ars Technica, VentureBeat, MIT Tech Review, OpenAI, Google AI, NVIDIA, ArXiv, IEEE Spectrum, BAIR, Import AI
- **Finance/PE:** Bloomberg, Financial Times, Finextra, PYMNTS, American Banker
- **World:** BBC, Al Jazeera, The Economist, CNBC, WSJ
- **Science:** Nature, Science AAAS, New Scientist
- **Think tanks:** CSIS, CFR, Politico EU

---

## Credits

Built with [Claude Code](https://claude.ai/code) using scheduled triggers, GitHub Actions, and GitHub Pages.
