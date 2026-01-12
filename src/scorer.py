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
                success = self._score_single_article(article, keywords, profile)

                # Only include successfully scored articles
                if success:
                    scored_articles.append(article)
                    print(f"  Scored {i}/{len(articles_to_score)}: {article.title[:60]}...")
                else:
                    print(f"  ⚠️  Skipped article (scoring failed): {article.title[:60]}...")

            except RateLimitExceeded as e:
                print(f"\n⚠️  {e}")
                print(f"  Processed {i-1}/{len(articles_to_score)} articles before hitting limit")
                break
            except Exception as e:
                print(f"  ⚠️  Error scoring article: {e}")
                continue

        return scored_articles

    def _score_single_article(self, article: Article, keywords: List[str], profile: Dict) -> bool:
        """Score a single article. Returns True if successful, False otherwise."""
        # Build prompt
        profile_description = profile.get('description', 'a news digest')

        # Check if this is from a preferred source
        preferred_sources = profile.get('preferred_sources', [])
        source_note = ""
        if article.source_name in preferred_sources:
            source_note = f"\n\n**NOTE: This article is from {article.source_name}, a PREFERRED SOURCE. Give it higher weight.**"

        prompt = f"""Analyze this article for a news digest.

AUDIENCE & PURPOSE:
{profile_description}

ARTICLE:
Title: {article.title}
Summary: {article.summary}
Source: {article.source_name}{source_note}

SCORING INSTRUCTIONS:

Relevance Score (how well it matches the audience's interests):
- 90-100: Directly addresses their top priorities (see AUDIENCE above)
- 70-89: Important to their industry/domain; includes INDIRECT impacts (e.g., tech industry news affects Netflix, media industry editorial decisions show industry trends)
- 50-69: Related but not central
- 30-49: Tangential connection
- 0-29: Little to no relevance

Importance Score (significance of the news itself):
- 90-100: Major breaking news, game-changing developments, critical events
- 70-89: Significant developments, important announcements, notable policy changes
- 50-69: Moderate news value, incremental updates
- 30-49: Minor updates, routine announcements
- 0-29: Trivial news, minor updates

CRITICAL REMINDERS:
- **INDIRECT IMPACTS MATTER**: Tech industry policy/workforce issues affect Netflix. Media industry editorial decisions show industry trends. Platform content policies affect the streaming ecosystem.
- **THINK BROADLY**: The audience cares about the full picture (read all their priorities above), not just direct mentions
- **PREFERRED SOURCES GET BONUS**: When comparing similar articles, prefer NYT
- **FILTER OUT**: Political gossip (salacious details, personal scandals without policy impact), celebrity gossip, minor product updates
- **OPINION PIECES OK**: Keep opinion pieces if they have substantive policy analysis or business insights

CRITICAL CLUSTERING RULES:
- Use BROAD topic clusters (1-2 words max): "venezuela", "israel-palestine", "ukraine-russia", "us-politics", "climate", "economy", "streaming-wars", "netflix"
- Do NOT create sub-variants: use "venezuela" NOT "venezuela-regime-change" or "venezuela-political-crisis"
- Similar stories = SAME cluster: All Venezuela coverage -> "venezuela", all Middle East conflict -> "middle-east", all Netflix news -> "netflix"
- Think: "Would a newspaper put these in the same section?" If yes, same cluster.

Respond with ONLY valid JSON (no markdown, no code blocks):
{{
  "relevance_score": 0-100,
  "importance_score": 0-100,
  "main_topic": "2-4 word topic label",
  "topic_cluster": "broad_single_topic",
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

            # Boost scores for NYT Most Popular articles
            if article.is_most_popular:
                article.relevance_score = min(100, article.relevance_score + 10)
                article.importance_score = min(100, article.importance_score + 10)

            # Calculate final score
            article.score = (article.relevance_score * 0.6) + (article.importance_score * 0.4)
            return True

        except json.JSONDecodeError as e:
            print(f"  ⚠️  Failed to parse JSON response: {e}")
            # Don't include failed articles
            return False

    def generate_summary(self, article: Article, profile: Dict) -> str:
        """Generate a summary for an article."""
        # Check if article has meaningful content to summarize
        summary_text = (article.summary or "").strip()
        if not summary_text or len(summary_text) < 50:
            return "No preview available."

        # Check for placeholder/empty content patterns that indicate no real summary
        no_content_patterns = [
            "no summary available",
            "no description available",
            "no abstract available",
            "no content available",
            "summary not available",
            "description not available",
            "content not available",
            "click to read",
            "read more",
            "continue reading",
            "full story at",
        ]
        summary_lower = summary_text.lower()
        if any(pattern in summary_lower for pattern in no_content_patterns):
            return "No preview available."

        # Check if summary is too similar to title (just a subtitle/tagline, not real content)
        title_lower = article.title.lower()
        # If summary is short and mostly overlaps with title, it's not useful
        if len(summary_text) < 150:
            # Check word overlap - if most words are from the title, skip
            title_words = set(title_lower.split())
            summary_words = set(summary_lower.split())
            if title_words and summary_words:
                overlap = len(title_words & summary_words) / len(summary_words)
                if overlap > 0.7:  # 70%+ overlap means it's basically the title
                    return "No preview available."

        self._check_rate_limit()

        sentence_count = profile.get('summary', {}).get('sentence_count', 2)
        instructions = profile.get('summary', {}).get('instructions', '')

        prompt = f"""Generate a concise {sentence_count}-sentence summary of this article.

