# News Curator - Complete Project Specification

## Project Overview

Build an AI-powered news curation system that:
- Collects articles from RSS feeds
- Scores and ranks them using Claude API based on relevance and importance
- Deduplicates using semantic topic clustering
- Generates weekly markdown digests
- Runs automatically via GitHub Actions

## Project Structure

```
news-curator/
├── config/
│   ├── profiles.yaml          # User-configurable news profiles
│   └── sources.yaml           # RSS feed definitions
├── data/
│   └── sent_articles.json     # Tracks sent articles to avoid duplicates
├── digests/
│   └── (generated .md files)  # Output directory for digests
├── src/
│   ├── __init__.py
│   ├── collector.py           # RSS feed collection
│   ├── scorer.py              # Claude API scoring
│   ├── ranker.py              # Ranking and deduplication
│   ├── generator.py           # Markdown generation
│   └── main.py                # Main orchestration
├── .github/
│   └── workflows/
│       └── digest.yml         # GitHub Actions workflow
├── requirements.txt
├── .env.example
└── README.md
```

## Technical Requirements

### Dependencies (requirements.txt)
```
feedparser==6.0.10
anthropic==0.39.0
python-dateutil==2.8.2
pyyaml==6.0.1
requests==2.31.0
python-dotenv==1.0.0
```

### Environment Variables
- `ANTHROPIC_API_KEY` - Required for Claude API access

## Configuration Files

### config/profiles.yaml

Format:
```yaml
profiles:
  profile_name:
    name: "Display Name"
    description: "Profile description"
    keywords: [list, of, keywords, to, match]
    sources: [source_id1, source_id2]  # References sources.yaml
    article_count: 10
    schedule: "0 18 * * 0"  # Cron syntax (UTC)
    lookback_days: 7
    max_per_cluster: 2
    summary:
      sentence_count: 2
      instructions: "Custom instructions for summary generation"
```

**Required Profiles:**

1. **career_news** - Media & Entertainment Industry News
   - Keywords: streaming platforms, Netflix, Disney+, HBO Max, Warner Bros Discovery, production technology, studio mergers, content distribution, entertainment technology
   - Sources: nyt_technology, the_verge, variety, deadline
   - Article count: 10
   - Schedule: Sunday 6 PM UTC
   - Summary: 2 sentences, focus on business impact and technology implications

2. **world_news** - World News Digest
   - Keywords: international affairs, major policy changes, global economy, significant world events, diplomatic developments
   - Sources: nyt_world, bbc_world, reuters
   - Article count: 10
   - Schedule: Sunday 6 PM UTC
   - Summary: 3 sentences, balanced and factual

### config/sources.yaml

Format:
```yaml
sources:
  source_id:
    name: "Source Display Name"
    url: "https://example.com/rss/feed.xml"
    credibility: 0.95  # 0-1 scale (for future use)
```

