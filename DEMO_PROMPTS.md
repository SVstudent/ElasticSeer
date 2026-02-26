# ElasticSeer Demo Prompts - Showcase All Capabilities

## 🎯 The Ultimate Demo Sequence

This sequence showcases ElasticSeer's complete autonomous capabilities in a realistic production scenario.

---

## Prompt 1: Data Discovery & Analysis
**Goal**: Show data-driven insights and anomaly detection

```
Show me the recent incidents and any anomalies in the auth-service
```

**Expected Agent Actions:**
1. Queries recent incidents from Elasticsearch
2. Searches for auth-service anomalies
3. Analyzes patterns and correlations
4. Presents structured data with insights

**Showcases:**
- ✅ Elasticsearch integration
- ✅ Data querying capabilities
- ✅ Pattern recognition
- ✅ Intelligent analysis

---

## Prompt 2: Incident Investigation
**Goal**: Show deep investigation with code search

```
Investigate incident INC-0635 and find the relevant code files
```

**Expected Agent Actions:**
1. Fetches incident details (severity, service, diagnosis)
2. Searches code repository for auth-related files
3. Identifies relevant files (e.g., jwt_validator.py)
4. Analyzes code for potential issues
5. Explains findings with context

**Showcases:**
- ✅ Incident data retrieval
- ✅ Code repository search
- ✅ Intelligent file discovery
- ✅ Root cause analysis

---

## Prompt 3: Autonomous Fix & PR Creation
**Goal**: Show adaptive file selection and PR creation

```
Fix this incident and create a PR
```

**Expected Agent Actions:**
1. Uses discovered file (not incident data)
2. Generates AI-powered code fix
3. Creates GitHub PR with detailed description
4. Returns PR number and URL

**Showcases:**
- ✅ Adaptive intelligence (uses discovered file)
- ✅ AI-powered code generation
- ✅ GitHub integration
- ✅ Autonomous remediation

---

## Prompt 4: Team Notification
**Goal**: Show Slack integration

```
Notify the team about this fix on Slack
```

**Expected Agent Actions:**
1. Crafts appropriate Slack message
2. Includes incident details and PR link
3. Sends to configured channel
4. Confirms delivery

**Showcases:**
- ✅ Slack integration
- ✅ Team collaboration
- ✅ Automated notifications
- ✅ Communication workflow

---

## 🚀 The Complete Autonomous Workflow (Single Prompt)

**The Ultimate Demo Prompt:**

```
We're seeing authentication failures in production. Users can't log in and it's affecting the auth-service. I think it might be related to JWT token validation. Can you investigate, fix it, create a PR, and notify the team?
```

**Expected Complete Workflow:**

### Step 1: Incident Registration
```
Agent: "I'll register this as a new incident..."
→ register_incident(
    title="Authentication failures in production",
    service="auth-service",
    severity="Sev-2",
    description="Users unable to log in, suspected JWT validation issue"
  )
→ Result: INC-1005 created
```

### Step 2: Code Investigation
```
Agent: "Searching for JWT-related code..."
→ search_code_by_path(pattern="*jwt*")
→ Found: src/auth/jwt_validator.py
→ Analysis: "Found hardcoded expiration in jwt_validator.py"
```

### Step 3: Fix Generation & PR
```
Agent: "Generating fix and creating PR..."
→ create_github_pr(
    incident_id="INC-1005",
    file_path="src/auth/jwt_validator.py"  // Adaptive override!
  )
→ Result: PR #126 created
```

### Step 4: Team Notification
```
Agent: "Notifying team on Slack..."
→ send_slack_alert(
    severity="Sev-2",
    incident_id="INC-1005",
    title="Auth service fix deployed",
    message="PR #126 created for authentication failures"
  )
→ Result: Team notified
```

### Step 5: Tracking
```
Agent: "Creating Jira ticket for tracking..."
→ create_jira_ticket(
    summary="Authentication failures - JWT validation",
    description="...",
    priority="High",
    incident_id="INC-1005"
  )
→ Result: Ticket INC-20260226... created
```

**Final Response:**
```
✅ Complete autonomous response executed!

**Incident**: INC-1005 (Sev-2)
**Root Cause**: Hardcoded JWT expiration in jwt_validator.py
**Fix**: PR #126 - https://github.com/owner/repo/pull/126
**Team**: Notified on Slack (#general)
**Tracking**: Jira ticket INC-20260226...

The PR is ready for review. I've updated the JWT validation logic to use 
configurable expiration times instead of hardcoded values.

**Next Steps**:
1. Review PR #126
2. Run tests in staging
3. Deploy to production
4. Monitor auth-service metrics
```

**Showcases:**
- ✅ Complete autonomous workflow
- ✅ Natural language understanding
- ✅ Incident registration
- ✅ Code investigation
- ✅ Adaptive file selection
- ✅ AI-powered fixes
- ✅ GitHub PR creation
- ✅ Slack notifications
- ✅ Jira integration
- ✅ End-to-end automation

---

## 🎬 Alternative Demo Scenarios

