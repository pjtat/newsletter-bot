"""
Article ranking and deduplication.
Ensures diversity by limiting articles per topic cluster.
"""

from typing import List, Dict
from collections import defaultdict

from collector import Article


class ArticleRanker:
    """Ranks articles and enforces diversity via topic clustering."""

    def rank_and_deduplicate(self, articles: List[Article], max_articles: int, max_per_cluster: int = 2, min_relevance: int = 40, min_per_source: Dict[str, int] = None, max_per_source: Dict[str, int] = None) -> List[Article]:
        """
        Select top articles with diversity constraints.

        Args:
            articles: List of scored articles
            max_articles: Maximum number of articles to return
            max_per_cluster: Maximum articles per topic cluster
            min_relevance: Minimum relevance score to include (default: 40)
            min_per_source: Minimum articles per source (e.g., {"BBC World News": 3})
            max_per_source: Maximum articles per source (e.g., {"BBC World News": 5})

        Returns:
            Selected articles with diversity
        """
        if not articles:
            return []

        # Filter out low-relevance articles
        filtered_articles = [a for a in articles if a.relevance_score >= min_relevance]

        if len(filtered_articles) < len(articles):
            filtered_count = len(articles) - len(filtered_articles)
            print(f"  Filtered out {filtered_count} low-relevance articles (below {min_relevance}/100)")

        if not filtered_articles:
            print(f"  ⚠️  No articles meet minimum relevance threshold of {min_relevance}/100")
            return []

        # Sort by score (descending)
        sorted_articles = sorted(filtered_articles, key=lambda a: a.score, reverse=True)

        # Ensure minimum source diversity if specified
        selected = []
        cluster_counts = defaultdict(int)

        if min_per_source:
            # First, guarantee minimum from each specified source
            source_counts = defaultdict(int)
            remaining = list(sorted_articles)

            for source_name, min_count in min_per_source.items():
                source_articles = [a for a in remaining if a.source_name == source_name]
                to_add = min(min_count, len(source_articles))

                for i in range(to_add):
                    if source_articles[i] not in selected:
                        selected.append(source_articles[i])
                        source_counts[source_name] += 1
                        # Track cluster counts for articles we've already selected
                        cluster = source_articles[i].topic_cluster or "uncategorized"
                        cluster_counts[cluster] += 1
                        remaining.remove(source_articles[i])

            # Now use remaining slots for highest scoring articles
            sorted_articles = remaining

        # Group by topic cluster
        clusters = defaultdict(list)
        for article in sorted_articles:
            cluster = article.topic_cluster or "uncategorized"
            clusters[cluster].append(article)

        # Selection strategy: ensure diversity (continue building on min_per_source selections)

        # Track source counts for max_per_source enforcement
        source_counts = defaultdict(int)
        for article in selected:
            source_counts[article.source_name] += 1

        # First pass: Take top articles from each cluster (up to max_per_cluster)
        for article in sorted_articles:
            if len(selected) >= max_articles:
                break

            cluster = article.topic_cluster or "uncategorized"

            # Check max_per_source constraint
            if max_per_source and article.source_name in max_per_source:
                if source_counts[article.source_name] >= max_per_source[article.source_name]:
                    continue  # Skip this article, source limit reached

            # Check if we can add more from this cluster
            if cluster_counts[cluster] < max_per_cluster:
                selected.append(article)
                cluster_counts[cluster] += 1
                source_counts[article.source_name] += 1

        # Second pass: If we still need more, take highest scoring regardless of cluster
        if len(selected) < max_articles:
            for article in sorted_articles:
                if len(selected) >= max_articles:
                    break

                # Check max_per_source constraint
                if max_per_source and article.source_name in max_per_source:
                    if source_counts[article.source_name] >= max_per_source[article.source_name]:
                        continue  # Skip this article, source limit reached

                if article not in selected:
                    selected.append(article)
                    source_counts[article.source_name] += 1

        # Sort selected by score again
        selected = sorted(selected, key=lambda a: a.score, reverse=True)

        # Print cluster distribution
        print(f"\n✓ Selected {len(selected)} articles:")
        cluster_dist = defaultdict(int)
        for article in selected:
            cluster = article.topic_cluster or "uncategorized"
            cluster_dist[cluster] += 1

        for cluster, count in sorted(cluster_dist.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cluster}: {count} articles")

        return selected[:max_articles]
