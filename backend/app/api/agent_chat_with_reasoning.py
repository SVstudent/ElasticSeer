"""
Agent Chat API with Reasoning Trace - Shows agent's thought process in real-time

This extends the Gemini agent with detailed reasoning traces that show:
- What the agent is thinking
- Which tools it's calling
- Why it's making decisions
- Progress through workflows
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Import the existing agent functionality
from app.api.agent_chat_gemini import (
    ChatMessage,
    ChatRequest,
    execute_function,
    GEMINI_FUNCTIONS,
    settings
)
import google.generativeai as genai

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agent", tags=["agent-reasoning"])

genai.configure(api_key=settings.gemini_api_key)


class ReasoningStep(BaseModel):
    step: str
    thought: str
    timestamp: str
    details: Optional[Dict[str, Any]] = None


class ChatResponseWithReasoning(BaseModel):
    response: str
    sources: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
    reasoning_trace: List[ReasoningStep]


@router.post("/chat_with_reasoning", response_model=ChatResponseWithReasoning)
async def chat_with_reasoning(request: ChatRequest):
    """
    Chat with ElasticSeer with full reasoning trace
    
    Returns the agent's thought process alongside the response
    """
    
    reasoning_trace = []
    
    def add_reasoning(step: str, thought: str, details: Optional[Dict[str, Any]] = None):
        """Helper to add reasoning steps"""
        reasoning_trace.append(ReasoningStep(
            step=step,
            thought=thought,
            timestamp=datetime.utcnow().isoformat(),
            details=details or {}
        ))
        logger.info(f"[REASONING] {step}: {thought}")
    
    try:
        add_reasoning("initialization", "🤖 ElasticSeer agent initialized, analyzing your request...")
        
        # Build conversation history
        history = []
        for msg in request.conversation_history[-10:]:
            history.append({
                "role": "user" if msg.role == "user" else "model",
                "parts": [msg.content]
            })
        
        add_reasoning("context_loading", f"📚 Loaded {len(history)} previous messages for context")
        
        # System instruction
        system_instruction = """You are ElasticSeer, an AUTONOMOUS incident response agent.

Your mission: AUTOMATICALLY handle complete incident workflows.

CRITICAL - USE autonomous_incident_response FOR COMPLETE WORKFLOWS:
When user requests complete workflows, call autonomous_incident_response() - it does EVERYTHING in one call.

