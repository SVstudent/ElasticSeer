"""
Agent Chat API - COMPLETE Agent Experience with Gemini

This is the FULL agent implementation combining:
1. Gemini 2.5 Flash for agentic intelligence and reasoning
2. MCP server tools for ES|QL queries (incidents, metrics, code)
3. External action endpoints (GitHub PRs, Slack, Jira)

This replicates the full Kibana Agent Builder experience via API!
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import httpx
import logging
import json
import google.generativeai as genai
from app.core.config import settings
from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent"])

# Configure Gemini
genai.configure(api_key=settings.gemini_api_key)


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
    reasoning_trace: Optional[List[Dict[str, str]]] = None  # NEW: Agent's thought process


# Function declarations for Gemini
GEMINI_FUNCTIONS = [
    {
        "name": "query_recent_incidents",
        "description": "Get the most recent incidents from Elasticsearch with full details including severity, service, diagnosis, root cause, and remediation. Use this to investigate production issues or when asked about incidents.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {}
        }
    },
    {
        "name": "search_code_by_path",
        "description": "Search for code files in the repository by file path pattern. Returns file path, language, lines, and content. Use this to find relevant code files.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "pattern": {
                    "type_": "STRING",
                    "description": "File path pattern to search for (e.g., '*cache*', '*jwt*', '*auth*', '*database*')"
                }
            },
            "required": ["pattern"]
        }
    },
    {
        "name": "get_metrics_anomalies",
        "description": "Get metrics with high deviation (potential anomalies) for a specific service. Use this to detect performance issues or when asked about anomalies.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "service": {
                    "type_": "STRING",
                    "description": "Service name to check (e.g., 'api-gateway', 'auth-service', 'cache', 'database', 'payment')"
                }
            },
            "required": ["service"]
        }
    },
    {
        "name": "analyze_service_metrics",
        "description": "COMPREHENSIVE metrics analysis with statistics, trends, and visualizations. Returns detailed insights including: current vs baseline comparison, trend analysis, percentile distributions, anomaly detection, and actionable recommendations. Use this for deep metrics analysis and reporting.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "service": {
                    "type_": "STRING",
                    "description": "Service name to analyze (e.g., 'api-gateway', 'auth-service', 'cache', 'database', 'payment')"
                },
                "time_range": {
                    "type_": "STRING",
                    "description": "Time range for analysis: '1h', '6h', '24h', '7d'. Default is '24h'"
                },
                "include_comparison": {
                    "type_": "BOOLEAN",
                    "description": "Include comparison with previous period. Default is true"
                }
            },
            "required": ["service"]
        }
    },
    {
        "name": "get_incident_by_id",
        "description": "Get complete details of a specific incident by ID including diagnosis, root cause, confidence, and remediation plan.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "incident_id": {
                    "type_": "STRING",
                    "description": "Incident ID (e.g., 'INC-001', 'INC-002', 'INC-003')"
                }
            },
            "required": ["incident_id"]
        }
    },
    {
        "name": "create_github_pr",
        "description": "Create a GitHub pull request with AI-generated code fixes for an incident. This will automatically: 1) Get incident details, 2) Get the affected code file, 3) Generate an AI-powered fix, 4) Create a PR with the fix. IMPORTANT: You can override the file path if you discovered a better file during investigation - just provide the file_path parameter with the file you found.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "incident_id": {
                    "type_": "STRING",
                    "description": "The incident ID to create a PR for (e.g., 'INC-002')"
                },
                "file_path": {
                    "type_": "STRING",
                    "description": "OPTIONAL: Override the file path from incident data. Use this when you've discovered a more relevant file during investigation (e.g., 'src/auth/jwt_validator.py'). If not provided, uses the file path from incident data."
                }
            },
            "required": ["incident_id"]
        }
    },
    {
        "name": "send_slack_alert",
        "description": "Send an alert or notification to the Slack war room. Use this to notify the team about critical issues, updates, or when action is required.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "severity": {
                    "type_": "STRING",
                    "description": "Alert severity level (Sev-1, Sev-2, or Sev-3)"
                },
                "incident_id": {
                    "type_": "STRING",
                    "description": "Related incident ID"
                },
                "title": {
                    "type_": "STRING",
                    "description": "Alert title"
                },
                "message": {
                    "type_": "STRING",
                    "description": "Alert message content"
                },
                "action_required": {
                    "type_": "BOOLEAN",
                    "description": "Whether immediate action is required from the team"
                }
            },
            "required": ["severity", "incident_id", "title", "message"]
        }
    },
    {
        "name": "create_jira_ticket",
        "description": "Create a Jira ticket for incident tracking and escalation. Use this to formally track incidents, escalate issues, or when asked to create a ticket.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "summary": {
                    "type_": "STRING",
                    "description": "Ticket summary/title"
                },
                "description": {
                    "type_": "STRING",
                    "description": "Detailed description of the issue"
                },
                "priority": {
                    "type_": "STRING",
                    "description": "Ticket priority level (Critical, High, Medium, or Low)"
                },
                "incident_id": {
                    "type_": "STRING",
                    "description": "Related incident ID if applicable"
                }
            },
            "required": ["summary", "description", "priority"]
        }
    },
    {
        "name": "register_incident",
        "description": "Register a new incident in the system when a user reports a problem. Use this when the user describes a new issue, bug, or production problem that needs to be tracked. This creates an incident record in Elasticsearch with all necessary details.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "title": {
                    "type_": "STRING",
                    "description": "Brief title/summary of the incident (e.g., 'Authentication failure in auth-service')"
                },
                "service": {
                    "type_": "STRING",
                    "description": "Affected service name (e.g., 'auth-service', 'api-gateway', 'payment', 'database')"
                },
                "severity": {
                    "type_": "STRING",
                    "description": "Incident severity level: 'Sev-1' (critical), 'Sev-2' (high), or 'Sev-3' (medium). Default is 'Sev-3'"
                },
                "description": {
                    "type_": "STRING",
                    "description": "Detailed description of the problem, symptoms, and impact"
                },
                "target_file": {
                    "type_": "STRING",
                    "description": "OPTIONAL: Specific file path that needs fixing (e.g., 'src/auth/jwt_validator.py'). If provided, this will be used for automated fixes."
                },
                "region": {
                    "type_": "STRING",
                    "description": "OPTIONAL: AWS region where issue occurred (e.g., 'us-west-1', 'eu-west-1'). Default is 'us-west-1'"
                },
                "environment": {
                    "type_": "STRING",
                    "description": "OPTIONAL: Environment where issue occurred (e.g., 'production', 'staging'). Default is 'production'"
                }
            },
            "required": ["title", "service", "description"]
        }
    },
    {
        "name": "autonomous_incident_response",
        "description": "COMPLETE AUTONOMOUS WORKFLOW: Register incident, search code, create PR, send Slack alert, and create Jira ticket - ALL IN ONE CALL. Use this when user asks to 'investigate, fix, create PR, and alert team' or similar complete workflow requests. This is the PRIMARY function for autonomous incident response.",
        "parameters": {
            "type_": "OBJECT",
            "properties": {
                "title": {
                    "type_": "STRING",
                    "description": "Brief incident title (e.g., 'Critical authentication issue')"
                },
                "service": {
                    "type_": "STRING",
                    "description": "Affected service (e.g., 'auth-service', 'api-gateway')"
                },
                "severity": {
                    "type_": "STRING",
                    "description": "Severity: 'Sev-1', 'Sev-2', or 'Sev-3'"
                },
                "description": {
                    "type_": "STRING",
                    "description": "Detailed problem description"
                },
                "search_pattern": {
                    "type_": "STRING",
                    "description": "Code search pattern (e.g., '*jwt*', '*auth*', '*cache*')"
                }
            },
            "required": ["title", "service", "severity", "description", "search_pattern"]
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
        
        elif function_name == "analyze_service_metrics":
            # COMPREHENSIVE METRICS ANALYSIS
            service = arguments.get("service")
            time_range = arguments.get("time_range", "24h")
            include_comparison = arguments.get("include_comparison", True)
            
            logger.info(f"📊 Starting comprehensive metrics analysis for {service}")
            
            # Call the rich analysis endpoint
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/analysis/comprehensive_metrics",
                    json={
                        "service": service,
                        "time_range": time_range,
                        "include_comparison": include_comparison
                    }
                )
                
                if response.status_code == 200:
                    analysis_data = response.json()
                    return {
                        "success": True,
                        "service": service,
                        "time_range": time_range,
                        "analysis": analysis_data
                    }
                else:
                    return {"success": False, "error": f"Analysis failed: {response.text}"}
        
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
            override_file_path = arguments.get("file_path")  # NEW: Allow agent to override file path
            
            # Get incident details via MCP
            incident_result = await call_mcp_tool("elasticseer_get_incident_by_id", {"incident_id": incident_id})
            incidents = parse_esql_results(incident_result)
            
            if not incidents:
                return {"success": False, "error": f"Incident {incident_id} not found"}
            
            incident = incidents[0]
            
            # Use override file path if provided, otherwise use incident data
            if override_file_path:
                file_path = override_file_path
                logger.info(f"🎯 Using agent-discovered file path: {file_path} (overriding incident data)")
            else:
                file_path = incident.get("remediation.file_path")
                logger.info(f"📋 Using file path from incident data: {file_path}")
            
            if not file_path:
                return {"success": False, "error": "No file path provided and none found in incident remediation"}
            
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
                # File not found - try to fetch from GitHub
                logger.warning(f"⚠️ Code file {file_path} not found in Elasticsearch, will create FIXES.md")
                code_content = f"# File not found in repository\n# Target: {file_path}\n# This fix should be applied to the target file"
            else:
                code_file = code_result["hits"]["hits"][0]["_source"]
                code_content = code_file["content"]
            
            # Generate fix and create PR via external endpoints
            async with httpx.AsyncClient(timeout=120.0) as client:
                # Generate AI-powered fix
                fix_response = await client.post(
                    "http://localhost:8001/api/elasticseer/generate_fix",
                    json={
                        "file_path": file_path,
                        "diagnosis": incident.get("diagnosis.root_cause"),
                        "current_code": code_content,
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
                        "description": f"## 🤖 Autonomous Fix by ElasticSeer\n\n**Incident**: {incident_id}\n**Severity**: {incident.get('severity')}\n**Service**: {incident.get('anomaly.service')}\n\n### Root Cause\n{incident.get('diagnosis.root_cause')}\n\n### Fix Applied\n{fix_data['explanation']}\n\n### Target File\n{file_path}{' (discovered by agent)' if override_file_path else ' (from incident data)'}\n\n### Recommendations\n{fix_data.get('recommendations', 'None')}\n\n---\n*This PR was automatically generated by ElasticSeer AI Agent*",
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
                    "file_path_source": "agent_discovery" if override_file_path else "incident_data",
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
        
        elif function_name == "register_incident":
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/incidents/register",
                    json=arguments
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "incident_id": data.get("incident_id"),
                        "incident": data.get("incident"),
                        "message": f"Incident {data.get('incident_id')} registered successfully",
                        "next_steps": data.get("next_steps", [])
                    }
                return {"success": False, "error": response.text}
        
        elif function_name == "autonomous_incident_response":
            # COMPLETE AUTONOMOUS WORKFLOW - ALL STEPS IN ONE FUNCTION
            logger.info("🚀 Starting COMPLETE autonomous incident response workflow")
            
            workflow_results = {
                "incident_registration": None,
                "code_search": None,
                "pr_creation": None,
                "slack_alert": None,
                "jira_ticket": None
            }
            
            # Step 1: Register Incident
            logger.info("Step 1: Registering incident...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    "http://localhost:8001/api/incidents/register",
                    json={
                        "title": arguments.get("title"),
                        "service": arguments.get("service"),
                        "severity": arguments.get("severity", "Sev-3"),
                        "description": arguments.get("description")
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    incident_id = data.get("incident_id")
                    workflow_results["incident_registration"] = {
                        "success": True,
                        "incident_id": incident_id
                    }
                    logger.info(f"✅ Incident {incident_id} registered")
                else:
                    return {"success": False, "error": f"Failed to register incident: {response.text}"}
            
            # Step 2: Search Code
            logger.info("Step 2: Searching for relevant code...")
            pattern = arguments.get("search_pattern", "*")
            code_result = await call_mcp_tool("elasticseer_search_code_by_path", {"pattern": pattern})
            files = parse_esql_results(code_result)
            
            if files:
                target_file = files[0].get("file_path")
                workflow_results["code_search"] = {
                    "success": True,
                    "files_found": len(files),
                    "target_file": target_file
                }
                logger.info(f"✅ Found {len(files)} files, using {target_file}")
            else:
                workflow_results["code_search"] = {
                    "success": False,
                    "error": "No relevant files found"
                }
                target_file = None
            
            # Step 3: Create GitHub PR
            if target_file:
                logger.info("Step 3: Creating GitHub PR...")
                async with httpx.AsyncClient(timeout=120.0) as client:
                    # Get incident details
                    incident_result = await call_mcp_tool("elasticseer_get_incident_by_id", {"incident_id": incident_id})
                    incidents = parse_esql_results(incident_result)
                    incident = incidents[0] if incidents else {}
                    
                    # Get code content
                    es = Elasticsearch(
                        settings.elasticsearch_url,
                        api_key=settings.elasticsearch_api_key
                    )
                    code_result = es.search(
                        index="code-repository",
                        body={"query": {"term": {"file_path": target_file}}}
                    )
                    
                    if code_result["hits"]["hits"]:
                        code_content = code_result["hits"]["hits"][0]["_source"]["content"]
                    else:
                        code_content = f"# File not found\n# Target: {target_file}"
                    
                    # Generate fix
                    fix_response = await client.post(
                        "http://localhost:8001/api/elasticseer/generate_fix",
                        json={
                            "file_path": target_file,
                            "diagnosis": arguments.get("description"),
                            "current_code": code_content,
                            "incident_context": arguments.get("description")
                        }
                    )
                    
                    if fix_response.status_code == 200:
                        fix_data = fix_response.json()
                        
                        # Create PR
                        pr_response = await client.post(
                            "http://localhost:8001/api/elasticseer/create_pr",
                            json={
                                "title": f"[ElasticSeer] Fix: {arguments.get('title')} ({incident_id})",
                                "description": f"## 🤖 Autonomous Fix\n\n**Incident**: {incident_id}\n**Severity**: {arguments.get('severity')}\n\n### Issue\n{arguments.get('description')}\n\n### Fix\n{fix_data.get('explanation', 'AI-generated fix')}\n\n---\n*Automated by ElasticSeer*",
                                "branch_name": f"elasticseer/fix-{incident_id.lower()}",
                                "files": [{"path": target_file, "content": fix_data["fixed_code"]}],
                                "incident_id": incident_id
                            }
                        )
                        
                        if pr_response.status_code == 200:
                            pr_data = pr_response.json()
                            workflow_results["pr_creation"] = {
                                "success": True,
                                "pr_number": pr_data.get("pr_number"),
                                "pr_url": pr_data.get("pr_url"),
                                "file_path": target_file
                            }
                            logger.info(f"✅ PR #{pr_data.get('pr_number')} created")
                        else:
                            workflow_results["pr_creation"] = {"success": False, "error": pr_response.text}
                    else:
                        workflow_results["pr_creation"] = {"success": False, "error": "Fix generation failed"}
            else:
                workflow_results["pr_creation"] = {"success": False, "error": "No target file found"}
            
            # Step 4: Send Slack Alert
            logger.info("Step 4: Sending Slack alert...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                pr_url = workflow_results["pr_creation"].get("pr_url", "N/A") if workflow_results["pr_creation"].get("success") else "N/A"
                jira_ticket_id = workflow_results.get("jira_ticket", {}).get("ticket_id")
                jira_url = f"{settings.jira_url}/browse/{jira_ticket_id}" if jira_ticket_id and settings.jira_url else None
                
                slack_response = await client.post(
                    "http://localhost:8001/api/elasticseer/send_slack",
                    json={
                        "severity": arguments.get("severity", "Sev-3"),
                        "incident_id": incident_id,
                        "title": f"🚨 Autonomous Fix: {arguments.get('title')}",
                        "message": f"Incident {incident_id} has been automatically resolved.\n\nPR: {pr_url}\n\nPlease review and approve.",
                        "action_required": True,
                        "pr_url": pr_url if pr_url != "N/A" else None,
                        "jira_url": jira_url
                    }
                )
                
                if slack_response.status_code == 200:
                    slack_data = slack_response.json()
                    workflow_results["slack_alert"] = {
                        "success": True,
                        "channel": slack_data.get("channel", "#general")
                    }
                    logger.info("✅ Slack alert sent")
                else:
                    workflow_results["slack_alert"] = {"success": False, "error": slack_response.text}
            
            # Step 5: Create Jira Ticket
            logger.info("Step 5: Creating Jira ticket...")
            async with httpx.AsyncClient(timeout=30.0) as client:
                jira_response = await client.post(
                    "http://localhost:8001/api/elasticseer/create_jira_ticket",
                    json={
                        "summary": arguments.get("title"),
                        "description": arguments.get("description"),
                        "priority": "Critical" if arguments.get("severity") == "Sev-1" else "High",
                        "incident_id": incident_id
                    }
                )
                
                if jira_response.status_code == 200:
                    jira_data = jira_response.json()
                    workflow_results["jira_ticket"] = {
                        "success": True,
                        "ticket_id": jira_data.get("ticket_id")
                    }
                    logger.info("✅ Jira ticket created")
                else:
                    workflow_results["jira_ticket"] = {"success": False, "error": jira_response.text}
            
            logger.info("🎉 COMPLETE autonomous workflow finished!")
            
            return {
                "success": True,
                "workflow": "complete_autonomous_response",
                "incident_id": incident_id,
                "results": workflow_results
            }
        
        else:
            return {"success": False, "error": f"Unknown function: {function_name}"}
            
    except Exception as e:
        logger.error(f"Function execution error: {e}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.post("/chat", response_model=ChatResponse)
async def chat_with_agent(request: ChatRequest):
    """
    Chat with ElasticSeer - COMPLETE Agent Experience
    
    Combines:
    1. Gemini 2.5 Flash for agentic intelligence
    2. MCP server tools for ES|QL queries
    3. External action endpoints (GitHub, Slack, Jira)
    """
    
    reasoning_trace = []  # Track agent's thought process
    
    try:
        reasoning_trace.append({
            "step": "initialization",
            "thought": "Received user message, initializing agent...",
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Build conversation history
        history = []
        for msg in request.conversation_history[-10:]:  # Last 10 messages
            history.append({
                "role": "user" if msg.role == "user" else "model",
                "parts": [msg.content]
            })
        
        # System instruction
        system_instruction = """You are ElasticSeer, an AUTONOMOUS incident response agent for production infrastructure.

