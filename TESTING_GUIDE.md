# ElasticSeer Chat UI - Testing Guide

## 🧪 Complete Testing Checklist

This guide walks you through testing every component of the ElasticSeer chat UI system.

## Prerequisites

Before testing, ensure:

✅ Backend `.env` file is configured  
✅ Elasticsearch cluster is running  
✅ Kibana is accessible  
✅ ElasticSeer agent is deployed in Kibana  
✅ ES|QL tools are created  
✅ Sample data is loaded  

## 1. Backend Testing

### 1.1 Test Backend Health

```bash
curl http://localhost:8001/health
```

**Expected Response:**
```json
{
  "status": "healthy"
}
```

### 1.2 Test Agent Chat Health

```bash
curl http://localhost:8001/api/agent/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "kibana_reachable": true,
  "agent_id": "elasticseer-orchestrator"
}
```

### 1.3 Test Chat Endpoint

```bash
curl -X POST http://localhost:8001/api/agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Show me recent incidents",
    "conversation_history": []
  }'
```

**Expected Response:**
```json
{
  "response": "Here are the recent incidents from the incident-history index:\n\n1. **INC-001**...",
  "sources": ["incident-history"],
  "metadata": {}
}
```

### 1.4 Test Autonomous Tools

#### Generate Fix
```bash
curl -X POST http://localhost:8001/api/elasticseer/generate_fix \
  -H "Content-Type: application/json" \
  -d '{
    "file_path": "src/auth/jwt_handler.py",
    "diagnosis": "JWT token expiration too short",
    "current_code": "TOKEN_EXPIRY = 3600"
  }'
```

#### Create PR
```bash
curl -X POST http://localhost:8001/api/elasticseer/create_pr \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test PR",
    "description": "Testing PR creation",
    "branch_name": "test-branch",
    "files": [
      {
        "path": "test.txt",
        "content": "Hello World"
      }
    ],
    "incident_id": "TEST-001"
  }'
```

## 2. Frontend Testing

### 2.1 Visual Testing

Open http://localhost:5173 and verify:

#### Layout
- [ ] Sidebar is visible on the left
- [ ] Main chat area is in the center
- [ ] Header shows "ElasticSeer" with bot icon
- [ ] Input box is at the bottom

