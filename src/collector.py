"""
Article collection from RSS feeds and APIs.
Handles fetching, filtering, and deduplication.
"""

import json
import os
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from difflib import SequenceMatcher

import feedparser
import requests
from dateutil import parser as date_parser


@dataclass
class Article:
    """Represents a news article with metadata and scoring info."""
    title: str
    link: str
    summary: str
    published: datetime
    source_name: str

    # Set by scorer
    score: float = 0.0
    relevance_score: int = 0
    importance_score: int = 0
    topic_cluster: str = ""
    main_topic: str = ""
    reasoning: str = ""

    # Set by generator
    generated_summary: str = ""


class RSSCollector:
    """Collects articles from RSS feeds."""

    def __init__(self, source_config: Dict, sent_articles: List[str]):
        self.source_config = source_config
        self.sent_articles_set = set(sent_articles)

    def fetch(self, lookback_days: int) -> List[Article]:
        """Fetch articles from RSS feed."""
        url = self.source_config['url']
        source_name = self.source_config['name']

        try:
            feed = feedparser.parse(url)
            articles = []
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)

            for entry in feed.entries:
                # Skip if already sent
                if entry.link in self.sent_articles_set:
                    continue

                # Parse published date
                published = self._parse_date(entry)
                if not published:
                    continue

                # Make published date timezone-aware if it isn't
                if published.tzinfo is None:
                    published = published.replace(tzinfo=timezone.utc)

                # Filter by date - only articles within lookback window
                if published < cutoff_date:
                    continue

                # Filter out articles published more than 7 days ago (strict cutoff)
                seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
                if published < seven_days_ago:
                    continue

                # Create article
                article = Article(
                    title=entry.get('title', ''),
                    link=entry.link,
                    summary=entry.get('summary', entry.get('description', '')),
                    published=published,
                    source_name=source_name
                )
                articles.append(article)

            return articles

        except Exception as e:
            print(f"⚠️  Error fetching RSS feed {source_name}: {e}")
            return []

    def _parse_date(self, entry) -> Optional[datetime]:
        """Parse date from RSS entry."""
        date_fields = ['published', 'updated', 'pubDate']

        for field in date_fields:
            if hasattr(entry, field):
                try:
                    date_str = getattr(entry, field)
                    return date_parser.parse(date_str)
                except:
                    continue

        return None


class NYTAPICollector:
    """Collects articles from New York Times API."""

    def __init__(self, api_key: str, source_config: Dict, sent_articles: List[str]):
        self.api_key = api_key
        self.source_config = source_config
        self.sent_articles_set = set(sent_articles)
        self.base_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"

    def fetch(self, lookback_days: int, sections: Optional[List[str]] = None) -> List[Article]:
        """Fetch articles from NYT API."""
        if not self.api_key:
            print("⚠️  NYT API key not provided, skipping NYT source")
            return []

        articles = []
        sections = sections or self.source_config.get('sections', ['world'])

        for section in sections:
            try:
                section_articles = self._fetch_section(section, lookback_days)
                articles.extend(section_articles)
            except Exception as e:
                print(f"⚠️  Error fetching NYT {section}: {e}")

        return articles

    def _fetch_section(self, section: str, lookback_days: int) -> List[Article]:
        """Fetch articles for a specific section."""
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=lookback_days)
        seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)

        # NYT API date format: YYYYMMDD
        begin_date = cutoff_date.strftime('%Y%m%d')

        params = {
            'api-key': self.api_key,
            'fq': f'section_name:("{section}")',
            'begin_date': begin_date,
            'sort': 'newest',
            'page': 0
        }

        try:
            response = requests.get(self.base_url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()

            articles = []
            docs = data.get('response', {}).get('docs', [])

            for doc in docs:
                # Skip if already sent
                url = doc.get('web_url', '')
                if url in self.sent_articles_set:
                    continue

                # Parse date
                pub_date_str = doc.get('pub_date', '')
                try:
                    published = date_parser.parse(pub_date_str)
                    # Make timezone-aware if it isn't
                    if published.tzinfo is None:
                        published = published.replace(tzinfo=timezone.utc)
                except:
                    continue

                # Filter by date - only articles within 7 days
                if published < seven_days_ago:
                    continue

                # Create article
                article = Article(
                    title=doc.get('headline', {}).get('main', ''),
                    link=url,
                    summary=doc.get('abstract', doc.get('lead_paragraph', '')),
                    published=published,
                    source_name=self.source_config['name']
                )
                articles.append(article)

            return articles

        except Exception as e:
            print(f"⚠️  Error fetching NYT API section {section}: {e}")
            return []


class ArticleCollector:
    """Main collector that orchestrates RSS and API sources."""

    def __init__(self, sources_path: str, sent_articles_path: str, nyt_api_key: Optional[str] = None):
        self.sources_path = sources_path
        self.sent_articles_path = sent_articles_path
        self.nyt_api_key = nyt_api_key

        # Load configurations
        with open(sources_path, 'r') as f:
            import yaml
            self.sources = yaml.safe_load(f)['sources']

        # Load sent articles
        with open(sent_articles_path, 'r') as f:
            data = json.load(f)
            self.sent_articles = data.get('articles', [])

    def collect_articles(self, source_ids: List[str], lookback_days: int) -> List[Article]:
        """Collect articles from specified sources."""
        all_articles = []

        for source_id in source_ids:
            if source_id not in self.sources:
                print(f"⚠️  Source '{source_id}' not found in sources.yaml")
                continue

            source = self.sources[source_id]
            source_type = source.get('type', 'rss')

            if source_type == 'rss':
                collector = RSSCollector(source, self.sent_articles)
                articles = collector.fetch(lookback_days)
                all_articles.extend(articles)
                print(f"✓ Collected {len(articles)} articles from {source['name']}")

            elif source_type == 'api' and source.get('api_type') == 'nyt':
                if not self.nyt_api_key:
                    print(f"⚠️  NYT API key not provided, skipping {source['name']}")
                    continue

                collector = NYTAPICollector(self.nyt_api_key, source, self.sent_articles)
                sections = source.get('sections', ['world'])
                articles = collector.fetch(lookback_days, sections)
                all_articles.extend(articles)
                print(f"✓ Collected {len(articles)} articles from {source['name']}")

        # Remove duplicate titles (95% similarity threshold)
        all_articles = self._deduplicate_by_title(all_articles)

        return all_articles

    def _deduplicate_by_title(self, articles: List[Article]) -> List[Article]:
        """Remove articles with very similar titles."""
        if not articles:
            return articles

        unique_articles = []
        seen_titles = []

        for article in articles:
            is_duplicate = False

            for seen_title in seen_titles:
                similarity = self._title_similarity(article.title, seen_title)
                if similarity >= 0.95:  # 95% similarity threshold
                    is_duplicate = True
                    break

            if not is_duplicate:
                unique_articles.append(article)
                seen_titles.append(article.title)

        removed_count = len(articles) - len(unique_articles)
        if removed_count > 0:
            print(f"✓ Removed {removed_count} duplicate articles (title similarity)")

        return unique_articles

    def _title_similarity(self, title1: str, title2: str) -> float:
        """Calculate similarity between two titles."""
        return SequenceMatcher(None, title1.lower(), title2.lower()).ratio()
