#!/usr/bin/env python3
"""
News Curator - Main orchestration script.
Collects, scores, ranks, and generates news digests.
"""

import os
import sys
import argparse
from pathlib import Path

import yaml
from dotenv import load_dotenv

from collector import ArticleCollector
from scorer import LLMScorer
from ranker import ArticleRanker
from generator import MarkdownGenerator


def load_config(config_path: str):
    """Load YAML configuration file."""
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='News Curator - AI-powered news digest generator')
    parser.add_argument('--profile', type=str, help='Specific profile to run (default: all profiles)')
    parser.add_argument('--dry-run', action='store_true', help='Run without saving files or updating tracking')
    parser.add_argument('--limit', type=int, help='Limit number of articles to process per profile (for testing)')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Fix for conflicting ANTHROPIC_BASE_URL environment variable
    if 'ANTHROPIC_BASE_URL' in os.environ and not os.environ['ANTHROPIC_BASE_URL']:
        del os.environ['ANTHROPIC_BASE_URL']

    # Get project root (parent of src/)
    project_root = Path(__file__).parent.parent

    # Paths
    config_dir = project_root / 'config'
    data_dir = project_root / 'data'
    output_dir = project_root / 'digests'

    sources_path = config_dir / 'sources.yaml'
    profiles_path = config_dir / 'profiles.yaml'
    limits_path = config_dir / 'limits.yaml'
    sent_articles_path = data_dir / 'sent_articles.json'

    # Load configurations
    print("Loading configurations...")
    profiles_config = load_config(profiles_path)
    limits_config = load_config(limits_path)

    # Get API keys
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    nyt_key = os.getenv('NYT_API_KEY')

    if not anthropic_key:
        print("❌ Error: ANTHROPIC_API_KEY not found in environment")
        sys.exit(1)

    # Initialize components
    print("Initializing components...")
    collector = ArticleCollector(str(sources_path), str(sent_articles_path), nyt_key)
    scorer = LLMScorer(anthropic_key, limits_config)
    ranker = ArticleRanker()
    generator = MarkdownGenerator(scorer, str(sent_articles_path))

    # Determine which profiles to run
    profiles = profiles_config['profiles']
    if args.profile:
        if args.profile not in profiles:
            print(f"❌ Error: Profile '{args.profile}' not found")
            sys.exit(1)
        profiles_to_run = {args.profile: profiles[args.profile]}
    else:
        profiles_to_run = profiles

    # Process each profile
    total_articles_processed = 0
    total_digests_generated = 0

    for profile_id, profile in profiles_to_run.items():
        print(f"\n{'='*70}")
        print(f"Processing profile: {profile['name']}")
        print(f"{'='*70}\n")

        try:
            # 1. Collect articles
            print("Step 1: Collecting articles...")
            source_ids = profile['sources']
            lookback_days = profile.get('lookback_days', 7)
            articles = collector.collect_articles(source_ids, lookback_days)

            if not articles:
                print("⚠️  No articles collected, skipping profile")
                continue

            print(f"✓ Collected {len(articles)} articles total\n")

            # Apply test limit if specified
            if args.limit:
                articles = articles[:args.limit]
                print(f"⚠️  [TEST MODE] Limited to {len(articles)} articles\n")

            # 2. Score articles
            print("Step 2: Scoring articles with Claude API...")
            scored_articles = scorer.score_articles(articles, profile)

            if not scored_articles:
                print("⚠️  No articles scored, skipping profile")
                continue

            print(f"✓ Scored {len(scored_articles)} articles\n")

            # 3. Rank and deduplicate
            print("Step 3: Ranking and deduplicating...")
            max_articles = profile.get('article_count', 10)
            max_per_cluster = profile.get('max_per_cluster', 2)
            min_relevance = profile.get('min_relevance', 40)
            min_per_source = profile.get('min_per_source', None)
            max_per_source = profile.get('max_per_source', None)
            selected_articles = ranker.rank_and_deduplicate(
                scored_articles,
                max_articles,
                max_per_cluster,
                min_relevance,
                min_per_source,
                max_per_source
            )

            if not selected_articles:
                print("⚠️  No articles selected, skipping profile")
                continue

            # 4. Generate digest
            print("\nStep 4: Generating digest...")
            digest_path = generator.generate_digest(
                selected_articles,
                profile,
                str(output_dir),
                dry_run=args.dry_run
            )

            if digest_path:
                total_articles_processed += len(selected_articles)
                total_digests_generated += 1

        except Exception as e:
            print(f"\n❌ Error processing profile '{profile_id}': {e}")
            import traceback
            traceback.print_exc()
            continue

    # Print summary
    print(f"\n{'='*70}")
    print("Summary")
    print(f"{'='*70}")

    stats = scorer.get_usage_stats()
    print(f"\nProfiles processed: {total_digests_generated}/{len(profiles_to_run)}")
    print(f"Total articles in digests: {total_articles_processed}")
    print(f"\nAPI Usage:")
    print(f"  Total API calls: {stats['calls_made']}")
    print(f"  Estimated cost: ${stats['estimated_cost']:.2f}")

    if stats['estimated_cost'] > limits_config['rate_limits']['cost_warning_threshold']:
        print(f"  ⚠️  WARNING: Cost exceeded ${limits_config['rate_limits']['cost_warning_threshold']} threshold!")

    if args.dry_run:
        print(f"\n[DRY RUN] No files saved, no tracking updated")

    print(f"\n✓ Done!\n")


if __name__ == '__main__':
    main()
