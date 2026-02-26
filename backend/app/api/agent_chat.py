"""
Agent Chat API - Full Agent Experience with Claude + MCP Tools

This endpoint combines:
1. Claude Sonnet 3.7 for agentic intelligence
2. MCP server tools for ES|QL queries
3. External action endpoints (GitHub, Slack, Jira)

This is the COMPLETE agent experience!
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import logging
import json
import re
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


# Function definitions for Claude - combining MCP tools + external actions
FUNCTION_DEFINITIONS = [
    {
        "name": "query_recent_incidents",
        "description": "Get the most recent incidents from Elasticsearch with full details including severity, service, diagnosis, and remediation. Use this to investigate production issues.",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "search_code_by_path",
        "description": "Search for code files in the repository by file path pattern. Returns file path, language, and content. Use this to find relevant code.",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {
                    "type": "string",
                    "description": "File path pattern to search for (e.g., '*cache*', '*jwt*', '*auth*')"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "get_metrics_anomalies",
        "description": "Get metrics with high deviation (potential anomalies) for a specific service. Use this to detect performance issues.",
        "input_schema": {
            "type": "object",
            "properties": {
                "service": {
                    "type": "string",
                    "description": "Service name (e.g., 'api-gateway', 'auth-service', 'cache')"
                }
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_incident_by_id",
        "description": "Get complete details of a specific incident by ID including diagnosis, root cause, and remediation plan.",
        "input_schema": {
            "type": "object",
            "properties": {
                "incident_id": {
                    "type": "string",
                    "description": "Incident ID (e.g., 'INC-001', 'INC-002')"
                }
            },
            "required": ["incident_id"]
        }
    },
    {
        "name": "create_github_pr",
        "description": "Create a GitHub pull request with AI-generated code fixes for an incident. This will automatically generate the fix and create the PR. Use this when asked to fix code or create a PR.",
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
        "description": "Send an alert or notification to the Slack war room. Use this to notify the team about critical issues or updates.",
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
                    "description": "Alert message"
                },
                "action_required": {
                    "type": "boolean",
                    "description": "Whether immediate action is required"
                }
            },
            "required": ["severity", "incident_id", "title", "message"]
        }
    },
    {
        "name": "create_jira_ticket",
        "description": "Create a Jira ticket for incident tracking and escalation. Use this to escalate issues or track incidents formally.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {
                    "type": "string",
                    "description": "Ticket summary/title"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description"
                },
                "priority": {
                    "type": "string",
                    "enum": ["Critical", "High", "Medium", "Low"],
                    "description": "Ticket priority"
                },
                "incident_id": {
                    "type": "string",
                    "description": "Related incident ID"
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
            return {"success": True, "anomalies": anomalies, "count": len(anomalies)}
        
        elif function_name == "get_incident_by_id":
            incident_id = arguments.get("incident_id")
            result = await call_mcp_tool("elasticseer_get_incident_by_id", {"incident_id": incident_id})
            incidents = parse_esql_results(result)
            if incidents:
                return {"success": True, "incident": incidents[0]}
            return {"success": False, "error": "Incident not found"}
        
        # External Actions
        elif function_name == "create_github_pr":
            incident_id = arguments.get("incident_id")
            
            # Get incident details
            incident_result = await call_mcp_tool("elasticseer_get_incident_by_id", {"incident_id": incident_id})
            incidents = parse_esql_results(incident_result)
            
            if not incidents:
                return {"success": False, "error": f"Incident {incident_id} not found"}
            
            incident = incidents[0]
            file_path = incident.get("remediation.file_path")
            
            # Get code file
            es = Elasticsearch(
                settings.elasticsearch_url,
                api_key=settings.elasticsearch_api_key
            )
            
            code_result = es.search(
                index="code-repository",
                body={"query": {"term": {"file_path": file_path}}}
            )
            
            if not code_result["hits"]["hits"]:
                return {"success": False, "error": f"Code file {file_path} not found"}
            
            code_file = code_result["hits"]["hits"][0]["_source"]
            
            # Generate fix and create PR
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Generate fix
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
                
                # Create PR
                pr_response = await client.post(
                    "http://localhost:8001/api/elasticseer/create_pr",
                    json={
                        "title": f"[ElasticSeer] Fix: {incident.get('description')} ({incident_id})",
                        "description": f"## 🤖 Autonomous Fix\n\n**Incident**: {incident_id}\n**Severity**: {incident.get('severity')}\n\n### Root Cause\n{incident.get('diagnosis.root_cause')}\n\n### Fix\n{fix_data['explanation']}",
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
                    "incident_id": incident_id
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


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with ElasticSeer - Full Agent Experience
    
    Combines:
    1. Claude Sonnet 3.7 for agentic intelligence
    2. MCP server tools for ES|QL queries
    3. External action endpoints (GitHub, Slack, Jira)
    """
    
    try:
        # Build conversation history for Claude
        messages = []
        
        # Add conversation history (last 10 messages)
        for msg in request.conversation_history[-10:]:
            messages.append({
                "role": "user" if msg.role == "user" else "assistant",
                "content": msg.content
            })
        
        # Add current message
        messages.append({
            "role": "user",
            "content": request.message
        })
        
        # System prompt
        system_prompt = """You are ElasticSeer, an autonomous incident response agent for production infrastructure.

Your capabilities:
- Query Elasticsearch for incidents, metrics, anomalies, and code via MCP tools
- Create GitHub PRs with AI-generated code fixes
- Send Slack notifications to the war room
- Create Jira tickets for incident tracking
- Analyze patterns and provide insights

When users ask about incidents, anomalies, or code, use the appropriate query functions.
When asked to create a PR or fix code, use create_github_pr.
When alerting is needed, use send_slack_alert.
When escalation is needed, use create_jira_ticket.

Be proactive, autonomous, and helpful. Explain your reasoning and actions clearly."""

        # Call Claude via Elastic Inference API
        async with httpx.AsyncClient(timeout=120.0) as client:
            logger.info(f"Calling Claude with message: {request.message}")
            
            response = await client.post(
                f"{settings.kibana_url.rstrip('/')}/api/actions/connector/Anthropic-Claude-Sonnet-3-7/_execute",
                headers={
                    "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
                    "kbn-xsrf": "true",
                    "Content-Type": "application/json"
                },
                json={
                    "params": {
                        "subAction": "invokeAI",
                        "subActionParams": {
                            "messages": messages,
                            "system": system_prompt,
                            "tools": FUNCTION_DEFINITIONS,
                            "temperature": 0.7,
                            "max_tokens": 4096
                        }
                    }
                }
            )
            
            if response.status_code != 200:
                logger.error(f"Claude API error: {response.status_code} - {response.text}")
                raise HTTPException(status_code=500, detail=f"Claude API error: {response.text}")
            
            result = response.json()
            logger.info(f"Claude full response: {json.dumps(result, indent=2)}")
            
            # Extract response
            if "data" not in result:
                logger.error(f"No 'data' field in Claude response: {result}")
                raise HTTPException(status_code=500, detail=f"Invalid response from Claude: {json.dumps(result)[:200]}")
            
            claude_data = result["data"]
            
            # Check if Claude wants to use tools
            tool_calls = []
            response_text = ""
            
            # Parse Claude's response for tool use
            if isinstance(claude_data, dict):
                # Check for content blocks with tool_use
                content = claude_data.get("content", [])
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict):
                            if block.get("type") == "tool_use":
                                tool_calls.append({
                                    "id": block.get("id"),
                                    "name": block.get("name"),
                                    "input": block.get("input", {})
                                })
                            elif block.get("type") == "text":
                                response_text += block.get("text", "")
                
                # Also check top-level for tool_use (different format)
                if claude_data.get("stop_reason") == "tool_use" and not tool_calls:
                    # Try alternative format
                    if "tool_use" in claude_data:
                        tool_use = claude_data["tool_use"]
                        if isinstance(tool_use, dict):
                            tool_calls.append({
                                "id": tool_use.get("id"),
                                "name": tool_use.get("name"),
                                "input": tool_use.get("input", {})
                            })
            
            # Execute tool calls if any
            if tool_calls:
                logger.info(f"Executing {len(tool_calls)} tool calls")
                
                tool_results = []
                for tool_call in tool_calls:
                    function_name = tool_call["name"]
                    arguments = tool_call["input"]
                    
                    logger.info(f"Executing: {function_name} with {arguments}")
                    
                    result = await execute_function(function_name, arguments)
                    tool_results.append({
                        "tool_call_id": tool_call["id"],
                        "function": function_name,
                        "result": result
                    })
                
                # Call Claude again with tool results
                messages.append({
                    "role": "assistant",
                    "content": content
                })
                
                for tool_result in tool_results:
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_result["tool_call_id"],
                            "content": json.dumps(tool_result["result"])
                        }]
                    })
                
                # Second call to Claude with tool results
                response2 = await client.post(
                    f"{settings.kibana_url.rstrip('/')}/api/actions/connector/Anthropic-Claude-Sonnet-3-7/_execute",
                    headers={
                        "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
                        "kbn-xsrf": "true",
                        "Content-Type": "application/json"
                    },
                    json={
                        "params": {
                            "subAction": "invokeAI",
                            "subActionParams": {
                                "messages": messages,
                                "system": system_prompt,
                                "tools": FUNCTION_DEFINITIONS,
                                "temperature": 0.7,
                                "max_tokens": 4096
                            }
                        }
                    }
                )
                
                if response2.status_code == 200:
                    result2 = response2.json()
                    claude_data2 = result2.get("data", {})
                    
                    # Extract final response
                    content2 = claude_data2.get("content", [])
                    if isinstance(content2, list):
                        for block in content2:
                            if isinstance(block, dict) and block.get("type") == "text":
                                response_text = block.get("text", "")
                    elif isinstance(content2, str):
                        response_text = content2
                
                return ChatResponse(
                    response=response_text,
                    sources=["claude-sonnet-3.7", "mcp-server"] + [tr["function"] for tr in tool_results],
                    metadata={"tool_calls": tool_results, "model": "claude-sonnet-3.7"}
                )
            
            # No tool calls, return direct response
            if not response_text and isinstance(claude_data, dict):
                content = claude_data.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            response_text += block.get("text", "")
                elif isinstance(content, str):
                    response_text = content
            
            return ChatResponse(
                response=response_text or "I'm here to help! Ask me about incidents, anomalies, or code issues.",
                sources=["claude-sonnet-3.7"],
                metadata={"model": "claude-sonnet-3.7"}
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
            
            # Test Claude connector
            claude_response = await client.get(
                f"{settings.kibana_url.rstrip('/')}/api/actions/connectors",
                headers={
                    "Authorization": f"ApiKey {settings.elasticsearch_api_key}",
                    "kbn-xsrf": "true"
                }
            )
            
            claude_available = False
            if claude_response.status_code == 200:
                connectors = claude_response.json()
                claude_available = any(c["id"] == "Anthropic-Claude-Sonnet-3-7" for c in connectors)
            
            return {
                "status": "healthy" if (mcp_healthy and claude_available) else "degraded",
                "components": {
                    "mcp_server": "connected" if mcp_healthy else "disconnected",
                    "claude_sonnet": "available" if claude_available else "unavailable",
                    "elasticsearch": "connected",
                    "github": "configured" if settings.github_token else "not configured",
                    "slack": "configured" if settings.slack_bot_token else "not configured",
                    "jira": "configured" if settings.jira_url else "not configured"
                },
                "mcp_tools": len([t for t in tools if t["name"].startswith("elasticseer_")]),
                "total_tools": len(tools),
                "agent": "elasticseer-orchestrator",
                "model": "claude-sonnet-3.7"
            }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }
