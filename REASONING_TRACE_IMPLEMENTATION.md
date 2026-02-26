# 🧠 Reasoning Trace Implementation Guide

## Overview

This feature adds **real-time reasoning traces** that show the agent's actual thought process as it executes tasks. Users can see exactly what the agent is thinking and doing at each step.

---

## What Was Implemented

### 1. Backend: New Reasoning Trace API

**File**: `backend/app/api/agent_chat_with_reasoning.py`

**Endpoint**: `POST /api/agent/chat_with_reasoning`

**Features**:
- ✅ Tracks every step of agent execution
- ✅ Shows which tools are being called and why
- ✅ Provides real-time progress updates
- ✅ Includes timestamps for each thought
- ✅ Returns reasoning trace alongside response

**Example Reasoning Trace**:
```json
{
  "response": "✅ Complete workflow executed!",
  "reasoning_trace": [
    {
      "step": "initialization",
      "thought": "🤖 ElasticSeer agent initialized, analyzing your request...",
      "timestamp": "2024-02-26T10:00:00Z"
    },
    {
      "step": "analyzing_request",
      "thought": "🔍 Analyzing: 'Critical database issue. Connection pool exhausted...'",
      "timestamp": "2024-02-26T10:00:01Z"
    },
    {
      "step": "workflow_execution",
      "thought": "🚀 Executing COMPLETE autonomous workflow for: Critical database issue",
      "timestamp": "2024-02-26T10:00:02Z",
      "details": {"severity": "Sev-1", "service": "database"}
    },
    {
      "step": "workflow_step_1",
      "thought": "📝 Step 1/5: Registering incident in system...",
      "timestamp": "2024-02-26T10:00:03Z"
    },
    {
      "step": "workflow_complete_1",
      "thought": "✅ Incident INC-1005 registered successfully",
      "timestamp": "2024-02-26T10:00:05Z"
    },
    {
      "step": "workflow_step_2",
      "thought": "🔍 Step 2/5: Searching codebase for relevant files...",
      "timestamp": "2024-02-26T10:00:06Z"
    },
    {
      "step": "workflow_complete_2",
      "thought": "✅ Found relevant code file: src/database/connection_pool.py",
      "timestamp": "2024-02-26T10:00:08Z"
    },
    {
      "step": "workflow_step_3",
      "thought": "🔧 Step 3/5: Generating AI-powered fix and creating GitHub PR...",
      "timestamp": "2024-02-26T10:00:09Z"
    },
    {
      "step": "workflow_complete_3",
      "thought": "✅ GitHub PR #23 created with automated fix",
      "timestamp": "2024-02-26T10:00:15Z"
    },
    {
      "step": "workflow_step_4",
      "thought": "📢 Step 4/5: Sending Slack alert to team...",
      "timestamp": "2024-02-26T10:00:16Z"
    },
    {
      "step": "workflow_complete_4",
      "thought": "✅ Slack alert sent to team",
      "timestamp": "2024-02-26T10:00:17Z"
    },
    {
      "step": "workflow_step_5",
      "thought": "🎫 Step 5/5: Creating Jira ticket for tracking...",
      "timestamp": "2024-02-26T10:00:18Z"
    },
    {
      "step": "workflow_complete_5",
      "thought": "✅ Jira ticket KAN-7 created",
      "timestamp": "2024-02-26T10:00:20Z"
    },
    {
      "step": "workflow_success",
      "thought": "🎉 Complete autonomous workflow executed successfully!",
      "timestamp": "2024-02-26T10:00:21Z"
    },
    {
      "step": "response_ready",
      "thought": "✅ Response generated successfully!",
      "timestamp": "2024-02-26T10:00:22Z"
    }
  ]
}
```

---

## Frontend Changes Needed

### 1. Update AgentChat.tsx

**Location**: `frontend/src/pages/AgentChat.tsx`

**Changes**:

#### A. Add ReasoningStep interface (line ~10):
```typescript
interface ReasoningStep {
  step: string;
  thought: string;
  timestamp: string;
  details?: Record<string, any>;
}
```

#### B. Update Message interface (line ~15):
```typescript
interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  isError?: boolean;
  reasoningTrace?: ReasoningStep[];  // NEW
}
```