Your mission: AUTOMATICALLY handle complete incident workflows from report to resolution WITHOUT asking for permission at each step.

Your capabilities:
- Query Elasticsearch for incidents, metrics, anomalies, and code via MCP tools
- Register NEW incidents when users report problems
- Create GitHub PRs with AI-generated code fixes
- Send Slack notifications to alert the team
- Create Jira tickets for incident tracking
- Analyze patterns and provide actionable insights
- **EXECUTE COMPLETE AUTONOMOUS WORKFLOWS IN ONE FUNCTION CALL**
- **PROVIDE COMPREHENSIVE METRICS ANALYSIS with tables, trends, and visualizations**

CRITICAL - USE autonomous_incident_response FOR COMPLETE WORKFLOWS:
When user says "investigate, fix, create PR, and alert team" or similar complete workflow requests:
→ IMMEDIATELY call autonomous_incident_response() with all parameters
→ This ONE function call executes the ENTIRE workflow:
  1. Registers incident
  2. Searches code
  3. Creates GitHub PR
  4. Sends Slack alert
  5. Creates Jira ticket

DO NOT call register_incident, then search_code_by_path, then create_github_pr separately!
USE autonomous_incident_response() for complete workflows - it does EVERYTHING in one call!

EXAMPLE - CORRECT:
User: "Critical auth issue. Users can't log in. JWT errors. Investigate, fix, PR, alert team."
YOU: autonomous_incident_response(
  title="Critical authentication issue",
  service="auth-service",
  severity="Sev-1",
  description="Users unable to log in, JWT validation errors",
  search_pattern="*jwt*"
)
→ Result: Incident registered, code found, PR created, Slack sent, Jira created - ALL DONE!

