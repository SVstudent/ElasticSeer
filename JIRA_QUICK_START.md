# 🎫 Jira Integration - Quick Start

## What You Need (3 Things)

1. **JIRA_URL** - Your Jira instance URL
2. **JIRA_TOKEN** - API token for authentication  
3. **JIRA_PROJECT** - Project key where tickets will be created

---

## 5-Minute Setup

### Step 1: Get Your Jira URL (30 seconds)

Look at your browser when logged into Jira:

- **Jira Cloud**: `https://yourcompany.atlassian.net`
- **Jira Server**: `https://jira.yourcompany.com`

Copy the full URL including `https://`

---

### Step 2: Create API Token (2 minutes)

#### For Jira Cloud:

1. Go to: https://id.atlassian.com/manage-profile/security/api-tokens
2. Click "Create API token"
3. Name it: `ElasticSeer`
4. Click "Create"
5. **Copy the token immediately** (you won't see it again!)

Token looks like: `ATATT3xFfGF0...` (long string starting with ATATT)

#### For Jira Server:

1. Go to: `https://YOUR-JIRA-URL/secure/ViewProfile.jspa`
2. Click "Personal Access Tokens"
3. Create token named `ElasticSeer`
4. Copy the token

---

### Step 3: Get Project Key (30 seconds)

1. Go to your Jira project
2. Look at any ticket ID: `INC-123`
3. The project key is the part before the dash: `INC`

Common keys: `INC`, `OPS`, `SUP`, `PROD`

---

### Step 4: Add to .env (1 minute)

Open `backend/.env` and add:

```bash
# Jira Configuration
JIRA_URL=https://yourcompany.atlassian.net
JIRA_TOKEN=ATATT3xFfGF0abcdefghijklmnopqrstuvwxyz1234567890
JIRA_PROJECT=INC
```

Replace with YOUR values!

---

### Step 5: Restart Backend (30 seconds)

```bash
# Stop backend (Ctrl+C if running)
# Then restart:
cd backend
uvicorn app.main:app --reload --port 8001
```

---

## Test It!

1. Open chat: http://localhost:5173

2. Send this message:
   ```
   Critical database issue. Connection pool exhausted. 
   Investigate, fix, create PR, alert team, and create Jira ticket.
   ```

3. Check your Jira project for the new ticket!

---

## Example Configuration

```bash
# Real example for Jira Cloud
JIRA_URL=https://acmecorp.atlassian.net
JIRA_TOKEN=ATATT3xFfGF0T8vK9mNpQrStUvWxYz1234567890AbCdEfGhIjKlMnOpQrStUvWxYz
JIRA_PROJECT=INC
```

---

## Troubleshooting

### "401 Unauthorized"
→ Token is wrong or expired. Generate a new one.

### "404 Not Found"  
→ Check your JIRA_URL and JIRA_PROJECT are correct.

### "403 Forbidden"
→ Your account doesn't have permission to create issues in that project.

### Tickets not appearing
→ Make sure you're looking at the right project (check JIRA_PROJECT key).

---

## What Happens When Configured

When you run the autonomous workflow, ElasticSeer will:

1. ✅ Register incident
2. ✅ Search code
3. ✅ Create GitHub PR
4. ✅ Send Slack alert
5. ✅ **Create Jira ticket** ← NEW!

The Jira ticket includes:
- Incident summary
- Full description
- Priority (Critical/High/Medium/Low)
- Labels: `elasticseer`, `automated`, `incident-{ID}`
- Link to GitHub PR (if created)

---

## Security Notes

- ⚠️ Never commit your token to Git
- ⚠️ `.env` is already in `.gitignore` - keep it that way
- ⚠️ Rotate tokens every 90 days
- ⚠️ Use a service account for production

---

## Need More Details?

See the full guide: `JIRA_SETUP_GUIDE.md`

---

**That's it!** You're ready to automatically create Jira tickets for every incident. 🎫
