# SendGrid Setup Guide

Follow these steps to complete the SendGrid email delivery setup:

---

## Step 1: Get SendGrid API Key (5 minutes)

### 1.1 Sign up for SendGrid
1. Go to https://sendgrid.com/
2. Click "Start for Free"
3. Fill out the signup form (choose "Free" plan - 100 emails/day)
4. Verify your email address

### 1.2 Create API Key
1. Log into SendGrid dashboard
2. Go to **Settings** → **API Keys** (left sidebar)
3. Click **"Create API Key"** (blue button, top right)
4. Name it: `newsletter-bot`
5. Select **"Full Access"** (or at minimum: "Mail Send" access)
6. Click **"Create & View"**
7. **⚠️ COPY THE API KEY NOW** - you'll only see it once!
   - It looks like: `SG.xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### 1.3 Verify Sender Email (Required by SendGrid)
1. Go to **Settings** → **Sender Authentication**
2. Click **"Verify a Single Sender"**
3. Fill out the form with your email (e.g., your-email@gmail.com)
4. Check your inbox and click the verification link
5. Once verified, you can use this email as the "from" address

---

## Step 2: Add GitHub Secrets (2 minutes)

1. Go to your GitHub repository: https://github.com/pjtat/newsletter-bot
2. Click **Settings** (top menu)
3. In the left sidebar, click **Secrets and variables** → **Actions**
4. Click **"New repository secret"** for each:

### Secret 1: SENDGRID_API_KEY
- Name: `SENDGRID_API_KEY`
- Value: Paste the API key from Step 1.2 (starts with `SG.`)
- Click **"Add secret"**

### Secret 2: RECIPIENT_EMAIL
- Name: `RECIPIENT_EMAIL`
- Value: Your email address (where you want to receive digests)
- Click **"Add secret"**

### Secret 3: SENDGRID_FROM_EMAIL (Optional)
- Name: `SENDGRID_FROM_EMAIL`
- Value: The email you verified in Step 1.3
- Click **"Add secret"**
- If you skip this, it will default to `noreply@newsletterbot.com` (may go to spam)

---

## Step 3: Test Locally (Optional but Recommended)

### 3.1 Install SendGrid locally
```bash
cd /Users/ptatano/Documents/Side\ Projects/newsletter-bot
pip3 install sendgrid==6.11.0
```

### 3.2 Set environment variables
```bash
export SENDGRID_API_KEY="SG.your_actual_key_here"
export RECIPIENT_EMAIL="your-email@example.com"
```

### 3.3 Test with an existing digest
```bash
# Find a recent digest
ls -lt digests/*.md | head -1

# Send it as a test email
python3 src/email_sender.py digests/2025-12-27-world-news-digest.md your-email@example.com
```

### Expected output:
```
✓ Email sent to your-email@example.com! Status: 202
  Subject: 📰 World News Digest
```

### Check your inbox!
- Look for an email with subject "📰 World News Digest"
- Check spam folder if you don't see it
- The email should have nice formatting with your digest content

---

## Step 4: Test via GitHub Actions

Once GitHub secrets are set up:

1. Go to your repo's **Actions** tab
2. Click **"Generate News Digest"** workflow (left sidebar)
3. Click **"Run workflow"** dropdown (right side)
4. Click **"Run workflow"** button
5. Wait 2-3 minutes for it to complete
6. Check your email inbox for 2 digest emails:
   - 📰 Media & Entertainment Industry News
   - 📰 World News Digest

---

## Troubleshooting

### "Authentication failed" or 403 error
- Double-check your `SENDGRID_API_KEY` in GitHub secrets
- Make sure it starts with `SG.`
- Try creating a new API key with "Full Access"

### Emails going to spam
- Add `SENDGRID_FROM_EMAIL` secret with your verified sender email
- Ask SendGrid to verify your domain (Settings → Sender Authentication → Domain Authentication)

### "Sender email must be verified"
- Complete Step 1.3 above
- Use the exact email address you verified

### No email received
- Check spam folder
- Check GitHub Actions logs for errors
- Verify `RECIPIENT_EMAIL` secret is correct
- Try the local test (Step 3) first

---

## Next Steps

Once testing is complete:
1. Commit and push the changes
2. Digests will automatically email you every Sunday at 6 PM UTC
3. You can manually trigger anytime from GitHub Actions tab

---

## Current Setup Status

✅ SendGrid dependency added to requirements.txt
✅ Email sender script created (src/email_sender.py)
✅ GitHub Actions workflow updated
⏳ Need to: Get SendGrid API key
⏳ Need to: Add GitHub secrets
⏳ Need to: Test email delivery
⏳ Need to: Commit and push
