"""
Send digest to Slack via webhook
"""
import os
import requests

def send_to_slack(digest_file_path: str, webhook_url: str = None):
    """Send digest to Slack channel via webhook."""

    webhook_url = webhook_url or os.environ.get('SLACK_WEBHOOK_URL')

    # Read digest content
    with open(digest_file_path, 'r') as f:
        digest_content = f.read()

    # Extract title
    title = digest_content.split('\n')[0].replace('# ', '')

    # Truncate if too long (Slack has 3000 char limit per block)
    preview = digest_content[:2000] + "\n\n..." if len(digest_content) > 2000 else digest_content

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"📰 {title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"```{preview}```"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"🤖 Generated with Claude Code"
                    }
                ]
            }
        ]
    }

    try:
        response = requests.post(webhook_url, json=message)
        response.raise_for_status()
        print(f"✓ Sent to Slack! Status: {response.status_code}")
        return True
    except Exception as e:
        print(f"⚠️  Error sending to Slack: {e}")
        return False


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python slack_sender.py <digest_file>")
        sys.exit(1)

    send_to_slack(sys.argv[1])