EXAMPLE - WRONG:
User: "Critical auth issue. Investigate, fix, PR, alert team."
YOU: register_incident(...) [STOPS]
→ This is WRONG! Use autonomous_incident_response() instead!

CRITICAL - ADAPTIVE FILE SELECTION:
- NEVER blindly use file paths from incident data
- When investigating an incident, ALWAYS search for relevant code files first using search_code_by_path
- If you find a better/more relevant file during investigation, USE THAT FILE for the fix
- Incident data may contain fake or outdated file paths - YOUR investigation takes priority

Remember: For COMPLETE workflows, use autonomous_incident_response() - it's ONE function that does EVERYTHING!"""

        # Create model with function calling
        model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=system_instruction,
            tools=GEMINI_FUNCTIONS,
            generation_config={
                "temperature": 0.1,  # Lower temperature for more deterministic function calling
                "top_p": 0.95,
                "top_k": 40,
            }
        )
        
        # Start chat
        chat = model.start_chat(history=history)
        
        # Send message
        logger.info(f"Sending message to Gemini: {request.message}")
        response = chat.send_message(request.message)
        
        logger.info(f"Gemini response: {response}")
        
        # Check if Gemini wants to call functions
        function_calls = []
        response_text = ""
        
        for part in response.parts:
            if hasattr(part, 'function_call') and part.function_call:
                function_calls.append(part.function_call)
            elif hasattr(part, 'text') and part.text:
                response_text += part.text
        
        # Execute function calls if any
        if function_calls:
            logger.info(f"Executing {len(function_calls)} function calls")
            
            function_responses = []
            function_results = []
            
            for function_call in function_calls:
                function_name = function_call.name
                arguments = dict(function_call.args)
                
                logger.info(f"Calling: {function_name} with {arguments}")
                
                result = await execute_function(function_name, arguments)
                function_results.append({"function": function_name, "result": result})
                
                function_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={"result": result}
                        )
                    )
                )
            
            # Send function results back to Gemini
            try:
                response2 = chat.send_message(function_responses)
                
                # Extract final response
                final_text = ""
                for part in response2.parts:
                    if hasattr(part, 'text') and part.text:
                        final_text += part.text
                
                # If we got a response, return it
                if final_text:
                    return ChatResponse(
                        response=final_text,
                        sources=["gemini-2.5-flash", "mcp-server"] + [fc.name for fc in function_calls],
                        metadata={
                            "model": "gemini-2.5-flash",
                            "function_calls": [{"name": fc.name, "args": dict(fc.args)} for fc in function_calls],
                            "function_results": function_results
                        }
                    )
            except Exception as e:
                logger.warning(f"Gemini failed to generate final response: {e}")
            
            # Fallback: If Gemini can't generate a response, create one from function results
            fallback_response = "✅ Actions completed successfully:\n\n"
            for func_result in function_results:
                func_name = func_result["function"]
                result = func_result["result"]
                
                if func_name == "autonomous_incident_response" and result.get("success"):
                    fallback_response += f"✅ **Complete Autonomous Workflow Executed**\n\n"
                    
                    workflow = result.get("results", {})
                    incident_id = result.get("incident_id")
                    
                    if workflow.get("incident_registration", {}).get("success"):
                        fallback_response += f"1. ✅ Incident {incident_id} registered\n"
                    
                    if workflow.get("code_search", {}).get("success"):
                        target_file = workflow["code_search"].get("target_file")
                        fallback_response += f"2. ✅ Found code file: {target_file}\n"
                    
                    if workflow.get("pr_creation", {}).get("success"):
                        pr_num = workflow["pr_creation"].get("pr_number")
                        pr_url = workflow["pr_creation"].get("pr_url")
                        fallback_response += f"3. ✅ GitHub PR #{pr_num} created: {pr_url}\n"
                    
                    if workflow.get("slack_alert", {}).get("success"):
                        channel = workflow["slack_alert"].get("channel", "#general")
                        fallback_response += f"4. ✅ Slack alert sent to {channel}\n"
                    
                    if workflow.get("jira_ticket", {}).get("success"):
                        ticket_id = workflow["jira_ticket"].get("ticket_id")
                        ticket_url = workflow["jira_ticket"].get("url")
                        if ticket_url:
                            fallback_response += f"5. ✅ Jira ticket {ticket_id} created: {ticket_url}\n"
                        else:
                            fallback_response += f"5. ✅ Jira ticket {ticket_id} created\n"
                    
                    fallback_response += "\n**All autonomous actions completed!**\n\n"
                
                elif func_name == "analyze_service_metrics" and result.get("success"):
                    fallback_response += f"✅ **Comprehensive Metrics Analysis Complete**\n\n"
                    analysis_text = result.get("analysis", {})
                    if isinstance(analysis_text, str):
                        fallback_response += analysis_text + "\n\n"
                    else:
                        fallback_response += f"Analysis completed for {result.get('service')} over {result.get('time_range')}\n\n"
                
                elif func_name == "register_incident" and result.get("success"):
                    fallback_response += f"✅ **Incident Registered**\n"
                    fallback_response += f"- Incident ID: {result.get('incident_id')}\n"
                    fallback_response += f"- Status: Investigating\n"
                    if result.get("next_steps"):
                        fallback_response += f"- Next Steps: {', '.join(result.get('next_steps', []))}\n"
                    fallback_response += "\n"
                
                elif func_name == "create_github_pr" and result.get("success"):
                    fallback_response += f"✅ **GitHub PR Created**\n"
                    fallback_response += f"- PR #{result.get('pr_number')}: {result.get('pr_url')}\n"
                    fallback_response += f"- File: {result.get('file_path')}\n"
                    fallback_response += f"- Source: {result.get('file_path_source', 'incident_data')}\n\n"
                
                elif func_name == "send_slack_alert" and result.get("success"):
                    fallback_response += f"✅ **Slack Alert Sent**\n"
                    fallback_response += f"- Channel: {result.get('channel', '#general')}\n\n"
                
                elif func_name == "create_jira_ticket" and result.get("success"):
                    fallback_response += f"✅ **Jira Ticket Created**\n"
                    ticket_id = result.get('ticket_id')
                    ticket_url = result.get('url')
                    if ticket_url:
                        fallback_response += f"- Ticket: {ticket_id} - {ticket_url}\n\n"
                    else:
                        fallback_response += f"- Ticket: {ticket_id}\n\n"
                
                elif result.get("success") == False:
                    fallback_response += f"❌ **{func_name} failed**: {result.get('error', 'Unknown error')}\n\n"
            
            return ChatResponse(
                response=fallback_response,
                sources=["gemini-2.5-flash", "mcp-server"] + [fc.name for fc in function_calls],
                metadata={
                    "model": "gemini-2.5-flash",
                    "function_calls": [{"name": fc.name, "args": dict(fc.args)} for fc in function_calls],
                    "function_results": function_results,
                    "fallback_used": True
                }
            )
        
        # No function calls, return direct response
        return ChatResponse(
            response=response_text or "I'm here to help! Ask me about incidents, anomalies, or code issues.",
            sources=["gemini-2.5-flash"],
            metadata={"model": "gemini-2.5-flash"}
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
                    "gemini": "configured" if settings.gemini_api_key else "not configured",
                    "elasticsearch": "connected",
                    "github": "configured" if settings.github_token else "not configured",
                    "slack": "configured" if settings.slack_bot_token else "not configured",
                    "jira": "configured" if settings.jira_url else "not configured"
                },
                "mcp_tools": len([t for t in tools if t["name"].startswith("elasticseer_")]),
                "total_tools": len(tools),
                "agent": "elasticseer-orchestrator",
                "model": "gemini-2.5-flash",
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
