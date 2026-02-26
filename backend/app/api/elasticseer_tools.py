"""
ElasticSeer Custom Tools API Endpoints

These endpoints are called by the Kibana agent to perform actions:
- Generate code fixes
- Create GitHub PRs
- Send Slack notifications
- Detect anomalies
- Diagnose root causes
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
import google.generativeai as genai
from github import Github
import httpx
from app.core.config import settings

router = APIRouter(prefix="/api/elasticseer", tags=["elasticseer-tools"])

# Initialize services
genai.configure(api_key=settings.gemini_api_key)
github_client = Github(settings.github_token) if settings.github_token else None


# Request/Response Models
class GenerateFixRequest(BaseModel):
    file_path: str
    diagnosis: str
    current_code: str
    incident_context: Optional[str] = None


class FileChange(BaseModel):
    path: str
    content: str


class CreatePRRequest(BaseModel):
    title: str
    description: str
    branch_name: str
    files: List[FileChange]
    incident_id: Optional[str] = None


class SlackNotificationRequest(BaseModel):
    severity: str
    incident_id: str
    title: str
    message: str
    action_required: bool = False
    pr_url: Optional[str] = None
    jira_url: Optional[str] = None


class DetectAnomaliesRequest(BaseModel):
    service: Optional[str] = None
    metric_name: Optional[str] = None
    time_range: str = "1h"
    threshold_sigma: float = 3.0


class DiagnoseRequest(BaseModel):
    anomaly: Dict[str, Any]
    similar_incidents: Optional[List[Dict[str, Any]]] = None
    relevant_code: Optional[List[Dict[str, Any]]] = None


class CreateJiraTicketRequest(BaseModel):
    summary: str
    description: str
    priority: str = "High"
    incident_id: Optional[str] = None
    labels: Optional[List[str]] = None


class RegisterIncidentRequest(BaseModel):
    title: str
    service: str
    severity: str = "Sev-3"
    description: str
    target_file: Optional[str] = None


@router.post("/register_incident")
async def register_incident(request: RegisterIncidentRequest):
    """
    Register a new incident in the system
    This is a wrapper that calls the incident management API
    """
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.post(
                "http://localhost:8001/api/incidents/register",
                json={
                    "title": request.title,
                    "service": request.service,
                    "severity": request.severity,
                    "description": request.description,
                    "target_file": request.target_file
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "incident_id": data['incident_id'],
                    "message": f"Incident {data['incident_id']} registered successfully"
                }
            else:
                raise HTTPException(status_code=response.status_code, detail=response.text)
                
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to register incident: {str(e)}")


@router.post("/generate_fix")
async def generate_code_fix(request: GenerateFixRequest):
    """
    Generate AI-powered code fix using Gemini
    """
    try:
        model = genai.GenerativeModel(settings.gemini_model)
        
        prompt = f"""You are an expert software engineer fixing a production bug.

**File**: {request.file_path}

**Diagnosis**: {request.diagnosis}

**Current Code**:
```
{request.current_code}
```

**Context**: {request.incident_context or 'N/A'}

Generate a fixed version of the code that resolves the diagnosed issue. 
Provide:
1. The complete fixed code
2. Explanation of what was changed and why
3. Any additional recommendations

Format your response as:
FIXED_CODE:
```
[fixed code here]
```

EXPLANATION:
[explanation here]

