# Digest Delivery Options

Your newsletter-bot generates digests weekly via GitHub Actions. Here's how to get them delivered to you automatically:

---

## 🎯 Quick Comparison

| Method | Setup Time | Cost | Best For |
|--------|------------|------|----------|
| **GitHub Watch** | 1 min | Free | Simplest option |
| **SendGrid Email** | 10 min | Free | Professional emails |
| **Slack Webhook** | 5 min | Free | Team sharing |
| **Gmail SMTP** | 10 min | Free | Personal email |

---

## Option 1: GitHub Watch (Easiest!) ⭐

**Time:** 1 minute
**Effort:** Click a button

### Steps:
1. Go to https://github.com/pjtat/newsletter-bot
2. Click the **"Watch"** button (top right)
3. Select **"Custom"**
4. Check **"Commits"** or **"Pushes"**
5. You'll get email notifications when digests are committed

**Pros:** Zero setup, free, works immediately
**Cons:** Basic GitHub email format, includes commit info

---

## Option 2: SendGrid Email (Best for Clean Emails) 🌟

**Time:** 10 minutes
**Cost:** Free (100 emails/day)

### Steps:

#### 1. Get SendGrid API Key
- Sign up at https://sendgrid.com/
- Create API key: Settings → API Keys → Create API Key
- Copy the key (you'll only see it once!)

#### 2. Add SendGrid to requirements.txt
```bash
echo "sendgrid==6.10.0" >> requirements.txt
git add requirements.txt
git commit -m "Add SendGrid for email delivery"
git push
```

#### 3. Add GitHub Secret
- Go to your repo: Settings → Secrets and variables → Actions
- Click "New repository secret"
- Name: `SENDGRID_API_KEY`
- Value: Paste your API key
- Click "Add secret"

#### 4. Update GitHub Actions workflow

Replace `.github/workflows/digest.yml` with the content from `.github/workflows/digest-with-email.yml.example` and update `your-email@example.com` to your email.

**Pros:** Clean professional emails, reliable, free
**Cons:** Requires setup, sender email verification

---

## Option 3: Slack Webhook (Great for Teams)

**Time:** 5 minutes
**Cost:** Free

### Steps:

#### 1. Create Slack Webhook
- Go to https://api.slack.com/apps
- Click "Create New App" → "From scratch"
- Name it "Newsletter Bot", select your workspace
- In "Incoming Webhooks", toggle "Activate Incoming Webhooks" to On
- Click "Add New Webhook to Workspace"
- Select the channel where you want digests
- Copy the webhook URL

#### 2. Add to GitHub Secrets
- Repo Settings → Secrets → Actions
- Add secret: `SLACK_WEBHOOK_URL` with your webhook URL

#### 3. Update workflow

Add this step to `.github/workflows/digest.yml` after "Generate digest":

```yaml
- name: Send to Slack
  env:
    SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
  run: |
    for digest in digests/*-$(date +%Y-%m-%d)-*.md; do
      if [ -f "$digest" ]; then
        python src/slack_sender.py "$digest"
      fi
    done
```

**Pros:** Great for teams, real-time, searchable
**Cons:** Need Slack workspace, 3000 char limit per message

---

## Option 4: Gmail SMTP (Personal Email)

**Time:** 10 minutes
**Cost:** Free

### For Gmail:

#### 1. Enable App Password
- Go to Google Account → Security
- Enable 2-Step Verification (if not already)
- Search for "App Passwords"
- Generate password for "Mail" on "Other"
- Copy the 16-character password

#### 2. Add secrets to GitHub
- `GMAIL_USERNAME`: your.email@gmail.com
- `GMAIL_APP_PASSWORD`: the 16-char password

#### 3. Use this Python script (src/gmail_sender.py):

```python
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_via_gmail(digest_file, to_email):
    with open(digest_file, 'r') as f:
        content = f.read()

    title = content.split('\n')[0].replace('# ', '')

    msg = MIMEMultipart()
    msg['From'] = os.environ['GMAIL_USERNAME']
    msg['To'] = to_email
    msg['Subject'] = f'📰 {title}'

    html = f'<pre style="font-family: monospace; white-space: pre-wrap;">{content}</pre>'
    msg.attach(MIMEText(html, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(os.environ['GMAIL_USERNAME'], os.environ['GMAIL_APP_PASSWORD'])
    server.send_message(msg)
    server.quit()
```

---

## Recommended Setup

**For solo use:** GitHub Watch (simplest) or SendGrid (cleanest emails)
**For teams:** Slack Webhook
**For existing Gmail users:** Gmail SMTP

---

## Testing Your Setup

### Test locally:
```bash
# For email (SendGrid)
python src/email_sender.py digests/latest-digest.md your-email@example.com

# For Slack
python src/slack_sender.py digests/latest-digest.md
```

### Test via GitHub Actions:
1. Go to Actions tab in your repo
2. Click "Generate News Digest" workflow
3. Click "Run workflow" → "Run workflow"
4. Wait ~2 minutes and check your email/Slack

---

## Need Help?

- SendGrid docs: https://docs.sendgrid.com/
- Slack webhooks: https://api.slack.com/messaging/webhooks
- GitHub Actions logs: Check the Actions tab for error messages