### Scenario A: Metrics Analysis
```
Analyze metrics for the api-gateway and show me any performance issues
```

**Shows**: Metrics querying, anomaly detection, data visualization

### Scenario B: Code Search
```
Find all files related to caching in the repository
```

**Shows**: Code repository search, pattern matching, file discovery

### Scenario C: Incident Comparison
```
Show me recent incidents similar to INC-0635
```

**Shows**: Pattern recognition, incident correlation, historical analysis

### Scenario D: New Problem Report
```
The payment service is timing out in eu-west-1. It started 10 minutes ago and customers are complaining. This is critical!
```

**Shows**: 
- Severity detection (Sev-1 from "critical")
- Region extraction (eu-west-1)
- Service identification (payment)
- Immediate autonomous response

### Scenario E: Multi-Service Investigation
```
We're seeing high latency across api-gateway, auth-service, and database. What's the root cause?
```

**Shows**:
- Multi-service analysis
- Correlation detection
- Root cause diagnosis
- Comprehensive investigation

---

## 📊 Demo Flow Recommendations

### For Technical Audience (Developers/SREs)
1. Start with data query (show Elasticsearch integration)
2. Investigate specific incident (show code search)
3. Create PR with adaptive file selection (show intelligence)
4. Show the PR on GitHub (prove it works)

### For Business Audience (Managers/Executives)
1. Use the complete autonomous workflow prompt
2. Show how one message triggers entire response
3. Highlight time saved and automation
4. Emphasize team collaboration features

### For Live Demo
1. **Prompt 1**: "Show recent incidents" (quick, safe)
2. **Prompt 2**: "Investigate INC-0635" (shows intelligence)
3. **Prompt 3**: "Fix it and create a PR" (shows automation)
4. **Prompt 4**: "Notify the team" (shows integration)
5. **Show GitHub**: Open the actual PR that was created
6. **Show Slack**: Show the actual message sent

---

## 🎯 The "Wow Factor" Prompts

### Prompt A: Zero to Fix in One Message
```
The cache is returning stale data and it's breaking the user dashboard. Fix it now.
```

**Why it's impressive**: Single message → Incident registered → Code found → PR created → Team notified

### Prompt B: Intelligent Override
```
Incident INC-0635 says the issue is in src/user_service/service.py, but I think it's actually in the JWT validator. Can you check?
```

**Why it's impressive**: Shows agent can override bad data and make intelligent decisions

### Prompt C: Complex Analysis
```
Why are we seeing more Sev-2 incidents in auth-service this week compared to last week?
```

**Why it's impressive**: Shows data analysis, pattern recognition, and insights

---

## 💡 Pro Tips for Demo

1. **Start Simple**: Begin with data queries to warm up
2. **Build Complexity**: Progress to autonomous workflows
3. **Show Real Results**: Open GitHub PRs and Slack messages
4. **Highlight Intelligence**: Point out adaptive file selection
5. **Emphasize Speed**: "This would take hours manually, took 30 seconds"
6. **Show Reliability**: Demonstrate fallback responses work

---

## 🚨 Emergency Demo (If Something Breaks)

If the full workflow fails, use these safe prompts:

```
1. "Show me recent incidents" (always works - just queries data)
2. "Tell me about incident INC-0635" (shows data retrieval)
3. "Search for auth-related code files" (shows code search)
```

These are read-only operations that showcase capabilities without requiring external integrations.

---

## 📝 Demo Script Template

```
[Opening]
"Let me show you ElasticSeer, our autonomous incident response agent."

[Prompt 1 - Data]
"Show me recent incidents and anomalies in auth-service"
→ Wait for response
→ Point out: "Notice how it queries real Elasticsearch data"

[Prompt 2 - Investigation]
"Investigate incident INC-0635 and find the relevant code"
→ Wait for response
→ Point out: "It found jwt_validator.py through intelligent search"

[Prompt 3 - Autonomous Fix]
"Fix this incident and create a PR"
→ Wait for response
→ Point out: "It used the file IT found, not the incident data"
→ Open GitHub to show actual PR

[Prompt 4 - Notification]
"Notify the team on Slack"
→ Wait for response
→ Show Slack channel with message

[Closing]
"That's ElasticSeer - from problem to fix to notification, completely autonomous."
```

---

## 🎉 The Perfect Demo Prompt

If you only have time for ONE prompt, use this:

```
We have a critical authentication issue in production. Users can't log in. The auth-service is failing with JWT validation errors. Please investigate, create a fix, submit a PR, and alert the team immediately.
```

**Why it's perfect:**
- ✅ Shows urgency handling (critical)
- ✅ Demonstrates investigation
- ✅ Proves autonomous fixing
- ✅ Shows GitHub integration
- ✅ Demonstrates team collaboration
- ✅ All in ONE prompt
- ✅ Realistic production scenario
- ✅ Complete end-to-end workflow

**Expected time**: 30-60 seconds for complete autonomous response

**Expected result**: Incident registered → Code found → PR created → Team notified → Jira ticket created

This is ElasticSeer at its best! 🚀
