# ElasticSeer — Autonomous Incident Response Platform

**From detection to fix in 30 seconds. Completely autonomous.**

ElasticSeer is a multi-agent AI platform that handles **complete incident response workflows** — from anomaly detection to code fix to team notification — all through natural language chat. Built with **Elastic Agent Builder**, **Elasticsearch**, **ES|QL**, and **Elastic Workflows**.

---

## 🏗️ Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                    ElasticSeer Multi-Agent System               │
├────────────┬────────────────────────────┬──────────────────────┤
│  Observer  │     Reasoning Agent        │   Action Agents      │
│  Engine    │     (Gemini 2.0 Flash)     │                      │
│            │                            │  ┌─────────────────┐ │
│  Anomaly   │  ┌──────────────────────┐  │  │ GitHub PR Agent │ │
│  Detection │  │ Agent Builder + MCP  │  │  │ Slack Agent     │ │
│  (3σ)      │──│ ES|QL Queries        │──│  │ Jira Agent      │ │
│            │  │ Elastic Workflows    │  │  │ Postmortem Gen  │ │
│  Elastic   │  └──────────────────────┘  │  └─────────────────┘ │
│  Workflow  │                            │                      │
└────────────┴────────────────────────────┴──────────────────────┘
                          │
              ┌───────────┼───────────┐
              ▼           ▼           ▼
        Elasticsearch   GitHub    Slack / Jira
        (Incidents,     (PRs,     (Alerts,
         Metrics,       Code)     Tickets)
         Code, Logs)
```

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

---

## ✨ Key Features

### 🤖 Autonomous Incident Response Workflow
One natural language prompt triggers a **complete Elastic Workflow**:
1. ✅ **Detect** — Observer Engine monitors metrics via Elasticsearch, flags anomalies using 3σ statistical analysis
2. ✅ **Investigate** — Agent queries incidents and code via **Agent Builder MCP** + **ES|QL**
3. ✅ **Fix** — Generates AI-powered code fix with Gemini, creates **GitHub PR**
4. ✅ **Notify** — Sends **Slack** alert to war room channel
5. ✅ **Track** — Creates **Jira** ticket for incident tracking
6. ✅ **Report** — Auto-generates **Postmortem Report** with timeline, root cause & recommendations

### 🧠 Elastic Agent Builder Integration
- **4 MCP Tools** via Kibana Agent Builder server:
  - `elasticseer_get_recent_incidents` — ES|QL query for incident data
  - `elasticseer_search_code_by_path` — ES|QL query for code repository
  - `elasticseer_get_metrics_anomalies` — ES|QL query for metric anomalies
  - `elasticseer_get_incident_by_id` — ES|QL query for specific incidents
- **ES|QL** powers all data retrieval through the MCP server
- **Elastic Workflows** implemented as the Observer Engine's autonomous detection → response pipeline

### 🔭 Observer Engine (Continuous Monitoring)
- Autonomous background agent that continuously monitors Elasticsearch metrics
- **Statistical anomaly detection** using 3σ deviation analysis
- Auto-correlates anomalies with recent GitHub commits to identify suspect changes
- Triggers autonomous remediation workflows when critical anomalies are detected

### 📋 Postmortem Report Generator
- Ask the agent: *"Generate a postmortem for INC-1010"*
- Aggregates: incident data, full action timeline, anomaly context
- Generates structured report with root cause, impact, recommendations
- Every SRE team's dream — postmortems written automatically

### 🔗 Complete Integration Suite
| Integration | What It Does |
|---|---|
| **Elasticsearch** | Data store for incidents, metrics, code, activity logs |
| **Agent Builder + MCP** | Tool orchestration for ES|QL queries |
| **GitHub** | Automated PR creation with AI-generated code fixes |
| **Slack** | Real-time team notifications and war room alerts |
| **Jira** | Incident tracking, ticket creation, escalation |
| **Gemini 2.0 Flash** | Reasoning, code generation, postmortem writing |

---

## 🎯 Agent Functions (11 Tools)

| Function | Type | Description |
|---|---|---|
| `query_recent_incidents` | MCP/ES\|QL | Get recent incidents from Elasticsearch |
| `search_code_by_path` | MCP/ES\|QL | Search code repository by pattern |
| `get_metrics_anomalies` | MCP/ES\|QL | Detect performance anomalies per service |
| `analyze_service_metrics` | Analysis | Comprehensive metrics with trends & baselines |
| `get_incident_by_id` | MCP/ES\|QL | Get specific incident details |
| `register_incident` | Elasticsearch | Register new incident from user report |
| `create_github_pr` | GitHub API | Create PR with AI-generated code fix |
| `send_slack_alert` | Slack API | Alert the team on Slack |
| `create_jira_ticket` | Jira API | Create tracking ticket |
| `autonomous_incident_response` | Workflow | Complete end-to-end workflow in ONE call |
| `generate_postmortem` | Gemini AI | Auto-generate incident postmortem report |

---

## 🛠️ Tech Stack

- **Frontend**: React + TypeScript + Vite + TailwindCSS
- **Backend**: FastAPI + Python
- **AI**: Google Gemini 2.0 Flash (reasoning + code generation + postmortems)
- **Data**: Elasticsearch (incidents, metrics, code repository, activity logs)
- **Agent Framework**: Elastic Agent Builder + MCP Server
- **Query Language**: ES|QL (via Agent Builder MCP tools)
- **Integrations**: GitHub API, Slack API, Jira API

---

## ⚙️ Configuration

Create `backend/.env`:
```bash
# Elasticsearch
ELASTICSEARCH_URL=https://your-cluster.elastic.cloud
ELASTICSEARCH_API_KEY=your-api-key

# Kibana (for Agent Builder MCP)
KIBANA_URL=https://your-kibana.elastic.cloud

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

## 🎬 Demo Prompts

**Full Autonomous Workflow:**
```
We have a critical authentication issue in production. Users can't log in. 
The auth-service is failing with JWT validation errors. Please investigate, 
create a fix, submit a PR, and alert the team immediately.
```

**Postmortem Report:**
```
Generate a postmortem report for INC-1010
```

**Deep Metrics Analysis:**
```
Analyze the api-gateway service metrics for the last 24 hours
```

---

## 📊 Impact Metrics

| Metric | Before ElasticSeer | After ElasticSeer |
|---|---|---|
| **Time to Detection** | Minutes to hours | < 30 seconds |
| **Time to Remediation** | Hours to days | < 60 seconds |
| **Manual Steps** | 6+ (detect, investigate, fix, PR, alert, ticket) | 0 (fully autonomous) |
| **Postmortem Writing** | 2-4 hours manual | Instant (auto-generated) |
| **Human Intervention** | Required at every step | Only for approval |

---

## 📝 License

MIT License

---

**Built for the Elasticsearch Agent Builder Hackathon 🏆**

*ElasticSeer — From problem to fix in 30 seconds. Completely autonomous.*