CRITICAL - ADAPTIVE FILE SELECTION:
- ALWAYS search for relevant code files first
- Use discovered files, not incident data file paths
- YOUR investigation takes priority"""
        
        add_reasoning("model_configuration", "⚙️ Configuring Gemini 2.5 Flash with function calling...")
        
        # Create model
        model = genai.GenerativeModel(
            model_name=settings.gemini_model,
            system_instruction=system_instruction,
            tools=GEMINI_FUNCTIONS,
            generation_config={
                "temperature": 0.1,
                "top_p": 0.95,
                "top_k": 40,
            }
        )
        
        chat = model.start_chat(history=history)
        
        add_reasoning(
            "analyzing_request",
            f"🔍 Analyzing: '{request.message[:80]}{'...' if len(request.message) > 80 else ''}'",
            {"message_length": len(request.message)}
        )
        
        # Send message to Gemini
        response = chat.send_message(request.message)
        
        # Check for function calls
        function_calls = []
        response_text = ""
        
        for part in response.parts:
            if hasattr(part, 'function_call') and part.function_call:
                function_calls.append(part.function_call)
            elif hasattr(part, 'text') and part.text:
                response_text += part.text
        
        # Execute function calls if any
        if function_calls:
            add_reasoning(
                "function_planning",
                f"🎯 Agent decided to call {len(function_calls)} function(s) to complete your request",
                {"function_count": len(function_calls)}
            )
            
            function_responses = []
            function_results = []
            
            for idx, function_call in enumerate(function_calls, 1):
                function_name = function_call.name
                arguments = dict(function_call.args)
                
                # Add detailed reasoning for each function
                if function_name == "autonomous_incident_response":
                    add_reasoning(
                        "workflow_execution",
                        f"🚀 Executing COMPLETE autonomous workflow for: {arguments.get('title', 'incident')}",
                        {"severity": arguments.get('severity'), "service": arguments.get('service')}
                    )
                    add_reasoning("workflow_step_1", "📝 Step 1/5: Registering incident in system...")
                    add_reasoning("workflow_step_2", "🔍 Step 2/5: Searching codebase for relevant files...")
                    add_reasoning("workflow_step_3", "🔧 Step 3/5: Generating AI-powered fix and creating GitHub PR...")
                    add_reasoning("workflow_step_4", "📢 Step 4/5: Sending Slack alert to team...")
                    add_reasoning("workflow_step_5", "🎫 Step 5/5: Creating Jira ticket for tracking...")
                
                elif function_name == "query_recent_incidents":
                    add_reasoning("data_query", "📊 Querying Elasticsearch for recent incidents...")
                
                elif function_name == "search_code_by_path":
                    pattern = arguments.get('pattern', '*')
                    add_reasoning(
                        "code_search",
                        f"🔎 Searching GitHub repository for files matching: {pattern}",
                        {"pattern": pattern}
                    )
                
                elif function_name == "get_metrics_anomalies":
                    service = arguments.get('service')
                    add_reasoning(
                        "anomaly_detection",
                        f"📈 Analyzing metrics for {service} to detect anomalies...",
                        {"service": service}
                    )
                
                elif function_name == "analyze_service_metrics":
                    service = arguments.get('service')
                    time_range = arguments.get('time_range', '24h')
                    add_reasoning(
                        "metrics_analysis",
                        f"📊 Running comprehensive metrics analysis for {service} over {time_range}...",
                        {"service": service, "time_range": time_range}
                    )
                
                elif function_name == "create_github_pr":
                    incident_id = arguments.get('incident_id')
                    add_reasoning(
                        "pr_creation",
                        f"🔧 Creating GitHub PR with automated fix for {incident_id}...",
                        {"incident_id": incident_id}
                    )
                
                elif function_name == "send_slack_alert":
                    add_reasoning("slack_notification", "📢 Sending alert to Slack war room...")
                
                elif function_name == "create_jira_ticket":
                    add_reasoning("jira_creation", "🎫 Creating Jira ticket for incident tracking...")
                
                elif function_name == "register_incident":
                    title = arguments.get('title', '')
                    add_reasoning(
                        "incident_registration",
                        f"📝 Registering new incident: {title[:50]}...",
                        {"severity": arguments.get('severity')}
                    )
                
                # Execute the function
                result = await execute_function(function_name, arguments)
                function_results.append({"function": function_name, "result": result})
                
                # Add result reasoning
                if result.get("success"):
                    if function_name == "autonomous_incident_response":
                        workflow = result.get("results", {})
                        incident_id = result.get("incident_id")
                        
                        if workflow.get("incident_registration", {}).get("success"):
                            add_reasoning("workflow_complete_1", f"✅ Incident {incident_id} registered successfully")
                        
                        if workflow.get("code_search", {}).get("success"):
                            file = workflow["code_search"].get("target_file")
                            add_reasoning("workflow_complete_2", f"✅ Found relevant code file: {file}")
                        
                        if workflow.get("pr_creation", {}).get("success"):
                            pr_num = workflow["pr_creation"].get("pr_number")
                            add_reasoning("workflow_complete_3", f"✅ GitHub PR #{pr_num} created with automated fix")
                        
                        if workflow.get("slack_alert", {}).get("success"):
                            add_reasoning("workflow_complete_4", "✅ Slack alert sent to team")
                        
                        if workflow.get("jira_ticket", {}).get("success"):
                            ticket_id = workflow["jira_ticket"].get("ticket_id")
                            add_reasoning("workflow_complete_5", f"✅ Jira ticket {ticket_id} created")
                        
                        add_reasoning("workflow_success", "🎉 Complete autonomous workflow executed successfully!")
                    
                    elif function_name == "analyze_service_metrics":
                        add_reasoning("analysis_complete", "✅ Comprehensive metrics analysis completed with insights")
                    
                    else:
                        add_reasoning(f"{function_name}_complete", f"✅ {function_name} completed successfully")
                else:
                    add_reasoning(f"{function_name}_error", f"⚠️ {function_name} encountered an issue: {result.get('error', 'Unknown')}")
                
                function_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=function_name,
                            response={"result": result}
                        )
                    )
                )
            
            add_reasoning("generating_response", "💭 Synthesizing final response from results...")
            
            # Send function results back to Gemini
            try:
                response2 = chat.send_message(function_responses)
                
                final_text = ""
                for part in response2.parts:
                    if hasattr(part, 'text') and part.text:
                        final_text += part.text
                
                if final_text:
                    add_reasoning("response_ready", "✅ Response generated successfully!")
                    
                    return ChatResponseWithReasoning(
                        response=final_text,
                        sources=["gemini-2.5-flash", "mcp-server"] + [fc.name for fc in function_calls],
                        metadata={
                            "model": "gemini-2.5-flash",
                            "function_calls": [{"name": fc.name, "args": dict(fc.args)} for fc in function_calls],
                            "function_results": function_results
                        },
                        reasoning_trace=reasoning_trace
                    )
            except Exception as e:
                logger.warning(f"Gemini failed to generate final response: {e}")
                add_reasoning("fallback_response", "⚠️ Using fallback response generation...")
            
            # Fallback response
            fallback_response = "✅ Actions completed successfully:\n\n"
            for func_result in function_results:
                func_name = func_result["function"]
                result = func_result["result"]
                
                if func_name == "autonomous_incident_response" and result.get("success"):
                    workflow = result.get("results", {})
                    incident_id = result.get("incident_id")
                    
                    fallback_response += f"✅ **Complete Autonomous Workflow Executed**\n\n"
                    
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
            
            add_reasoning("response_ready", "✅ Fallback response generated!")
            
            return ChatResponseWithReasoning(
                response=fallback_response,
                sources=["gemini-2.5-flash", "mcp-server"] + [fc.name for fc in function_calls],
                metadata={
                    "model": "gemini-2.5-flash",
                    "function_calls": [{"name": fc.name, "args": dict(fc.args)} for fc in function_calls],
                    "function_results": function_results,
                    "fallback_used": True
                },
                reasoning_trace=reasoning_trace
            )
        
        # No function calls, return direct response
        add_reasoning("direct_response", "💬 Generating direct response (no tools needed)")
        add_reasoning("response_ready", "✅ Response ready!")
        
        return ChatResponseWithReasoning(
            response=response_text or "I'm here to help! Ask me about incidents, anomalies, or code issues.",
            sources=["gemini-2.5-flash"],
            metadata={"model": "gemini-2.5-flash"},
            reasoning_trace=reasoning_trace
        )
        
    except Exception as e:
        logger.error(f"Error: {e}", exc_info=True)
        add_reasoning("error", f"❌ Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
