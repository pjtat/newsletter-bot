"""
Article ranking and deduplication.
Ensures diversity by limiting articles per topic cluster.
"""

from typing import List, Dict
from collections import defaultdict

from collector import Article


class ArticleRanker:
    """Ranks articles and enforces diversity via topic clustering."""

    def rank_and_deduplicate(self, articles: List[Article], max_articles: int, max_per_cluster: int = 2) -> List[Article]:
        """
        Select top articles with diversity constraints.

        Args:
            articles: List of scored articles
            max_articles: Maximum number of articles to return
            max_per_cluster: Maximum articles per topic cluster

        Returns:
            Selected articles with diversity
        """
        if not articles:
            return []

        # Sort by score (descending)
        sorted_articles = sorted(articles, key=lambda a: a.score, reverse=True)

        # Group by topic cluster
        clusters = defaultdict(list)
        for article in sorted_articles:
            cluster = article.topic_cluster or "uncategorized"
            clusters[cluster].append(article)

        # Selection strategy: ensure diversity
        selected = []
        cluster_counts = defaultdict(int)

        # First pass: Take top articles from each cluster (up to max_per_cluster)
        for article in sorted_articles:
            if len(selected) >= max_articles:
                break

            cluster = article.topic_cluster or "uncategorized"

            # Check if we can add more from this cluster
            if cluster_counts[cluster] < max_per_cluster:
                selected.append(article)
                cluster_counts[cluster] += 1

        # Second pass: If we still need more, take highest scoring regardless of cluster
        if len(selected) < max_articles:
            for article in sorted_articles:
                if len(selected) >= max_articles:
                    break

                if article not in selected:
                    selected.append(article)

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