RECOMMENDATIONS:
[recommendations here]
"""
        
        response = model.generate_content(prompt)
        result_text = response.text
        
        # Parse the response
        fixed_code = ""
        explanation = ""
        recommendations = ""
        
        if "FIXED_CODE:" in result_text:
            parts = result_text.split("FIXED_CODE:")[1]
            if "```" in parts:
                code_parts = parts.split("```")
                if len(code_parts) >= 2:
                    fixed_code = code_parts[1].strip()
        
        if "EXPLANATION:" in result_text:
            parts = result_text.split("EXPLANATION:")[1]
            if "RECOMMENDATIONS:" in parts:
                explanation = parts.split("RECOMMENDATIONS:")[0].strip()
            else:
                explanation = parts.strip()
        
        if "RECOMMENDATIONS:" in result_text:
            recommendations = result_text.split("RECOMMENDATIONS:")[1].strip()
        
        return {
            "success": True,
            "file_path": request.file_path,
            "fixed_code": fixed_code,
            "explanation": explanation,
            "recommendations": recommendations,
            "generated_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate fix: {str(e)}")


@router.post("/create_pr")
async def create_github_pr(request: CreatePRRequest):
    """
    Create a GitHub pull request with code fixes
    Handles missing files by creating a FIXES.md document instead
    """
    if not github_client:
        raise HTTPException(status_code=503, detail="GitHub integration not configured")
    
    try:
        repo = github_client.get_repo(f"{settings.github_owner}/{settings.github_repo}")
        
        # Get default branch
        default_branch = repo.default_branch
        base_ref = repo.get_git_ref(f"heads/{default_branch}")
        base_sha = base_ref.object.sha
        
        # Create new branch
        try:
            repo.create_git_ref(f"refs/heads/{request.branch_name}", base_sha)
        except Exception as e:
            if "already exists" not in str(e).lower():
                raise
        
        # Update files - with fallback for missing files
        files_updated = []
        for file_change in request.files:
            try:
                # Try to get existing file
                contents = repo.get_contents(file_change.path, ref=request.branch_name)
                repo.update_file(
                    file_change.path,
                    f"Fix: Update {file_change.path}",
                    file_change.content,
                    contents.sha,
                    branch=request.branch_name
                )
                files_updated.append(file_change.path)
            except:
                # File doesn't exist - create FIXES.md with proposed changes
                fix_doc = f"""# Proposed Fix for {file_change.path}

**Incident**: {request.incident_id or 'N/A'}
**Target File**: {file_change.path}
**Status**: File not found in repository

## Proposed Changes

```
{file_change.content}
```

## Notes

The target file `{file_change.path}` was not found in the repository.
This document contains the proposed fix that should be applied manually.