Title: {article.title}
Content: {article.summary}

Instructions: {instructions}

Respond with ONLY the summary text (no introduction, no markdown). If there is not enough content to summarize, respond with exactly: NO_CONTENT"""

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
            generated = response.content[0].text.strip()

            # Check if LLM indicated insufficient content
            if generated == "NO_CONTENT":
                return "No preview available."

            # Check if LLM generated meta-commentary instead of a summary
            meta_patterns = [
                "i notice",
                "i cannot",
                "i can't",
                "without the full",
                "without access",
                "only the title",
                "not enough content",
                "not enough information",
                "insufficient content",
                "insufficient information",
                "to generate a summary",
                "to create a summary",
                "would need access",
                "would need the full",
            ]
            generated_lower = generated.lower()
            if any(pattern in generated_lower for pattern in meta_patterns):
                return "No preview available."

            return generated

        except Exception as e:
            print(f"  ⚠️  Error generating summary: {e}")
            # Fallback to truncated original summary (or no preview if too short)
            if len(summary_text) < 50:
                return "No preview available."
            return article.summary[:200] + "..." if len(article.summary) > 200 else article.summary

    def generate_executive_summary(self, articles: List[Article], profile: Dict) -> str:
        """Generate an executive summary of all articles in the digest."""
        self._check_rate_limit()

        # Build article overview for the prompt
        article_summaries = []
        for i, article in enumerate(articles, 1):
            article_summaries.append(
                f"{i}. {article.title}\n"
                f"   Topic: {article.main_topic}\n"
                f"   Summary: {article.summary[:200]}..."
            )

        articles_text = "\n\n".join(article_summaries)
        profile_name = profile.get('name', 'News Digest')

        prompt = f"""You are creating an executive summary for a news digest called "{profile_name}".

Below are the {len(articles)} articles selected for this week's digest. Generate a 4-6 sentence executive summary that:
- Captures the overall themes and trends from these articles
- Highlights what's "going on" in the news this week
- Doesn't need to mention every article, but should represent the key stories and patterns
- Is written in an engaging, journalistic style
- Provides context and connections between stories where relevant

ARTICLES:
{articles_text}

Respond with ONLY the executive summary text (no introduction, no markdown, no heading)."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=500,
                temperature=0.7,
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                timeout=self.timeout
            )

            self.api_calls_made += 1
            return response.content[0].text.strip()

        except Exception as e:
            print(f"  ⚠️  Error generating executive summary: {e}")
            # Fallback to simple description
            return f"This week's digest covers {len(articles)} articles across topics including {', '.join(set(a.main_topic for a in articles[:3]))}."

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
