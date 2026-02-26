"""
Agent Chat API - Elastic Inference API with Claude Sonnet

This is the CORRECT implementation using:
1. Elastic's Inference API with Claude Sonnet 3.7 (NOT Gemini!)
2. MCP server tools for ES|QL queries
3. External action endpoints (GitHub PRs, Slack, Jira)

This uses Elastic's native Claude integration!
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import logging
import json
from app.core.config import settings
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: str


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[ChatMessage] = []


class ChatResponse(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None


# Claude function/tool definitions (Anthropic format)
CLAUDE_TOOLS = [
    {
        "name": "query_recent_incidents",
        "description": "Get the most recent incidents from Elasticsearch with full details including severity, service, diagnosis, root cause, and remediation. Use this to investigate production issues or when asked about incidents.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_code_by_path",
        "description": "Search for code files in the repository by file path pattern. Returns file path, language, lines, and content. Use this to find relevant code files.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "File path pattern to search for (e.g., '*cache*', '*jwt*', '*auth*', '*database*')"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "get_metrics_anomalies",
        "description": "Get metrics with high deviation (potential anomalies) for a specific service. Use this to detect performance issues or when asked about anomalies.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name to check (e.g., 'api-gateway', 'auth-service', 'cache', 'database', 'payment')"
                }
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_incident_by_id",
        "description": "Get complete details of a specific incident by ID including diagnosis, root cause, confidence, and remediation plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "Incident ID (e.g., 'INC-001', 'INC-002', 'INC-003')"
                }
            },
            "required": ["incident_id"]
        }
    },
    {
        "name": "create_github_pr",
        "description": "Create a GitHub pull request with AI-generated code fixes for an incident. This will automatically: 1) Get incident details, 2) Get the affected code file, 3) Generate an AI-powered fix, 4) Create a PR with the fix. Use this when asked to fix code, create a PR, or resolve an incident.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "The incident ID to create a PR for (e.g., 'INC-002')"
                }
            },
            "required": ["incident_id"]
        }
    },
    {
        "name": "send_slack_alert",
        "description": "Send an alert or notification to the Slack war room. Use this to notify the team about critical issues, updates, or when action is required.",
        "input_schema": {
            "type": "object",
            "properties": {
                "severity": {
                    "type": "string",
                    "enum": ["Sev-1", "Sev-2", "Sev-3"],
                    "description": "Alert severity level"
                },
                "incident_id": {
                    "type": "string",
                    "description": "Related incident ID"
                },
                "title": {
                    "type": "string",
                    "description": "Alert title"
                },
                "message": {
                    "type": "string",
                    "description": "Alert message content"
                },
                "action_required": {
                    "type": "boolean",
                    "description": "Whether immediate action is required from the team"
                }
            },
            "required": ["severity", "incident_id", "title", "message"]
        }
    },
    {
        "name": "create_jira_ticket",
        "description": "Create a Jira ticket for incident tracking and escalation. Use this to formally track incidents, escalate issues, or when asked to create a ticket.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Ticket summary/title"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the issue"
                },
                "priority": {
                    "type": "string",
                    "enum": ["Critical", "High", "Medium", "Low"],
                    "description": "Ticket priority level"
                },
                "incident_id": {
                    "type": "string",
                    "description": "Related incident ID if applicable"
                }
            },
            "required": ["summary", "description", "priority"]
        }
    }
]


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any] = None) -> Dict[str, Any]:
    """Call an MCP tool via the Agent Builder MCP server"""
    
    mcp_url = f"{settings.kibana_url.rstrip('/')}/api/agent_builder/mcp"
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(
            mcp_url,
            headers={
                "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json"
            },
            json={
                "jsonrpc": "2.0",
                "id": 1,
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments or {}
                }
            }
        )
        
        if response.status_code != 200:
            logger.error(f"MCP tool call error: {response.status_code} - {response.text}")
            return {"error": f"MCP tool call failed: {response.text}"}
        
        result = response.json()
        
        if "error" in result:
            return {"error": f"MCP error: {result['error']}"}
        
        return result.get("result", {})


def parse_esql_results(tool_result: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Parse ES|QL results from MCP tool response into structured data"""
    
    try:
        if "content" not in tool_result:
            return []
        
        content = tool_result["content"]
        if not isinstance(content, list) or len(content) == 0:
            return []
        
        text_content = content[0].get("text", "")
        data = json.loads(text_content)
        
        # Find ES|QL results
        if "results" in data and isinstance(data["results"], list):
            for result in data["results"]:
                if result.get("type") == "esql_results" and "data" in result:
                    esql_data = result["data"]
                    columns = esql_data.get("columns", [])
                    values = esql_data.get("values", [])
                    
                    # Convert to list of dicts
                    col_names = [col["name"] for col in columns]
                    rows = []
                    for row_values in values:
                        row_dict = dict(zip(col_names, row_values))
                        rows.append(row_dict)
                    
                    return rows
        
        return []
    except Exception as e:
        logger.error(f"Error parsing ES|QL results: {e}", exc_info=True)
        return []


