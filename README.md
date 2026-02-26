# ElasticSeer - Autonomous Incident Response Agent

**From problem to fix in 30 seconds. Completely autonomous.**

ElasticSeer is an AI-powered autonomous agent that handles complete incident response workflows - from detection to fix to notification - all through natural language chat.

---

## 🚀 Quick Start

```bash
# 1. Start Backend
cd backend
uvicorn app.main:app --reload --port 8001

# 2. Start Frontend (new terminal)
cd frontend
npm run dev

# 3. Open http://localhost:5173
```

**Try this prompt:**
```
We have a critical authentication issue in production. Users can't log in. 
The auth-service is failing with JWT validation errors. Please investigate, 
create a fix, submit a PR, and alert the team immediately.
```

**Result:** Complete autonomous workflow in 30-60 seconds!

---

## ✨ Key Features

- 🤖 **Autonomous Workflows** - One prompt triggers complete incident response
- 🧠 **Adaptive Intelligence** - Uses discovered files, not hardcoded paths
- 🔗 **Full Integration** - GitHub PRs, Slack alerts, Jira tickets, Elasticsearch
- 💬 **Natural Language** - No commands, just describe the problem
- ⚡ **Lightning Fast** - Hours of work done in seconds

---

## 📚 Documentation

- **[ELASTICSEER_GUIDE.md](ELASTICSEER_GUIDE.md)** - Complete setup and usage guide
- **[DEMO_PROMPTS.md](DEMO_PROMPTS.md)** - Demo scenarios and example prompts
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing and validation
- **[ORCHESTRATOR_FUNCTION_FIX.md](ORCHESTRATOR_FUNCTION_FIX.md)** - Technical architecture

---

## 🎯 What It Does

### Complete Autonomous Workflow
1. ✅ Registers incident in Elasticsearch
2. ✅ Searches codebase for relevant files
3. ✅ Generates AI-powered code fix
4. ✅ Creates GitHub PR with fix
5. ✅ Sends Slack alert to team
6. ✅ Creates Jira ticket for tracking

**All from ONE natural language prompt!**

---

## 🛠️ Tech Stack

- **Frontend**: React + TypeScript + Vite
- **Backend**: FastAPI + Python
- **AI**: Google Gemini 2.0 Flash
- **Data**: Elasticsearch
- **Integration**: GitHub API, Slack API, Jira API

---

## ⚙️ Configuration

Create `backend/.env`:
```bash
# Elasticsearch
ELASTICSEARCH_URL=https://your-cluster.elastic.cloud
ELASTICSEARCH_API_KEY=your-api-key

# Gemini AI
GEMINI_API_KEY=your-gemini-key

# GitHub
GITHUB_TOKEN=your-github-token
GITHUB_OWNER=your-username
GITHUB_REPO=your-repo

# Slack (optional)
SLACK_BOT_TOKEN=your-slack-token

# Jira (optional)
JIRA_URL=https://your-domain.atlassian.net
```

---

## 📊 Architecture

```
Chat UI (React) → FastAPI Backend → Gemini AI Agent
                                   ↓
                    ┌──────────────┼──────────────┐
                    ↓              ↓              ↓
              Elasticsearch    GitHub API    Slack API
```

---

## 🎬 Demo

**Input:**
```
Critical auth issue. Users can't log in. JWT errors. Fix it now.
```

**Output:**
```
✅ Complete Autonomous Workflow Executed!

1. ✅ Incident INC-1003 registered
2. ✅ Found code file: src/auth/jwt_validator.py
3. ✅ GitHub PR #22 created: https://github.com/...
4. ✅ Slack alert sent to #general
5. ✅ Jira ticket created

All autonomous actions completed!
```

---

## 🤝 Contributing

This is a hackathon project demonstrating autonomous AI agents for incident response.

---

## 📝 License

MIT License - See LICENSE file for details

---

**Built with ❤️ for autonomous incident response**