#### C. Add state for current reasoning (line ~50):
```typescript
const [currentReasoningTrace, setCurrentReasoningTrace] = useState<ReasoningStep[]>([]);
```

#### D. Update handleSubmit to use new endpoint (line ~200):
```typescript
const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
  event.preventDefault();
  if (!input.trim() || isLoading) return;

  const userMessage: Message = {
    role: 'user',
    content: input.trim(),
    timestamp: new Date().toISOString(),
  };

  setMessages((prev) => [...prev, userMessage]);
  setInput('');
  setIsLoading(true);
  setCurrentReasoningTrace([]);  // Clear previous reasoning

  try {
    // Call NEW reasoning trace endpoint
    const response = await axios.post('/api/agent/chat_with_reasoning', {
      message: input.trim(),
      conversation_history: messages.filter((m) => m.role !== 'system'),
    });

    const assistantMessage: Message = {
      role: 'assistant',
      content: response.data.response || 'I received your message but had trouble generating a response.',
      timestamp: new Date().toISOString(),
      reasoningTrace: response.data.reasoning_trace || [],  // Include reasoning trace
    };

    setMessages((prev) => [...prev, assistantMessage]);
    setCurrentReasoningTrace([]);  // Clear after completion
  } catch (error) {
    // ... error handling
  }
};
```

#### E. Update loading indicator to show real reasoning (line ~350):
```typescript
{/* Loading Indicator with REAL Reasoning */}
{isLoading && (
  <div className="flex gap-3">
    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-elastic-lightBlue text-elastic-blue flex items-center justify-center">
      <Bot className="h-4 w-4" />
    </div>
    <div className="flex-1 rounded-lg px-4 py-3 bg-white border border-elastic-border">
      <div className="flex items-center gap-2 text-sm text-elastic-gray mb-2">
        <Sparkles className="h-4 w-4 animate-pulse-subtle" />
        <span className="font-medium">ElasticSeer is working...</span>
      </div>
      
      {/* Show REAL reasoning trace as it happens */}
      {currentReasoningTrace.length > 0 && (
        <div className="mt-2 space-y-1 text-xs text-elastic-gray">
          {currentReasoningTrace.map((step, idx) => (
            <div 
              key={idx} 
              className="flex items-start gap-2 animate-fade-in"
              style={{ animationDelay: `${idx * 0.1}s` }}
            >
              <span className="text-elastic-blue">→</span>
              <span>{step.thought}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  </div>
)}
```

#### F. Add reasoning trace display in message (line ~300):
```typescript
{/* Message Content */}
<div className={`flex-1 rounded-lg px-4 py-3 ...`}>
  <div className="markdown-content ...">
    <ReactMarkdown remarkPlugins={[remarkGfm]}>{message.content}</ReactMarkdown>
  </div>
  
  {/* Show reasoning trace if available */}
  {message.reasoningTrace && message.reasoningTrace.length > 0 && (
    <details className="mt-3 text-xs">
      <summary className="cursor-pointer text-elastic-gray hover:text-elastic-blue font-medium">
        🧠 View Agent's Reasoning ({message.reasoningTrace.length} steps)
      </summary>
      <div className="mt-2 space-y-1 pl-4 border-l-2 border-elastic-lightBlue">
        {message.reasoningTrace.map((step, idx) => (
          <div key={idx} className="text-elastic-gray">
            <span className="text-elastic-blue">→</span> {step.thought}
            {step.details && Object.keys(step.details).length > 0 && (
              <span className="ml-2 text-xs text-elastic-gray opacity-75">
                {JSON.stringify(step.details)}
              </span>
            )}
          </div>
        ))}
      </div>
    </details>
  )}
  
  <div className="text-xs mt-2 ...">
    {new Date(message.timestamp).toLocaleTimeString()}
  </div>
</div>
```

---

## How It Works

### 1. User Sends Message
```
User: "Critical database issue. Investigate, fix, create PR, alert team."
```