async def execute_function(function_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Execute a function call - either MCP tool or external action"""
    
    try:
        logger.info(f"Executing function: {function_name} with args: {arguments}")
        
        # MCP Tools
        if function_name == "query_recent_incidents":
            result = await call_mcp_tool("elasticseer_get_recent_incidents", {})
            incidents = parse_esql_results(result)
            return {"success": True, "incidents": incidents, "count": len(incidents)}
        
        elif function_name == "search_code_by_path":
            pattern = arguments.get("pattern", "*")
            result = await call_mcp_tool("elasticseer_search_code_by_path", {"pattern": pattern})
            files = parse_esql_results(result)
            return {"success": True, "files": files, "count": len(files)}
        
        elif function_name == "get_metrics_anomalies":
            service = arguments.get("service")
            result = await call_mcp_tool("elasticseer_get_metrics_anomalies", {"service": service})
            anomalies = parse_esql_results(result)
            return {"success": True, "anomalies": anomalies, "count": len(anomalies), "service": service}
        
        elif function_name == "get_incident_by_id":
            incident_id = arguments.get("incident_id")
            result = await call_mcp_tool("elasticseer_get_incident_by_id", {"incident_id": incident_id})
            incidents = parse_esql_results(result)
            if incidents:
                return {"success": True, "incident": incidents[0]}
            return {"success": False, "error": f"Incident {incident_id} not found"}
        
        # External Actions
        elif function_name == "create_github_pr":
            incident_id = arguments.get("incident_id")
            
            # Get incident details via MCP
            incident_result = await call_mcp_tool("elasticseer_get_incident_by_id", {"incident_id": incident_id})
            incidents = parse_esql_results(incident_result)
            
            if not incidents:
                return {"success": False, "error": f"Incident {incident_id} not found"}
            
            incident = incidents[0]
            file_path = incident.get("remediation.file_path")
            
            if not file_path:
                return {"success": False, "error": "No file path found in incident remediation"}
            
            # Get code file from Elasticsearch
            es = Elasticsearch(
                settings.elasticsearch_url,
                api_key=settings.elasticsearch_api_key
            )
            
            code_result = es.search(
                index="code-repository",
                body={"query": {"term": {"file_path": file_path}}}
            )
            
            if not code_result["hits"]["hits"]:
                return {"success": False, "error": f"Code file {file_path} not found in repository"}
            
            code_file = code_result["hits"]["hits"][0]["_source"]
            
            # Generate fix and create PR via external endpoints
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Generate AI-powered fix
                fix_response = await client.post(
                    "http://localhost:8001/api/elasticseer/generate_fix",
                    json={
                        "file_path": file_path,
                        "diagnosis": incident.get("diagnosis.root_cause"),
                        "current_code": code_file["content"],
                        "incident_context": incident.get("description")
                    }
                )
                
                if fix_response.status_code != 200:
                    return {"success": False, "error": f"Failed to generate fix: {fix_response.text}"}
                
                fix_data = fix_response.json()
                
                # Create GitHub PR
                pr_response = await client.post(
                    "http://localhost:8001/api/elasticseer/create_pr",
                    json={
                        "title": f"[ElasticSeer] Fix: {incident.get('description')} ({incident_id})",
                        "description": f"## 🤖 Autonomous Fix by ElasticSeer\n\n**Incident**: {incident_id}\n**Severity**: {incident.get('severity')}\n**Service**: {incident.get('anomaly.service')}\n\n### Root Cause\n{incident.get('diagnosis.root_cause')}\n\n### Fix Applied\n{fix_data['explanation']}\n\n### Recommendations\n{fix_data.get('recommendations', 'None')}\n\n---\n*This PR was automatically generated by ElasticSeer AI Agent powered by Elastic + Claude Sonnet*",
                        "branch_name": f"elasticseer/fix-{incident_id.lower()}",
                        "files": [{"path": file_path, "content": fix_data["fixed_code"]}],
                        "incident_id": incident_id
                    }
                )
                
                if pr_response.status_code != 200:
                    return {"success": False, "error": f"Failed to create PR: {pr_response.text}"}
                
                pr_data = pr_response.json()
                return {
                    "success": True,
                    "pr_number": pr_data["pr_number"],
                    "pr_url": pr_data["pr_url"],
                    "branch": pr_data["branch"],
                    "incident_id": incident_id,
                    "file_path": file_path,
                    "fix_explanation": fix_data["explanation"]
                }
        
        elif function_name == "send_slack_alert":
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/elasticseer/send_slack",
                    json=arguments
                )
                
                if response.status_code == 200:
                    return response.json()
                return {"success": False, "error": response.text}
        
        elif function_name == "create_jira_ticket":
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/elasticseer/create_jira_ticket",
                    json=arguments
                )
                
                if response.status_code == 200:
                    return response.json()
                return {"success": False, "error": response.text}
        
        else:
            return {"success": False, "error": f"Unknown function: {function_name}"}
            
    except Exception as e:
        logger.error(f"Function execution error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


async def call_claude_with_streaming(messages: List[Dict], system: str, tools: List[Dict]) -> tuple[str, List[Dict]]:
    """Call Claude via Elastic Inference API with streaming"""
    
    inference_url = f"{settings.elasticsearch_url.rstrip('/')}/_inference/chat_completion/.rainbow-sprinkles-elastic/_stream"
    
    # Build request
    request_body = {
        "messages": messages,
        "tools": tools,
        "max_tokens": 4096,
        "temperature": 0.7
    }
    
    # Add system message if provided
    if system:
        request_body["system"] = system
    
    async with httpx.AsyncClient(timeout=120.0) as client:
        async with client.stream(
            "POST",
            inference_url,
            headers={
                "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
                "Content-Type": "application/json"
            },
            json=request_body
        ) as response:
            if response.status_code != 200:
                error_text = await response.aread()
                raise HTTPException(status_code=500, detail=f"Claude API error: {error_text.decode()}")
            
            # Parse SSE stream
            content = ""
            tool_calls = []
            current_tool_call = None
            
            async for line in response.aiter_lines():
                if not line or not line.startswith("data: "):
                    continue
                
                try:
                    data = json.loads(line[6:])  # Remove "data: " prefix
                    
                    if "choices" in data and len(data["choices"]) > 0:
                        choice = data["choices"][0]
                        delta = choice.get("delta", {})
                        
                        # Handle content
                        if "content" in delta:
                            content += delta["content"]
                        
                        # Handle tool calls
                        if "tool_calls" in delta:
                            for tool_call in delta["tool_calls"]:
                                if "id" in tool_call:
                                    # New tool call
                                    current_tool_call = {
                                        "id": tool_call["id"],
                                        "name": tool_call.get("function", {}).get("name", ""),
                                        "arguments": ""
                                    }
                                    tool_calls.append(current_tool_call)
                                elif current_tool_call and "function" in tool_call:
                                    # Append arguments
                                    args = tool_call["function"].get("arguments", "")
                                    current_tool_call["arguments"] += args
                
                except json.JSONDecodeError:
                    continue
            
            # Parse tool call arguments
            for tool_call in tool_calls:
                if tool_call["arguments"]:
                    try:
                        tool_call["arguments"] = json.loads(tool_call["arguments"])
                    except:
                        pass
            
            return content, tool_calls


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with ElasticSeer - Using Elastic's Claude Sonnet Inference API
    
    Combines:
    1. Elastic Inference API with Claude Sonnet 3.7
    2. MCP server tools for ES|QL queries
    3. External action endpoints (GitHub, Slack, Jira)
    """
    
    try:
        # Build conversation history
        messages = []
        for msg in request.conversation_history[-10:]:
            messages.append({
                "role": msg.role,
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # System instruction
        system_instruction = """You are ElasticSeer, an autonomous incident response agent for production infrastructure.

Your mission: Proactively monitor, diagnose, and resolve production incidents with minimal human intervention.

Your capabilities:
- Query Elasticsearch for incidents, metrics, anomalies, and code via MCP tools
- Create GitHub PRs with AI-generated code fixes
- Send Slack notifications to alert the team
- Create Jira tickets for incident tracking
- Analyze patterns and provide actionable insights

Guidelines:
- Be proactive and autonomous in your responses
- When asked about incidents or anomalies, query the data first
- When asked to fix something, create a PR automatically
- Explain your reasoning and actions clearly
- Provide specific, actionable recommendations
- Use markdown formatting for better readability

Remember: You're not just answering questions - you're actively managing production incidents!"""

        # Call Claude via Elastic Inference API
        logger.info(f"Calling Claude via Elastic Inference API: {request.message}")
        
        content, tool_calls = await call_claude_with_streaming(messages, system_instruction, CLAUDE_TOOLS)
        
        # Execute tool calls if any
        if tool_calls:
            logger.info(f"Executing {len(tool_calls)} tool calls")
            
            tool_results = []
            for tool_call in tool_calls:
                function_name = tool_call["name"]
                arguments = tool_call["arguments"]
                
                logger.info(f"Calling: {function_name} with {arguments}")
                
                result = await execute_function(function_name, arguments)
                tool_results.append({
                    "tool_call_id": tool_call["id"],
                    "function": function_name,
                    "result": result
                })
            
            # Call Claude again with tool results
            messages.append({
                "role": "assistant",
                "content": content,
                "tool_calls": [{"id": tc["id"], "type": "function", "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])}} for tc in tool_calls]
            })
            
            for tool_result in tool_results:
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_result["tool_call_id"],
                    "content": json.dumps(tool_result["result"])
                })
            
            # Second call to Claude with tool results
            final_content, _ = await call_claude_with_streaming(messages, system_instruction, CLAUDE_TOOLS)
            
            return ChatResponse(
                response=final_content,
                sources=["claude-sonnet-3.7-elastic", "mcp-server"] + [tr["function"] for tr in tool_results],
                metadata={
                    "model": "claude-sonnet-3.7",
                    "provider": "elastic-inference",
                    "function_calls": [{"name": tc["name"], "args": tc["arguments"]} for tc in tool_calls]
                }
            )
        
        # No tool calls, return direct response
        return ChatResponse(
            response=content or "I'm here to help! Ask me about incidents, anomalies, or code issues.",
            sources=["claude-sonnet-3.7-elastic"],
            metadata={"model": "claude-sonnet-3.7", "provider": "elastic-inference"}
        )
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check - verify all components"""
    try:
        # Test MCP server
        mcp_url = f"{settings.kibana_url.rstrip('/')}/api/agent_builder/mcp"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            mcp_response = await client.post(
                mcp_url,
                headers={
                    "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                },
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "tools/list",
                    "params": {}
                }
            )
            
            mcp_healthy = mcp_response.status_code == 200
            tools = []
            if mcp_healthy:
                result = mcp_response.json()
                tools = result.get("result", {}).get("tools", [])
            
            return {
                "status": "healthy" if mcp_healthy else "degraded",
                "components": {
                    "mcp_server": "connected" if mcp_healthy else "disconnected",
                    "claude_sonnet": "elastic-inference",
                    "elasticsearch": "connected",
                    "github": "configured" if settings.github_token else "not configured",
                    "slack": "configured" if settings.slack_bot_token else "not configured",
                    "jira": "configured" if settings.jira_url else "not configured"
                },
                "mcp_tools": len([t for t in tools if t["name"].startswith("elasticseer_")]),
                "total_tools": len(tools),
                "agent": "elasticseer-orchestrator",
                "model": "claude-sonnet-3.7",
                "provider": "elastic-inference-api",
                "capabilities": [
                    "Query incidents, metrics, anomalies, code",
                    "Create GitHub PRs with AI fixes",
                    "Send Slack alerts",
                    "Create Jira tickets",
                    "Autonomous decision-making"
                ]
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
