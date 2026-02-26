# ElasticSeer - Autonomous Incident Response Agent

## Quick Start

### 1. Start Services
```bash
# Terminal 1: Backend
cd backend
uvicorn app.main:app --reload --port 8001

# Terminal 2: Frontend
cd frontend
npm run dev
```

### 2. Open Chat UI
Navigate to: http://localhost:5173

### 3. Test Autonomous Workflow

**The Perfect Demo Prompt:**
```
We have a critical authentication issue in production. Users can't log in. 
The auth-service is failing with JWT validation errors. Please investigate, 
create a fix, submit a PR, and alert the team immediately.
```

**Expected Result (30-60 seconds):**
```
✅ Complete Autonomous Workflow Executed!

1. ✅ Incident INC-XXXX registered
2. ✅ Found code file: src/auth/jwt_validator.py
3. ✅ GitHub PR #XX created: https://github.com/owner/repo/pull/XX
4. ✅ Slack alert sent to #general
5. ✅ Jira ticket created

All autonomous actions completed!
```

---

## Key Features

### 🤖 Autonomous Incident Response
- **One prompt → Complete workflow**
- Registers incidents automatically
- Searches codebase intelligently
- Creates GitHub PRs with AI-generated fixes
- Sends Slack notifications
- Creates Jira tickets for tracking

### 🧠 Adaptive Intelligence
- Uses discovered files, not hardcoded paths
- Makes intelligent decisions based on investigation
- Overrides bad incident data with real findings
- Natural language understanding

### 🔗 Complete Integration
- **Elasticsearch**: Data storage and querying
- **GitHub**: Automated PR creation
- **Slack**: Team notifications
- **Jira**: Incident tracking
- **Gemini AI**: Intelligent decision-making

---

## Agent Functions

The agent has 9 functions covering the complete incident lifecycle:

1. **query_recent_incidents** - Get recent incidents from Elasticsearch
2. **search_code_by_path** - Search code repository by pattern
3. **get_metrics_anomalies** - Detect performance issues
4. **get_incident_by_id** - Get specific incident details
5. **create_github_pr** - Create PR with AI-generated fix
6. **send_slack_alert** - Notify team on Slack
7. **create_jira_ticket** - Create tracking ticket
8. **register_incident** - Register new incident
9. **autonomous_incident_response** - Complete workflow in ONE call

---

## Usage Examples

### Complete Autonomous Workflow
```
User: "Critical auth issue. Users can't log in. JWT errors. Investigate, fix, PR, alert team."
Agent: [Executes complete workflow] "✅ All done! PR #22 created, team notified."
```

### Data Query
```
User: "Show me recent incidents in auth-service"
Agent: [Queries Elasticsearch] "Found 5 incidents in the last 24 hours..."
```

### Code Investigation
```
User: "Investigate incident INC-0635 and find the relevant code"
Agent: [Searches code] "Found src/auth/jwt_validator.py with hardcoded expiration..."
```

### Manual Fix
```
User: "Fix incident INC-0635 and create a PR"
Agent: [Creates PR] "PR #23 created: https://github.com/..."
```

---

## Configuration

### Backend (.env)
```bash
# Elasticsearch
ELASTICSEARCH_URL=https://your-cluster.elastic.cloud
ELASTICSEARCH_API_KEY=your-api-key

# Gemini AI
GEMINI_API_KEY=your-gemini-key
GEMINI_MODEL=gemini-2.0-flash-exp

# GitHub
GITHUB_TOKEN=your-github-token
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo

# Slack (optional)
SLACK_BOT_TOKEN=your-slack-token
SLACK_WAR_ROOM_CHANNEL=#general

# Jira (optional)
JIRA_URL=https://your-domain.atlassian.net
JIRA_PROJECT=INCIDENT
```

---

## Architecture

```
┌─────────────────┐
│   Chat UI       │  (React + TypeScript)
│  localhost:5173 │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  FastAPI        │  (Python)
│  Backend        │
│  localhost:8001 │
└────────┬────────┘
         │
         ├──────────────┐
         │              │
         ▼              ▼
┌─────────────┐  ┌──────────────┐
│  Gemini AI  │  │ Elasticsearch│
│  (Agent)    │  │  (Data)      │
└─────────────┘  └──────────────┘
         │
         ├──────────────┬──────────────┐
         ▼              ▼              ▼
    ┌────────┐    ┌────────┐    ┌────────┐
    │ GitHub │    │ Slack  │    │  Jira  │
    └────────┘    └────────┘    └────────┘
```

---

## Key Capabilities

### 1. Natural Language Understanding
- No commands or syntax required
- Understands context and urgency
- Extracts key information automatically

### 2. Autonomous Decision Making
- Registers incidents automatically
- Determines severity from context
- Chooses appropriate actions

### 3. Intelligent Investigation
- Searches code repository
- Identifies relevant files
- Analyzes code for issues

### 4. Adaptive Intelligence
- Uses discovered files (not hardcoded)
- Makes smart decisions based on findings
- Overrides bad data with real investigation

### 5. AI-Powered Remediation
- Generates actual code fixes
- Explains changes clearly
- Provides testing recommendations

### 6. Complete Integration
- GitHub: Creates real PRs
- Slack: Sends actual messages
- Jira: Creates tracking tickets
- Elasticsearch: Stores incident data

### 7. End-to-End Automation
- One prompt → Complete workflow
- No manual intervention needed
- Saves hours of work

---

## Troubleshooting

### Backend won't start
```bash
cd backend
pip install -r requirements.txt
```

### Frontend won't start
```bash
cd frontend
npm install
```

### Agent doesn't find files
Make sure Elasticsearch is running and code repository is indexed:
```bash
cd backend
python ingest_github_code.py
```

### PR creation fails
- Check GitHub token in backend/.env
- Verify repository access
- Agent will create FIXES.md if file doesn't exist

### Slack messages not sending
- Check Slack token in backend/.env
- Messages will log to console as fallback

---

## Demo Tips

1. **Start Simple**: "Show me recent incidents"
2. **Build Complexity**: Use the complete workflow prompt
3. **Show Real Results**: Open GitHub PRs and Slack messages
4. **Highlight Intelligence**: Point out adaptive file selection
5. **Emphasize Speed**: "Hours → Seconds"

---

## Success Metrics

- **Time Saved**: 90%+ (hours → seconds)
- **Automation**: 100% autonomous workflow
- **Accuracy**: AI-powered root cause analysis
- **Integration**: GitHub, Slack, Jira, Elasticsearch
- **Intelligence**: Adaptive file selection

---

## Support

For issues or questions:
1. Check backend logs: `tail -f backend/logs/app.log`
2. Check frontend console: Browser DevTools
3. Verify services are running: `curl http://localhost:8001/health`

---

**ElasticSeer - From problem to fix in 30 seconds. Completely autonomous.** 🚀
