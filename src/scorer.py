"""
Article scoring using Claude API.
Handles relevance/importance scoring and topic clustering.
"""

import json
import time
from typing import List, Dict

from anthropic import Anthropic

from collector import Article


class RateLimitExceeded(Exception):
    """Raised when API rate limit is exceeded."""
    pass


class LLMScorer:
    """Scores articles using Claude API with rate limiting."""

    def __init__(self, api_key: str, limits_config: Dict):
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-20250514"

        # Rate limiting
        self.api_calls_made = 0
        self.max_calls = limits_config['rate_limits']['max_api_calls_per_run']
        self.timeout = limits_config['rate_limits']['api_timeout_seconds']
        self.cost_per_call = limits_config['cost_estimates']['estimated_cost_per_call']

    def score_articles(self, articles: List[Article], profile: Dict) -> List[Article]:
        """Score all articles for a profile."""
        max_articles = profile.get('max_articles_to_score', 50)
        articles_to_score = articles[:max_articles]

        if len(articles) > max_articles:
            print(f"⚠️  Limiting to {max_articles} articles (rate limit protection)")

        keywords = profile.get('keywords', [])
        scored_articles = []

        for i, article in enumerate(articles_to_score, 1):
            try:
                self._check_rate_limit()
                self._score_single_article(article, keywords, profile)
                scored_articles.append(article)
                print(f"  Scored {i}/{len(articles_to_score)}: {article.title[:60]}...")

            except RateLimitExceeded as e:
                print(f"\n⚠️  {e}")
                print(f"  Processed {i-1}/{len(articles_to_score)} articles before hitting limit")
                break
            except Exception as e:
                print(f"  ⚠️  Error scoring article: {e}")
                continue

        return scored_articles

    def _score_single_article(self, article: Article, keywords: List[str], profile: Dict):
        """Score a single article."""
        # Build prompt
        keywords_str = ", ".join(keywords)
        prompt = f"""Analyze this article for a news digest.

Title: {article.title}
Summary: {article.summary}
Source: {article.source_name}

Profile keywords: {keywords_str}

Respond with ONLY valid JSON (no markdown, no code blocks):
{{
  "relevance_score": 0-100,
  "importance_score": 0-100,
  "main_topic": "2-4 word topic label",
  "topic_cluster": "slug_like_this",
  "reasoning": "1-2 sentence explanation"
}}"""

        # Call API
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.3,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                timeout=self.timeout
            )

            self.api_calls_made += 1

            # Parse response
            content = response.content[0].text
            data = json.loads(content)

            # Set article properties
            article.relevance_score = data.get('relevance_score', 0)
            article.importance_score = data.get('importance_score', 0)
            article.main_topic = data.get('main_topic', '')
            article.topic_cluster = data.get('topic_cluster', '')
            article.reasoning = data.get('reasoning', '')

            # Calculate final score
            article.score = (article.relevance_score * 0.6) + (article.importance_score * 0.4)

        except json.JSONDecodeError as e:
            print(f"  ⚠️  Failed to parse JSON response: {e}")
            # Set default values
            article.relevance_score = 0
            article.importance_score = 0
            article.score = 0

    def generate_summary(self, article: Article, profile: Dict) -> str:
        """Generate a summary for an article."""
        self._check_rate_limit()

        sentence_count = profile.get('summary', {}).get('sentence_count', 2)
        instructions = profile.get('summary', {}).get('instructions', '')

        prompt = f"""Generate a concise {sentence_count}-sentence summary of this article.

Title: {article.title}
Content: {article.summary}

Instructions: {instructions}

Respond with ONLY the summary text (no introduction, no markdown)."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=300,
                temperature=0.5,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                timeout=self.timeout
            )

            self.api_calls_made += 1
            return response.content[0].text.strip()

        except Exception as e:
            print(f"  ⚠️  Error generating summary: {e}")
            # Fallback to truncated original summary
            return article.summary[:200] + "..." if len(article.summary) > 200 else article.summary

    def _check_rate_limit(self):
        """Check if rate limit has been exceeded."""
        if self.api_calls_made >= self.max_calls:
            estimated_cost = self.api_calls_made * self.cost_per_call
            raise RateLimitExceeded(
                f"Hit rate limit: {self.api_calls_made} calls made. "
                f"Estimated cost: ${estimated_cost:.2f}"
            )

    def get_usage_stats(self) -> Dict:
        """Get API usage statistics."""
        return {
            'calls_made': self.api_calls_made,
            'estimated_cost': self.api_calls_made * self.cost_per_call
        }
