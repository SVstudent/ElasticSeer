# 🎫 Jira Integration Setup Guide

This guide walks you through setting up Jira integration for ElasticSeer to automatically create incident tickets.

---

## Prerequisites

- A Jira account (Cloud or Server/Data Center)
- Admin or project admin permissions to create API tokens
- A Jira project where incidents will be tracked

---

## Step 1: Get Your Jira URL

Your Jira URL depends on your Jira type:

### Jira Cloud
Format: `https://YOUR-DOMAIN.atlassian.net`

Example: `https://mycompany.atlassian.net`

To find it:
1. Log into Jira
2. Look at your browser's address bar
3. Copy everything up to `.atlassian.net` (including the https://)

### Jira Server/Data Center
Format: `https://jira.yourcompany.com`

Example: `https://jira.acme.com`

---

## Step 2: Create a Jira API Token

### For Jira Cloud:

1. **Go to Atlassian Account Settings**
   - Visit: https://id.atlassian.com/manage-profile/security/api-tokens
   - Or: Click your profile picture → Account Settings → Security → API tokens

2. **Create API Token**
   - Click "Create API token"
   - Label: `ElasticSeer Integration` (or any name you prefer)
   - Click "Create"

3. **Copy the Token**
   - ⚠️ **IMPORTANT**: Copy the token immediately - you won't see it again!
   - It looks like: `ATATT3xFfGF0abcdefghijklmnopqrstuvwxyz1234567890`

### For Jira Server/Data Center:

1. **Go to Personal Access Tokens**
   - Visit: `https://YOUR-JIRA-URL/secure/ViewProfile.jspa`
   - Click "Personal Access Tokens" in the left sidebar

2. **Create Token**
   - Click "Create token"
   - Name: `ElasticSeer`
   - Expiry: Choose appropriate duration (or "Never" for testing)
   - Click "Create"

3. **Copy the Token**
   - Copy the generated token immediately

---

## Step 3: Find Your Jira Project Key

The project key is the short code used in ticket IDs (e.g., `INC` in `INC-123`).

1. **Go to Your Jira Project**
   - Navigate to the project where you want incidents tracked

2. **Find the Project Key**
   - Look at the URL: `https://yourcompany.atlassian.net/browse/INC`
   - The project key is the last part: `INC`
   - Or look at any ticket ID in the project: `INC-123` → key is `INC`

Common project keys:
- `INC` - Incidents
- `OPS` - Operations
- `SUP` - Support
- `PROD` - Production Issues

---

## Step 4: Configure ElasticSeer

### Option A: Using .env File (Recommended)

1. **Open `backend/.env`**

2. **Add Your Jira Credentials**:
   ```bash
   # Jira Configuration
   JIRA_URL=https://yourcompany.atlassian.net
   JIRA_TOKEN=ATATT3xFfGF0abcdefghijklmnopqrstuvwxyz1234567890
   JIRA_PROJECT=INC
   ```

3. **Replace with Your Values**:
   - `JIRA_URL`: Your Jira instance URL (from Step 1)
   - `JIRA_TOKEN`: Your API token (from Step 2)
   - `JIRA_PROJECT`: Your project key (from Step 3)

### Option B: Using Environment Variables

Export the variables in your terminal:

```bash
export JIRA_URL="https://yourcompany.atlassian.net"
export JIRA_TOKEN="ATATT3xFfGF0abcdefghijklmnopqrstuvwxyz1234567890"
export JIRA_PROJECT="INC"
```

---

## Step 5: Verify Configuration

### Test the Integration

1. **Restart the Backend** (if running):
   ```bash
   # Stop the backend (Ctrl+C)
   # Then restart:
   cd backend
   uvicorn app.main:app --reload --port 8001
   ```

2. **Check Health Endpoint**:
   ```bash
   curl http://localhost:8001/api/elasticseer/health
   ```

   You should see:
   ```json
   {
     "status": "healthy",
     "services": {
       "gemini": true,
       "github": true,
       "slack": true,
       "elasticsearch": true
     }
   }
   ```

3. **Test Ticket Creation** (via chat):
   - Open chat UI: http://localhost:5173
   - Send: "Create a test Jira ticket for a database connection issue"
   - The agent should create a ticket and return the ticket ID

---

## Step 6: Verify in Jira

1. **Go to Your Jira Project**
   - Visit: `https://yourcompany.atlassian.net/browse/INC`

2. **Check for New Tickets**
   - Look for tickets created by ElasticSeer
   - They should have:
     - Summary from the incident
     - Description with full details
     - Priority set (Critical/High/Medium/Low)
     - Labels: `elasticseer`, `automated`

---

## Authentication Methods

ElasticSeer supports two authentication methods:

### 1. API Token (Recommended for Jira Cloud)
- Uses: `JIRA_TOKEN` environment variable
- Format: `ATATT3xFfGF0...` (starts with ATATT)
- Best for: Jira Cloud instances

### 2. Personal Access Token (For Jira Server/Data Center)
- Uses: `JIRA_TOKEN` environment variable
- Format: Varies by Jira version
- Best for: Self-hosted Jira instances

---

## Troubleshooting

### Issue: "401 Unauthorized"

**Cause**: Invalid or expired token

**Solution**:
1. Verify your token is correct in `.env`
2. Check token hasn't expired (for PATs)
3. Regenerate a new token if needed

### Issue: "404 Not Found"

**Cause**: Invalid Jira URL or project key

**Solution**:
1. Verify `JIRA_URL` is correct (include `https://`)
2. Check `JIRA_PROJECT` matches your project key exactly
3. Ensure you have access to the project

### Issue: "403 Forbidden"

**Cause**: Insufficient permissions

**Solution**:
1. Verify your Jira account has permission to create issues
2. Check the project allows issue creation
3. Ensure the token has the right scopes

### Issue: Tickets Not Appearing

**Cause**: Wrong project or permissions

**Solution**:
1. Check you're looking at the correct project
2. Verify the project key in `.env` matches
3. Check Jira filters aren't hiding the tickets

---

## Example Configuration

Here's a complete example for Jira Cloud:

```bash
# Jira Configuration
JIRA_URL=https://acmecorp.atlassian.net
JIRA_TOKEN=ATATT3xFfGF0T8vK9mNpQrStUvWxYz1234567890AbCdEfGhIjKlMnOpQrStUvWxYz
JIRA_PROJECT=INC
```

---

## Security Best Practices

1. **Never commit tokens to Git**
   - `.env` is in `.gitignore` - keep it that way
   - Use environment variables in production

2. **Rotate tokens regularly**
   - Set expiration dates on tokens
   - Regenerate every 90 days

3. **Use service accounts**
   - Create a dedicated "ElasticSeer Bot" Jira user
   - Generate tokens from that account
   - Easier to track and revoke

4. **Limit permissions**
   - Only grant "Create Issues" permission
   - Don't use admin tokens

---

## What Gets Created in Jira

When ElasticSeer creates a ticket, it includes:

- **Summary**: Brief incident title
- **Description**: Full incident details including:
  - Incident ID
  - Service affected
  - Severity level
  - Root cause (if diagnosed)
  - Related PR (if created)
- **Priority**: Mapped from severity:
  - Sev-1 → Critical
  - Sev-2 → High
  - Sev-3 → Medium
- **Labels**: `elasticseer`, `automated`, `incident-{ID}`
- **Issue Type**: Usually "Bug" or "Incident" (configurable)

---

## Next Steps

Once Jira is configured:

1. ✅ Test the autonomous workflow:
   ```
   "Critical database issue. Connection pool exhausted. 
   Investigate, fix, create PR, alert team, and create Jira ticket."
   ```

2. ✅ The agent will automatically:
   - Register the incident
   - Search for relevant code
   - Create a GitHub PR with fix
   - Send Slack alert
   - **Create Jira ticket** ← NEW!

3. ✅ Check Jira for the new ticket with all details

---

## Need Help?

- **Jira Cloud API Docs**: https://developer.atlassian.com/cloud/jira/platform/rest/v3/
- **API Token Management**: https://id.atlassian.com/manage-profile/security/api-tokens
- **Jira Server API**: https://docs.atlassian.com/software/jira/docs/api/REST/latest/

---

**Ready to integrate?** Follow the steps above and you'll have Jira tickets automatically created for every incident! 🎫
