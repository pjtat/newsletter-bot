"""
Email digest delivery via SendGrid
"""
import os
import sys
import re
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email
from pathlib import Path


def convert_markdown_to_html(markdown_text: str) -> str:
    """Convert markdown digest to nicely formatted HTML."""

    lines = markdown_text.split('\n')
    html_parts = []

    # Start HTML with styling
    html_parts.append("""
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
                line-height: 1.6;
                color: #24292e;
                max-width: 700px;
                margin: 0 auto;
                padding: 20px;
                background-color: #ffffff;
            }
            .header {
                border-bottom: 3px solid #0366d6;
                padding-bottom: 20px;
                margin-bottom: 30px;
            }
            .header h1 {
                color: #0366d6;
                font-size: 28px;
                margin: 0 0 8px 0;
                font-weight: 600;
            }
            .header .date {
                color: #586069;
                font-size: 14px;
                font-style: italic;
            }
            .article {
                margin-bottom: 35px;
                padding: 20px;
                background-color: #f6f8fa;
                border-radius: 6px;
                border-left: 4px solid #0366d6;
            }
            .article h2 {
                color: #24292e;
                font-size: 20px;
                margin: 0 0 12px 0;
                font-weight: 600;
                line-height: 1.3;
            }
            .article-meta {
                color: #586069;
                font-size: 13px;
                margin-bottom: 8px;
                display: flex;
                flex-wrap: wrap;
                gap: 15px;
            }
            .meta-item {
                display: inline-block;
            }
            .scores {
                margin: 10px 0;
                padding: 8px 12px;
                background-color: #fff;
                border-radius: 4px;
                font-size: 13px;
            }
            .score-badge {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: 600;
                margin-right: 8px;
            }
            .relevance {
                background-color: #d1f0ff;
                color: #0366d6;
            }
            .importance {
                background-color: #fff5b1;
                color: #735c0f;
            }
            .topic {
                background-color: #f1f8ff;
                padding: 4px 10px;
                border-radius: 3px;
                font-size: 12px;
                color: #0366d6;
                display: inline-block;
                margin: 8px 0;
                font-weight: 500;
            }
            .summary {
                color: #24292e;
                font-size: 15px;
                line-height: 1.6;
                margin: 12px 0;
            }
            .read-more {
                display: inline-block;
                margin-top: 12px;
                color: #0366d6;
                text-decoration: none;
                font-weight: 500;
                font-size: 14px;
            }
            .read-more:hover {
                text-decoration: underline;
            }
            .footer {
                margin-top: 40px;
                padding-top: 20px;
                border-top: 1px solid #e1e4e8;
                color: #586069;
                font-size: 12px;
                text-align: center;
            }
            hr {
                display: none;
            }
        </style>
    </head>
    <body>
    """)

    in_article = False
    article_num = None
    current_article = {}

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Main title
        if line.startswith('# ') and not in_article:
            title = line.replace('# ', '')
            html_parts.append(f'<div class="header"><h1>{title}</h1>')

        # Date line
        elif line.startswith('*Generated'):
            date = line.strip('*')
            html_parts.append(f'<div class="date">{date}</div></div>')

        # Article number (## 1. Title)
        elif re.match(r'^## \d+\. ', line):
            # Save previous article if exists
            if in_article and current_article:
                html_parts.append(format_article(current_article))

            # Start new article
            in_article = True
            article_title = re.sub(r'^## \d+\. ', '', line)
            current_article = {'title': article_title, 'meta': {}}

        # Source, Published, Scores
        elif line.startswith('**Source:**') and in_article:
            current_article['meta']['source'] = line.replace('**Source:**', '').strip()
        elif line.startswith('**Published:**') and in_article:
            current_article['meta']['published'] = line.replace('**Published:**', '').strip()
        elif 'Relevance Score:' in line and 'Importance Score:' in line:
            # Extract scores
            scores = re.findall(r'(\d+)/100', line)
            if len(scores) >= 2:
                current_article['meta']['relevance'] = scores[0]
                current_article['meta']['importance'] = scores[1]
        elif line.startswith('**Topic:**') and in_article:
            current_article['meta']['topic'] = line.replace('**Topic:**', '').strip()

        # Summary
        elif line.startswith('**Summary:**') and in_article:
            summary = line.replace('**Summary:**', '').strip()
            current_article['summary'] = summary

        # Read full article link
        elif line.startswith('[Read full article]') and in_article:
            link_match = re.search(r'\((.*?)\)', line)
            if link_match:
                current_article['link'] = link_match.group(1)

        i += 1

    # Add last article
    if in_article and current_article:
        html_parts.append(format_article(current_article))

    # Footer
    html_parts.append("""
        <div class="footer">
            🤖 Generated with Claude Code
        </div>
    </body>
    </html>
    """)

    return ''.join(html_parts)