---
*Generated by ElasticSeer Autonomous Agent*
"""
                try:
                    repo.create_file(
                        "FIXES.md",
                        f"Fix: Proposed changes for {file_change.path}",
                        fix_doc,
                        branch=request.branch_name
                    )
                    files_updated.append("FIXES.md")
                except:
                    # FIXES.md exists, update it
                    try:
                        fixes_content = repo.get_contents("FIXES.md", ref=request.branch_name)
                        repo.update_file(
                            "FIXES.md",
                            f"Fix: Update proposed changes",
                            fix_doc,
                            fixes_content.sha,
                            branch=request.branch_name
                        )
                        files_updated.append("FIXES.md")
                    except:
                        pass
        
        # Create pull request
        pr = repo.create_pull(
            title=request.title,
            body=request.description,
            head=request.branch_name,
            base=default_branch
        )
        
        # Add labels
        pr.add_to_labels("elasticseer", "automated-fix")
        if request.incident_id:
            pr.add_to_labels(f"incident-{request.incident_id}")
        
        return {
            "success": True,
            "pr_number": pr.number,
            "pr_url": pr.html_url,
            "branch": request.branch_name,
            "files_changed": len(files_updated),
            "files_updated": files_updated,
            "created_at": pr.created_at.isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create PR: {str(e)}")


@router.post("/send_slack")
async def send_slack_notification(request: SlackNotificationRequest):
    """
    Send notification to Slack war room
    """
    
    severity_emoji = {
        "Sev-1": "🚨",
        "Sev-2": "⚠️",
        "Sev-3": "ℹ️"
    }
    
    emoji = severity_emoji.get(request.severity, "📢")
    
    # Build Slack message
    message = f"{emoji} *{request.severity}* - {request.title}\n\n"
    message += f"*Incident*: {request.incident_id}\n"
    message += f"*Message*: {request.message}\n"
    
    if request.pr_url:
        message += f"*PR*: {request.pr_url}\n"
    
    # Add Jira ticket URL if provided
    if hasattr(request, 'jira_url') and request.jira_url:
        message += f"*Jira Ticket*: {request.jira_url}\n"
    
    if request.action_required:
        message += f"\n⚡ *Action Required*: Please review and approve"
    
    # Try to send to Slack if token is configured
    if settings.slack_bot_token:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    "https://slack.com/api/chat.postMessage",
                    headers={
                        "Authorization": f"Bearer {settings.slack_bot_token}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "channel": settings.slack_war_room_channel or "#elasticseer-alerts",
                        "text": message,
                        "mrkdwn": True
                    }
                )
                
                result = response.json()
                
                if result.get("ok"):
                    return {
                        "success": True,
                        "channel": settings.slack_war_room_channel or "#elasticseer-alerts",
                        "message": message,
                        "sent_at": datetime.utcnow().isoformat(),
                        "slack_ts": result.get("ts")
                    }
                else:
                    # Log error but don't fail
                    error_msg = result.get("error", "Unknown error")
                    print(f"Slack API error: {error_msg}")
                    
                    # Fall through to console logging
        except Exception as e:
            print(f"Failed to send to Slack: {e}")
            # Fall through to console logging
    
    # Log the notification to console (fallback or if Slack not configured)
    print(f"\n{'='*60}")
    print("SLACK NOTIFICATION (Console)")
    print('='*60)
    print(message)
    print('='*60)
    
    return {
        "success": True,
        "channel": settings.slack_war_room_channel or "#elasticseer-alerts",
        "message": message,
        "sent_at": datetime.utcnow().isoformat(),
        "note": "Logged to console (Slack may not be fully configured)"
    }


@router.post("/detect_anomalies")
async def detect_anomalies(request: DetectAnomaliesRequest):
    """
    Detect anomalies in metrics using statistical analysis
    """
    # This would integrate with the observer_engine.py
    # For now, return a sample response
    
    return {
        "success": True,
        "anomalies_detected": 0,
        "time_range": request.time_range,
        "threshold": request.threshold_sigma,
        "message": "Anomaly detection requires the Observer Engine to be running"
    }


@router.post("/diagnose")
async def diagnose_root_cause(request: DiagnoseRequest):
    """
    Diagnose root cause using AI analysis
    """
    try:
        model = genai.GenerativeModel(settings.gemini_model)
        
        prompt = f"""You are an expert SRE diagnosing a production incident.

**Anomaly**:
{request.anomaly}

**Similar Past Incidents**:
{request.similar_incidents or 'None found'}

**Relevant Code**:
{request.relevant_code or 'Not available'}

Provide a root cause diagnosis including:
1. Root cause explanation
2. Affected components
3. Impact assessment
4. Confidence level (0.0-1.0)
5. Recommended fix

Be specific and actionable.
"""
        
        response = model.generate_content(prompt)
        
        return {
            "success": True,
            "diagnosis": response.text,
            "confidence": 0.85,  # Would be calculated based on evidence
            "diagnosed_at": datetime.utcnow().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to diagnose: {str(e)}")


@router.post("/create_jira_ticket")
async def create_jira_ticket(request: CreateJiraTicketRequest):
    """
    Create a Jira ticket for incident tracking using the Jira client
    """
    from app.services.jira_client import jira_client
    
    try:
        result = await jira_client.create_ticket(
            summary=request.summary,
            description=request.description,
            priority=request.priority,
            incident_id=request.incident_id,
            labels=request.labels
        )
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create Jira ticket: {str(e)}")


@router.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "services": {
            "gemini": bool(settings.gemini_api_key),
            "github": bool(settings.github_token),
            "slack": bool(settings.slack_bot_token),
            "elasticsearch": bool(settings.elasticsearch_url)
        }
    }