**Required Sources:**
- nyt_technology: New York Times Technology (https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml)
- nyt_world: New York Times World (https://rss.nytimes.com/services/xml/rss/nyt/World.xml)
- the_verge: The Verge (https://www.theverge.com/rss/index.xml)
- variety: Variety (https://variety.com/feed/)
- deadline: Deadline Hollywood (https://deadline.com/feed/)
- bbc_world: BBC World News (https://feeds.bbci.co.uk/news/world/rss.xml)
- reuters: Reuters (https://www.reutersagency.com/feed/)

### data/sent_articles.json

Initial structure:
```json
{
  "articles": []
}
```

Purpose: Track article links that have been included in previous digests to avoid sending duplicates.

## Core Components

### 1. collector.py (RSSCollector class)

**Purpose:** Fetch and parse RSS feeds

**Key Methods:**
- `__init__(sources_path, sent_articles_path)` - Load sources and sent articles tracker
- `collect_articles(source_ids, lookback_days)` - Collect articles from specified sources

**Logic:**
1. Load sources from sources.yaml
2. Load sent articles history from JSON
3. For each source ID:
   - Fetch RSS feed using feedparser
   - Parse entries
   - Filter by date (only articles within lookback_days)
   - Skip articles already in sent_articles.json
   - Create Article objects with: title, link, summary, published date, source name
4. Return list of Article objects

**Article Object Properties:**
- title, link, summary, published, source_name
- score, relevance_score, importance_score (set by scorer)
- topic_cluster, main_topic, reasoning (set by scorer)
- generated_summary (set by generator)

### 2. scorer.py (LLMScorer class)

**Purpose:** Score articles using Claude API and identify topic clusters

**Key Methods:**
- `__init__()` - Initialize Anthropic client with API key
- `score_articles(articles, profile)` - Score all articles for a profile
- `_score_single_article(article, keywords, profile)` - Score individual article
- `generate_summary(article, profile)` - Generate brief summary

**Scoring Logic:**
1. For each article, send to Claude API with prompt:
   ```
   Analyze this article for a news digest.
   
   Title: {title}
   Summary: {summary}
   Source: {source}
   
   Profile keywords: {keywords}
   
   Respond with ONLY JSON:
   {
     "relevance_score": 0-100,
     "importance_score": 0-100,
     "main_topic": "2-4 word topic label",
     "topic_cluster": "slug like 'streaming_mergers'",
     "reasoning": "1-2 sentence explanation"
   }
   ```

2. Parse JSON response and set article properties
3. Calculate final score: `(relevance * 0.6) + (importance * 0.4)`
4. Use Claude Sonnet 4 model: `claude-sonnet-4-20250514`

**Summary Generation:**
- Use profile's summary.sentence_count and summary.instructions
- Generate concise summary based on article content
- Fallback to truncated original summary if API fails

### 3. ranker.py (ArticleRanker class)

**Purpose:** Rank articles and enforce diversity via deduplication

**Key Methods:**
- `rank_and_deduplicate(articles, max_articles, max_per_cluster)` - Select top articles with diversity

**Logic:**
1. Sort all articles by final score (descending)
2. Group articles by topic_cluster
3. Selection strategy:
   - First pass: Take top N articles from each cluster (up to max_per_cluster per cluster)
   - Continue until we have max_articles total
   - Second pass: If still need more, take highest scoring regardless of cluster
4. Return selected articles (limit to max_articles)

**Default Settings:**
- max_per_cluster: 2 (no more than 2 articles on same topic)
- Ensures diversity across different topics

### 4. generator.py (MarkdownGenerator class)

**Purpose:** Generate markdown digest files and track sent articles

**Key Methods:**
- `__init__(scorer, sent_articles_path)` - Initialize with scorer reference
- `generate_digest(articles, profile, output_dir)` - Create markdown file
- `_build_markdown(articles, profile, date_str)` - Format markdown content
- `_update_sent_articles(article_links)` - Update tracking file

**Markdown Format:**
```markdown
# {Profile Name}
*Generated on {date}*

{Profile description}

**Top {N} Articles**

---

## 1. {Article Title}

**Source:** {Source Name}
**Published:** {Date}
**Relevance Score:** {X}/100 | **Importance Score:** {Y}/100
**Topic:** {Main Topic}

**Summary:** {Generated summary}

[Read full article]({URL})

---

## 2. ...

---

*Digest generated by News Curator on {timestamp}*
```

**File Naming:**
- Format: `{YYYY-MM-DD}-{profile-slug}.md`
- Example: `2024-12-22-media-and-entertainment-industry-news.md`
- Saved to `digests/` directory

**Tracking Logic:**
1. After generating digest, extract all article links
2. Load existing sent_articles.json
3. Add new links to the set
4. Save updated JSON

### 5. main.py

**Purpose:** Orchestrate the entire pipeline

**Features:**
- Command-line arguments: `--profile {name}`, `--dry-run`
- Load environment variables from .env
- Load profiles from config/profiles.yaml
- Initialize all components
- Process each profile (or specific profile if specified)

**Pipeline Flow:**
1. Collect articles (RSSCollector)
2. Score articles (LLMScorer)
3. Rank and deduplicate (ArticleRanker)
4. Generate digest (MarkdownGenerator)

**Error Handling:**
- Continue on individual article errors
- Print warnings for missing sources
- Skip profiles with no articles

## GitHub Actions Workflow

### .github/workflows/digest.yml

**Triggers:**
- Scheduled: Every Sunday at 6 PM UTC (`0 18 * * 0`)
- Manual: workflow_dispatch

**Steps:**
1. Checkout repository
2. Set up Python 3.11
3. Install dependencies from requirements.txt
4. Run main.py with ANTHROPIC_API_KEY from secrets
5. Commit generated digests and updated sent_articles.json
6. Push to repository

**Git Configuration:**
- Author: GitHub Action (action@github.com)
- Commit message: "Add weekly news digest [automated]"

**Required Secret:**
- `ANTHROPIC_API_KEY` - Must be added to repository secrets

## Additional Files

### .env.example
```
ANTHROPIC_API_KEY=your_api_key_here
```

### README.md

Should include:
- Project description and features
- Setup instructions (clone, install, configure)
- Local testing commands
- GitHub Actions deployment steps
- Configuration guide (profiles, sources, cron syntax)
- Troubleshooting section
- Cost estimates (~$2-5/month for Claude API)
- Future enhancement ideas

## Testing Instructions

**Local Testing:**
```bash
# Install dependencies
pip install -r requirements.txt

# Create .env file with API key
cp .env.example .env
# Edit .env to add actual API key

# Test with dry run (no file generation)
python src/main.py --profile career_news --dry-run

# Generate actual digest
python src/main.py --profile career_news

# Run all profiles
python src/main.py
```

**Expected Behavior:**
1. Fetches articles from RSS feeds
2. Filters by date and sent history
3. Scores each article using Claude API
4. Groups by topic cluster
5. Selects top articles with diversity
6. Generates summaries
7. Creates markdown file in digests/
8. Updates sent_articles.json

## Design Principles

1. **Configurability:** All key parameters in YAML (no hardcoded values)
2. **Extensibility:** Easy to add new profiles and sources
3. **Simplicity:** Minimal dependencies, no database required
4. **Cost-Effective:** ~$2-5/month for typical usage
5. **Reliability:** Error handling for API failures and missing feeds
6. **Automation:** Fully automated via GitHub Actions

## Key Constraints

- **No localStorage/sessionStorage** - Not applicable (backend system)
- **LLM Model:** Use Claude Sonnet 4 (`claude-sonnet-4-20250514`)
- **No email delivery** (MVP) - Markdown files only
- **Free hosting** - GitHub Actions (2000 min/month free tier)
- **Deduplication:** Max 2 articles per topic cluster by default
- **Lookback:** 7 days default, configurable per profile

## Success Criteria

- ✅ Collects articles from all configured RSS feeds
- ✅ Scores relevance and importance using Claude API
- ✅ Identifies topic clusters for deduplication
- ✅ Generates clean, readable markdown digests
- ✅ Avoids sending duplicate articles across weeks
- ✅ Runs automatically on schedule via GitHub Actions
- ✅ Costs under $5/month
- ✅ Configurable for multiple use cases without code changes

## Future Enhancements (Not in MVP)

- Email delivery via SendGrid/SES
- Web UI for configuration
- Learning from user feedback
- Support for social media sources
- Multi-language support
- Sentiment analysis
- Custom scoring weights per profile