# News Curator

An AI-powered news curation system that automatically collects, scores, and generates weekly digest summaries from RSS feeds and news APIs using Claude.

## Features

- 📰 **Multi-source collection** - RSS feeds and NYT API support
- 🤖 **AI-powered scoring** - Claude API analyzes relevance and importance
- 🎯 **Smart deduplication** - Topic clustering ensures diverse coverage
- 📊 **Cost protection** - Rate limiting and budget safeguards
- ⏰ **Automated delivery** - GitHub Actions runs weekly on schedule
- 🎨 **Clean markdown output** - Readable digest files

## Quick Start

### Prerequisites

- Python 3.11+
- Anthropic API key ([Get one here](https://console.anthropic.com/))
- (Optional) NYT API key ([Get one here](https://developer.nytimes.com/))

### Installation

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd newsletter-bot
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment**
   ```bash
   cp .env.example .env
   # Edit .env and add your API keys
   ```

4. **Test locally**
   ```bash
   cd src
   python main.py --profile career_news --dry-run
   ```

## Configuration

### Profiles (`config/profiles.yaml`)

Profiles define what news you want to curate. Each profile specifies:

- **keywords** - Topics to match for relevance scoring
- **sources** - Which RSS/API sources to use
- **article_count** - How many articles in final digest
- **schedule** - When to run (cron syntax)
- **summary** - How to generate summaries

Example:
```yaml
profiles:
  career_news:
    name: "Media & Entertainment Industry News"
    keywords:
      - streaming platforms
      - Netflix
      - production technology
    sources:
      - variety
      - deadline
      - the_verge
    article_count: 10
    lookback_days: 7
```

### Sources (`config/sources.yaml`)

Define RSS feeds and API sources:

```yaml
sources:
  variety:
    name: "Variety"
    url: "https://variety.com/feed/"
    type: "rss"
    credibility: 0.90

  nyt_api:
    name: "New York Times"
    type: "api"
    api_type: "nyt"
    sections: ["technology", "world"]
```

### Rate Limits (`config/limits.yaml`)

Cost protection settings:

- `max_articles_per_profile: 50` - Limit articles processed
- `max_api_calls_per_run: 100` - Hard stop on API calls
- `cost_warning_threshold: 5.00` - Warn if cost exceeds $5

## Usage

### Local Testing

**Dry run (no files saved):**
```bash
python src/main.py --profile career_news --dry-run
```

**Test with limited articles:**
```bash
python src/main.py --profile career_news --limit 5
```

**Generate actual digest:**
```bash
python src/main.py --profile career_news
```

**Run all profiles:**
```bash
python src/main.py
```

### GitHub Actions Setup

1. **Add repository secrets**
   - Go to Settings → Secrets and variables → Actions
   - Add `ANTHROPIC_API_KEY`
   - (Optional) Add `NYT_API_KEY`

2. **Enable workflows**
   - Go to Actions tab
   - Enable workflows if prompted

3. **Test manual run**
   - Actions tab → "Generate News Digest"
   - Click "Run workflow"

4. **Scheduled runs**
   - Runs automatically every Sunday at 6 PM UTC
   - Adjust schedule in `.github/workflows/digest.yml`

## Output

Digests are saved to `digests/` as markdown files:

```
digests/2024-12-22-media-and-entertainment-industry-news.md
```

Each digest includes:
- Article title and source
- Relevance and importance scores
- Topic classification
- AI-generated summary
- Link to full article

Example:
```markdown
# Media & Entertainment Industry News
*Generated on 2024-12-22*

## 1. Netflix Announces New Streaming Feature

**Source:** The Verge
**Published:** 2024-12-20 14:30 UTC
**Relevance Score:** 95/100 | **Importance Score:** 85/100
**Topic:** Streaming Technology

**Summary:** Netflix rolls out enhanced viewing options...

[Read full article](https://example.com/article)
```

## Cost Estimates

Based on typical usage:

- **Per run:** ~40 API calls = $0.72
- **Weekly:** $0.72/week
- **Monthly:** ~$3/month

Protected by hard limits:
- Max 100 API calls per run
- Warning if cost exceeds $5
- Strict article limits per profile

## Project Structure

```
newsletter-bot/
├── config/
│   ├── profiles.yaml      # News profile definitions
│   ├── sources.yaml       # RSS/API source configs
│   └── limits.yaml        # Rate limit settings
├── data/
│   └── sent_articles.json # Tracks sent articles
├── digests/
│   └── *.md              # Generated digests
├── src/
│   ├── collector.py      # Article collection
│   ├── scorer.py         # Claude API scoring
│   ├── ranker.py         # Ranking/deduplication
│   ├── generator.py      # Markdown generation
│   └── main.py          # Main orchestration
└── .github/workflows/
    └── digest.yml       # GitHub Actions automation
```

## Customization

### Adding a New Profile

1. Edit `config/profiles.yaml`
2. Add your profile with keywords and sources
3. Test: `python src/main.py --profile your_profile --dry-run`

### Adding a New RSS Source

1. Edit `config/sources.yaml`
2. Add source with URL and metadata
3. Reference in a profile's `sources` list

### Changing Schedule

Edit `.github/workflows/digest.yml`:
```yaml
schedule:
  - cron: '0 9 * * 1'  # Every Monday at 9 AM UTC
```

[Cron syntax help](https://crontab.guru/)

## Troubleshooting

### "No articles collected"

- Check RSS feed URLs are valid
- Verify sources exist in `sources.yaml`
- Check date filters (articles must be within 7 days)

### "ANTHROPIC_API_KEY not found"

- Create `.env` file from `.env.example`
- Add your API key
- For GitHub Actions, add to repository secrets

### "Rate limit exceeded"

- Check `config/limits.yaml` settings
- Reduce `max_articles_to_score` in profiles
- Use `--limit N` flag for testing

### Articles not being filtered

- Verify `sent_articles.json` is being updated
- Check file permissions
- In dry-run mode, tracking is not updated

## Development

### Running Tests

```bash
# Test with 3 articles (low cost)
python src/main.py --limit 3 --dry-run

# Test specific profile
python src/main.py --profile world_news --limit 5
```

### Adding a New API Source

1. Create collector class in `collector.py`
2. Add source type to `sources.yaml`
3. Update `ArticleCollector.collect_articles()` to handle new type

## Future Enhancements

- Email delivery (SendGrid/SES)
- Web UI for configuration
- Additional news APIs
- Custom scoring weights per profile
- Multi-language support
- Sentiment analysis

## License

MIT License - feel free to use and modify

## Contributing

Issues and pull requests welcome!

---

**Estimated costs:** ~$3/month for typical usage
**Free tier:** GitHub Actions provides 2000 minutes/month free