def format_article(article: dict) -> str:
    """Format a single article as HTML."""
    html = ['<div class="article">']

    # Title
    html.append(f'<h2>{article.get("title", "")}</h2>')

    # Meta info
    meta = article.get('meta', {})
    if meta:
        html.append('<div class="article-meta">')
        if 'source' in meta:
            html.append(f'<span class="meta-item"><strong>Source:</strong> {meta["source"]}</span>')
        if 'published' in meta:
            # Format date nicely
            pub = meta['published'].replace(' UTC', '').split(' ')[0]
            html.append(f'<span class="meta-item"><strong>Published:</strong> {pub}</span>')
        html.append('</div>')

        # Scores
        if 'relevance' in meta and 'importance' in meta:
            html.append('<div class="scores">')
            html.append(f'<span class="score-badge relevance">Relevance: {meta["relevance"]}/100</span>')
            html.append(f'<span class="score-badge importance">Importance: {meta["importance"]}/100</span>')
            html.append('</div>')

        # Topic
        if 'topic' in meta:
            html.append(f'<div class="topic">📌 {meta["topic"]}</div>')

    # Summary
    if 'summary' in article:
        html.append(f'<div class="summary">{article["summary"]}</div>')

    # Link
    if 'link' in article:
        html.append(f'<a href="{article["link"]}" class="read-more">Read full article →</a>')

    html.append('</div>')
    return ''.join(html)


def send_digest_email(digest_file_path: str, recipient_email: str, from_email: str = None):
    """Send digest via email using SendGrid."""

    # Read digest content
    with open(digest_file_path, 'r') as f:
        digest_content = f.read()

    # Use environment variable for from_email if not provided
    if not from_email:
        from_email = os.environ.get('SENDGRID_FROM_EMAIL', 'noreply@newsletterbot.com')

    # Parse markdown and convert to HTML
    html_content = convert_markdown_to_html(digest_content)

    # Extract title for subject
    title = digest_content.split('\n')[0].replace('# ', '')

    # Create email with sender name
    message = Mail(
        from_email=Email(from_email, 'Newsletter Bot'),
        to_emails=recipient_email,
        subject=f'📰 {title}',
        html_content=html_content
    )

    try:
        api_key = os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            print("❌ Error: SENDGRID_API_KEY environment variable not set")
            return False

        sg = SendGridAPIClient(api_key)
        response = sg.send(message)
        print(f"✓ Email sent to {recipient_email}! Status: {response.status_code}")
        print(f"  Subject: 📰 {title}")
        return True
    except Exception as e:
        print(f"⚠️  Error sending email: {e}")
        return False


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python email_sender.py <digest_file> <recipient_email> [from_email]")
        sys.exit(1)

    digest_file = sys.argv[1]
    recipient = sys.argv[2]
    from_email = sys.argv[3] if len(sys.argv) > 3 else None

    success = send_digest_email(digest_file, recipient, from_email)
    sys.exit(0 if success else 1)