#### Styling
- [ ] Colors match Elastic theme (blue #0077CC)
- [ ] Fonts are Inter or similar
- [ ] Rounded corners on components
- [ ] Subtle shadows on cards

#### Sidebar
- [ ] "New conversation" button is visible
- [ ] Conversation list is empty initially
- [ ] Footer shows "ElasticSeer Agent" and "Powered by Kibana Agent Builder"

#### Chat Area
- [ ] Welcome message from agent is displayed
- [ ] Quick prompt buttons are visible (4 buttons)
- [ ] Input box has placeholder "Ask ElasticSeer anything..."
- [ ] Send button is visible (disabled when empty)

### 2.2 Interaction Testing

#### Test 1: Send a Message

1. Type "Hello" in the input box
2. Press Enter or click send button

**Expected:**
- [ ] Message appears in chat with blue background
- [ ] User avatar (blue circle with user icon) is shown
- [ ] Loading indicator appears (bot avatar with "thinking" text)
- [ ] Agent response appears after a few seconds
- [ ] Agent message has white background with border
- [ ] Bot avatar (light blue circle with bot icon) is shown
- [ ] Timestamp is shown below each message

#### Test 2: Use Quick Prompts

1. Click "Show me recent incidents" button

**Expected:**
- [ ] Input box is filled with the prompt text
- [ ] Message is NOT sent automatically
- [ ] User can edit the prompt before sending
- [ ] Pressing Enter sends the message

#### Test 3: Multi-line Messages

1. Type "Line 1"
2. Press Shift+Enter
3. Type "Line 2"
4. Press Enter

**Expected:**
- [ ] Message contains both lines
- [ ] Line break is preserved in display

#### Test 4: Markdown Rendering

Send this message:
```
Show me a **bold** word and a `code` snippet
```

**Expected:**
- [ ] "bold" is rendered in bold
- [ ] "code" is rendered in monospace with gray background

#### Test 5: Long Messages

Send a very long message (500+ characters)

**Expected:**
- [ ] Message is fully visible
- [ ] Scrollbar appears if needed
- [ ] Layout doesn't break

### 2.3 Conversation Management

#### Test 1: Create New Conversation

1. Click "New conversation" button

**Expected:**
- [ ] New conversation is created
- [ ] Conversation list shows "New Chat"
- [ ] Chat area is cleared
- [ ] Welcome message is shown

#### Test 2: Switch Conversations

1. Send a message in conversation 1
2. Create a new conversation
3. Send a different message in conversation 2
4. Click on conversation 1 in the sidebar

**Expected:**
- [ ] Conversation 1 messages are restored
- [ ] Conversation 2 messages are not visible
- [ ] Active conversation is highlighted in sidebar

#### Test 3: Delete Conversation

1. Hover over a conversation in the sidebar
2. Click the trash icon

**Expected:**
- [ ] Conversation is removed from list
- [ ] If it was active, next conversation is loaded
- [ ] If it was the last conversation, a new one is created

#### Test 4: Conversation Titles

1. Create a new conversation
2. Send a message: "This is a test message for the title"

**Expected:**
- [ ] Conversation title changes from "New Chat" to "This is a test message for the title" (truncated to 50 chars)

#### Test 5: Persistence

1. Send several messages
2. Refresh the page

**Expected:**
- [ ] All conversations are still visible
- [ ] All messages are preserved
- [ ] Active conversation is restored

### 2.4 Loading States

#### Test 1: Loading Indicator

1. Send a message
2. Observe the loading indicator

**Expected:**
- [ ] Bot avatar with sparkle icon appears
- [ ] "ElasticSeer is thinking..." text is shown
- [ ] Three animated progress messages appear:
  - "→ Analyzing your request..."
  - "→ Querying Elasticsearch..."
  - "→ Generating response..."
- [ ] Messages have staggered animation

#### Test 2: Send Button State

1. Observe send button when input is empty
2. Type a message
3. Observe send button while loading

**Expected:**
- [ ] Disabled (gray) when input is empty
- [ ] Enabled (blue) when input has text
- [ ] Shows sparkle icon while loading
- [ ] Disabled while loading

### 2.5 Error Handling

#### Test 1: Backend Offline

1. Stop the backend server
2. Send a message

**Expected:**
- [ ] Error message appears in chat
- [ ] Error has red background
- [ ] Error icon (alert circle) is shown
- [ ] Error message explains the issue

#### Test 2: Network Timeout

1. Send a message that takes too long (if possible)

**Expected:**
- [ ] Timeout error appears after 60 seconds
- [ ] Error message is clear

#### Test 3: Invalid Response

1. Send a message that causes an error in the backend

**Expected:**
- [ ] Error message appears
- [ ] User can retry

### 2.6 Responsive Design

#### Test 1: Sidebar Toggle

1. Click the menu icon in the header

**Expected:**
- [ ] Sidebar slides out (width becomes 0)
- [ ] Chat area expands to fill space
- [ ] Click again to show sidebar

#### Test 2: Mobile View

1. Resize browser to mobile width (< 768px)

**Expected:**
- [ ] Layout adapts to mobile
- [ ] Sidebar is hidden by default
- [ ] Chat area is full width
- [ ] Input box is still usable

#### Test 3: Tablet View

1. Resize browser to tablet width (768px - 1024px)

**Expected:**
- [ ] Layout looks good
- [ ] Sidebar is visible
- [ ] Chat area has appropriate width

## 3. Integration Testing

### 3.1 End-to-End: Simple Query

**Test:** Ask about recent incidents

1. Open http://localhost:5173
2. Type: "Show me recent incidents"
3. Press Enter

**Expected Flow:**
1. Message appears in chat
2. Loading indicator shows
3. Backend receives request
4. Backend calls Kibana API
5. Agent uses `elasticseer.get_recent_incidents` tool
6. Agent queries Elasticsearch
7. Agent formats response
8. Backend returns response
9. Frontend displays response
10. Response includes incident details

**Verify:**
- [ ] Response contains incident IDs (INC-001, INC-002, etc.)
- [ ] Response includes severity levels
- [ ] Response includes service names
- [ ] Response is formatted with markdown

### 3.2 End-to-End: Code Search

**Test:** Search for code

1. Type: "Search for authentication code"
2. Press Enter

**Expected:**
- [ ] Agent uses `elasticseer.search_code_by_path` tool
- [ ] Response includes file paths
- [ ] Response includes code snippets
- [ ] Code is formatted with syntax highlighting

### 3.3 End-to-End: Anomaly Detection

**Test:** Check for anomalies

1. Type: "What are the current anomalies in the api-gateway service?"
2. Press Enter

**Expected:**
- [ ] Agent uses `elasticseer.get_metrics_anomalies` tool
- [ ] Response includes metric names
- [ ] Response includes deviation values
- [ ] Response includes timestamps

### 3.4 End-to-End: PR Creation (Manual)

**Test:** Create a PR

1. Type: "Create a PR for INC-002"
2. Press Enter

**Expected (Current Behavior):**
- [ ] Agent explains how to create a PR
- [ ] Agent provides the command to run
- [ ] Agent mentions the autonomous action executor script

**Expected (Future with Workflows):**
- [ ] Agent triggers workflow
- [ ] Workflow creates PR
- [ ] Agent returns PR URL
- [ ] PR is visible on GitHub

## 4. Performance Testing

### 4.1 Response Time

**Test:** Measure response time for simple queries

1. Send: "Show me recent incidents"
2. Measure time from send to response

**Expected:**
- [ ] Response within 5 seconds
- [ ] No timeout errors

### 4.2 Large Responses

**Test:** Handle large responses

1. Send: "Show me all metrics for the last hour"
2. Wait for response

**Expected:**
- [ ] Response is displayed correctly
- [ ] No layout issues
- [ ] Scrollbar appears if needed
- [ ] No browser freeze

### 4.3 Multiple Conversations

**Test:** Create many conversations

1. Create 20 conversations
2. Send messages in each
3. Switch between them

**Expected:**
- [ ] All conversations load quickly
- [ ] No performance degradation
- [ ] localStorage doesn't exceed limits

## 5. Security Testing

### 5.1 API Key Protection

**Test:** Verify API key is not exposed

1. Open browser DevTools
2. Go to Network tab
3. Send a message
4. Inspect request to `/api/agent/chat`

**Expected:**
- [ ] Request does NOT contain Elasticsearch API key
- [ ] Request does NOT contain Kibana URL
- [ ] Request only contains message and conversation history

### 5.2 CORS

**Test:** Verify CORS is configured correctly

1. Try to access backend from a different origin

**Expected:**
- [ ] Requests from localhost:5173 are allowed
- [ ] Requests from other origins are blocked

### 5.3 Input Sanitization

**Test:** Try to inject malicious content

1. Send: `<script>alert('XSS')</script>`
2. Send: `**[Click me](javascript:alert('XSS'))**`

**Expected:**
- [ ] Script tags are escaped
- [ ] JavaScript URLs are not executed
- [ ] Content is displayed as text

## 6. Accessibility Testing

### 6.1 Keyboard Navigation

**Test:** Navigate with keyboard only

1. Tab through the interface
2. Use Enter to send messages
3. Use arrow keys to navigate

**Expected:**
- [ ] All interactive elements are reachable
- [ ] Focus indicators are visible
- [ ] Enter key sends messages
- [ ] Shift+Enter adds new line

### 6.2 Screen Reader

**Test:** Use a screen reader (VoiceOver, NVDA, JAWS)

**Expected:**
- [ ] All text is read correctly
- [ ] Buttons have descriptive labels
- [ ] Messages are announced
- [ ] Loading states are announced

### 6.3 Color Contrast

**Test:** Check color contrast ratios

**Expected:**
- [ ] Text on blue background has sufficient contrast
- [ ] Gray text on white background has sufficient contrast
- [ ] All text meets WCAG AA standards

## 7. Browser Compatibility

Test in multiple browsers:

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

**Verify:**
- [ ] Layout is consistent
- [ ] Functionality works
- [ ] No console errors
- [ ] Styles are applied correctly

## 8. Troubleshooting Common Issues

### Issue: Frontend can't reach backend

**Symptoms:**
- Error: "Failed to communicate with the agent"
- Network error in console

**Solutions:**
1. Check backend is running: `curl http://localhost:8001/health`
2. Check Vite proxy in `vite.config.ts`
3. Check CORS settings in `backend/app/main.py`
4. Check firewall settings

### Issue: Backend can't reach Kibana

**Symptoms:**
- Error: "Kibana Agent Builder API error"
- 401 Unauthorized

**Solutions:**
1. Check `KIBANA_URL` in `backend/.env`
2. Check `ELASTICSEARCH_API_KEY` is valid
3. Test Kibana connection: `curl http://localhost:8001/api/agent/health`
4. Verify agent is deployed in Kibana

### Issue: Agent not responding

**Symptoms:**
- Timeout error
- No response after long wait

**Solutions:**
1. Check agent is deployed: Kibana → Agent Builder → Agents
2. Check agent ID is correct: `elasticseer-orchestrator`
3. Check ES|QL tools are created
4. Check Elasticsearch indices have data
5. Increase timeout in `backend/app/api/agent_chat.py`

### Issue: Conversation history not saving

**Symptoms:**
- Conversations disappear on refresh
- localStorage errors in console

**Solutions:**
1. Check browser localStorage is enabled
2. Check localStorage quota (5-10MB limit)
3. Clear localStorage: `localStorage.clear()`
4. Check for JavaScript errors in console

### Issue: Styles not loading

**Symptoms:**
- Plain HTML with no styling
- Tailwind classes not applied

**Solutions:**
1. Check Tailwind is installed: `npm list tailwindcss`
2. Check `tailwind.config.js` exists
3. Check `postcss.config.js` exists
4. Rebuild: `npm run build`
5. Clear browser cache

## 9. Success Criteria

The system is working correctly if:

✅ Frontend loads without errors  
✅ Backend health check passes  
✅ Agent health check passes  
✅ Messages are sent and received  
✅ Agent responses are displayed correctly  
✅ Conversation history is saved  
✅ Markdown is rendered properly  
✅ Loading states are shown  
✅ Errors are handled gracefully  
✅ UI matches Kibana's design  
✅ All ES|QL tools work  
✅ Autonomous actions can be triggered  

## 10. Next Steps After Testing

Once all tests pass:

1. **Document any issues** found during testing
2. **Create GitHub issues** for bugs
3. **Update documentation** with any changes
4. **Deploy to staging** environment
5. **Perform user acceptance testing**
6. **Deploy to production**

## 📊 Test Results Template

Use this template to track your testing:

```markdown
# ElasticSeer Chat UI - Test Results

**Date:** YYYY-MM-DD
**Tester:** Your Name
**Environment:** Development / Staging / Production

## Backend Tests
- [ ] Health check: PASS / FAIL
- [ ] Agent health check: PASS / FAIL
- [ ] Chat endpoint: PASS / FAIL
- [ ] Autonomous tools: PASS / FAIL

## Frontend Tests
- [ ] Visual layout: PASS / FAIL
- [ ] Send message: PASS / FAIL
- [ ] Quick prompts: PASS / FAIL
- [ ] Markdown rendering: PASS / FAIL
- [ ] Conversation management: PASS / FAIL
- [ ] Loading states: PASS / FAIL
- [ ] Error handling: PASS / FAIL

## Integration Tests
- [ ] Simple query: PASS / FAIL
- [ ] Code search: PASS / FAIL
- [ ] Anomaly detection: PASS / FAIL
- [ ] PR creation: PASS / FAIL

## Performance Tests
- [ ] Response time: PASS / FAIL
- [ ] Large responses: PASS / FAIL
- [ ] Multiple conversations: PASS / FAIL

## Security Tests
- [ ] API key protection: PASS / FAIL
- [ ] CORS: PASS / FAIL
- [ ] Input sanitization: PASS / FAIL

## Accessibility Tests
- [ ] Keyboard navigation: PASS / FAIL
- [ ] Screen reader: PASS / FAIL
- [ ] Color contrast: PASS / FAIL

## Browser Compatibility
- [ ] Chrome: PASS / FAIL
- [ ] Firefox: PASS / FAIL
- [ ] Safari: PASS / FAIL
- [ ] Edge: PASS / FAIL

## Issues Found
1. Issue description
2. Issue description

## Overall Result
PASS / FAIL

## Notes
Additional observations...
```

Happy testing! 🧪