### 2. Agent Shows Real-Time Reasoning
```
🤖 ElasticSeer agent initialized, analyzing your request...
🔍 Analyzing: 'Critical database issue. Investigate, fix...'
⚙️ Configuring Gemini 2.5 Flash with function calling...
🎯 Agent decided to call 1 function(s) to complete your request
🚀 Executing COMPLETE autonomous workflow for: Critical database issue
📝 Step 1/5: Registering incident in system...
✅ Incident INC-1005 registered successfully
🔍 Step 2/5: Searching codebase for relevant files...
✅ Found relevant code file: src/database/connection_pool.py
🔧 Step 3/5: Generating AI-powered fix and creating GitHub PR...
✅ GitHub PR #23 created with automated fix
📢 Step 4/5: Sending Slack alert to team...
✅ Slack alert sent to team
🎫 Step 5/5: Creating Jira ticket for tracking...
✅ Jira ticket KAN-7 created
🎉 Complete autonomous workflow executed successfully!
✅ Response generated successfully!
```

### 3. Final Response with Collapsible Reasoning
```
✅ Complete Autonomous Workflow Executed

1. ✅ Incident INC-1005 registered
2. ✅ Found code file: src/database/connection_pool.py
3. ✅ GitHub PR #23 created: https://github.com/...
4. ✅ Slack alert sent to #general
5. ✅ Jira ticket KAN-7 created: https://...

All autonomous actions completed!

[🧠 View Agent's Reasoning (15 steps) ▼]
```

---

## Benefits

### For Users:
- ✅ **Transparency**: See exactly what the agent is doing
- ✅ **Trust**: Understand the agent's decision-making process
- ✅ **Debugging**: Identify where issues occur in the workflow
- ✅ **Learning**: Understand how the agent approaches problems

### For Developers:
- ✅ **Debugging**: Track agent execution step-by-step
- ✅ **Monitoring**: See which tools are being called
- ✅ **Optimization**: Identify slow steps in workflows
- ✅ **Auditing**: Complete trace of agent actions

---

## Testing

### 1. Start Backend with New Endpoint
```bash
cd backend
uvicorn app.main:app --reload --port 8001
```

### 2. Test API Directly
```bash
curl -X POST http://localhost:8001/api/agent/chat_with_reasoning \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show recent incidents",
    "conversation_history": []
  }' | jq '.reasoning_trace'
```

### 3. Update Frontend and Test
After making the frontend changes:
```bash
cd frontend
npm run dev
```

Visit http://localhost:5173 and send a message. You should see:
- Real-time reasoning as the agent works
- Collapsible reasoning trace in the final message
- Detailed step-by-step breakdown

---

## Example Workflows with Reasoning

### Simple Query:
```
User: "Show recent incidents"

Reasoning:
→ 🤖 ElasticSeer agent initialized
→ 🔍 Analyzing: 'Show recent incidents'
→ 📊 Querying Elasticsearch for recent incidents...
→ ✅ Query completed successfully
→ ✅ Response ready!
```

### Complex Workflow:
```
User: "Critical auth issue. Investigate, fix, PR, alert team."

Reasoning:
→ 🤖 ElasticSeer agent initialized
→ 🔍 Analyzing request
→ 🎯 Agent decided to call autonomous_incident_response
→ 🚀 Executing COMPLETE autonomous workflow
→ 📝 Step 1/5: Registering incident...
→ ✅ Incident INC-1006 registered
→ 🔍 Step 2/5: Searching codebase...
→ ✅ Found: src/auth/jwt_validator.py
→ 🔧 Step 3/5: Creating GitHub PR...
→ ✅ PR #24 created
→ 📢 Step 4/5: Sending Slack alert...
→ ✅ Slack sent
→ 🎫 Step 5/5: Creating Jira ticket...
→ ✅ Jira KAN-8 created
→ 🎉 Workflow complete!
```

---

## Next Steps

1. ✅ Backend is ready (`agent_chat_with_reasoning.py` created)
2. ✅ Router registered in `main.py`
3. ⏳ Update frontend `AgentChat.tsx` with changes above
4. ⏳ Test the new reasoning trace feature
5. ⏳ Optionally add streaming for real-time updates (future enhancement)

---

**Status**: Backend complete, frontend changes documented above  
**Impact**: Massive improvement in transparency and user trust  
**Effort**: ~30 minutes to update frontend
